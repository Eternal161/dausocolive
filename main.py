import os
import re
import time
import json
import uuid
import hashlib
import datetime
import requests
from github import Github
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from playwright_stealth import Stealth

# =========================================================
# CONFIG SOCOLIVE - CỖ MÁY XUYÊN THẤU KHIÊN QUẢNG CÁO
# =========================================================
TARGET_SITE   = "https://socolive14.cv/"
FILE_PATH     = "socolive.json"
LIMIT_MATCHES = 3

VN_TZ = datetime.timezone(datetime.timedelta(hours=7))
GITHUB_TOKEN = os.getenv("GH_TOKEN")
REPO_NAME    = os.getenv("GH_REPO", "Eternal161/dausocolive") 

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9",
}

def make_id(seed: str = "") -> str:
    h = hashlib.md5((seed or str(uuid.uuid4())).encode()).hexdigest()
    return f"soco-{h[:12]}"

def make_link_id() -> str:
    return "lnk-" + hashlib.md5(str(time.time_ns()).encode()).hexdigest()[:10]

def get_final_logo(team_name: str, site_logo: str = "") -> str:
    if site_logo and site_logo.startswith("http") and "data:image" not in site_logo: 
        return site_logo
    initials = requests.utils.quote(team_name[:2] if len(team_name) >= 2 else "FC")
    return f"https://ui-avatars.com/api/?name={initials}&size=200&background=1E88E5&color=ffffff&bold=true"

# =========================================================
# JS BÓC TÁCH TÊN VÀ LOGO
# =========================================================
JS_EXTRACT = """
() => {
    const results = [];
    const seen = new Set();
    const anchors = Array.from(document.querySelectorAll('a.link-match'));
    
    for (const a of anchors) {
        let href = a.getAttribute('href') || a.href || '';
        if (!href || href === '#' || href.includes('javascript:')) continue;
        if (href.startsWith('/')) href = window.location.origin + href;
        href = href.split('#')[0];
        
        if (seen.has(href)) continue;
        seen.add(href);

        let title = a.getAttribute('title') || '';
        let home = 'Đội nhà';
        let away = 'Đội khách';
        let timeStr = 'Live';

        let matchInfo = title.replace(/Trực tiếp bóng đá( Socolive)? /i, '').trim();
        let timeParts = matchInfo.split(' lúc ');

        if (timeParts.length > 0) {
            let teams = timeParts[0].split(' vs ');
            if (teams.length === 2) {
                home = teams[0].trim();
                away = teams[1].trim();
            }
        }
        if (timeParts.length > 1) {
            timeStr = timeParts[1].replace('ngày ', '').split('/202')[0].trim();
        }

        let parent = a.parentElement;
        for(let i=0; i<3; i++) {
            if(parent && parent.querySelectorAll('.match-item-body').length > 0) break;
            if(parent) parent = parent.parentElement;
        }
        if(!parent) parent = a.parentElement;
        
        let validImgs = Array.from(parent.querySelectorAll('img'))
            .map(i => i.getAttribute('data-src') || i.src || '')
            .filter(src => src && !src.includes('avatar') && !src.includes('man-user') && !src.includes('icon'));
        
        let homeLogo = validImgs.length > 0 ? validImgs[0] : '';
        let awayLogo = validImgs.length > 1 ? validImgs[1] : '';
        
        results.push({ href, home, away, timeStr, homeLogo, awayLogo });
    }
    return results;
}
"""

# =========================================================
# VÀO PHÒNG LIVE: QUÉT MÃ NGUỒN + XÓA KHIÊN + ÉP PLAY
# =========================================================
def capture_stream(context, match_url: str) -> list:
    page = context.new_page()
    try: Stealth().apply_stealth_sync(page)
    except: pass
    streams = []

    page.on("popup", lambda p: p.close())

    def process_url(url):
        u = url.lower()
        # Chặn các m3u8 lỗi hoặc quảng cáo tĩnh
        if (".m3u8" in u or ".flv" in u) and url not in streams and "ad" not in u:
            streams.append(url)

    page.on("request",  lambda req: process_url(req.url))
    page.on("response", lambda res: process_url(res.url))

    try:
        page.goto(match_url, wait_until="load", timeout=60000)
        page.wait_for_timeout(4000) 
        
        # BƯỚC 1: Quét X-Quang mã nguồn HTML để mò link giấu kín
        try:
            m3u8_pattern = re.compile(r'(https?://[^\s"\'<>]*\.m3u8[^\s"\'<>]*)')
            flv_pattern = re.compile(r'(https?://[^\s"\'<>]*\.flv[^\s"\'<>]*)')
            
            # Quét trang chính
            html = page.content()
            for m in m3u8_pattern.findall(html): process_url(m)
            for m in flv_pattern.findall(html): process_url(m)
            
            # Quét các Iframe bên trong (Socolive hay giấu Player trong Iframe)
            for frame in page.frames:
                try:
                    f_html = frame.content()
                    for m in m3u8_pattern.findall(f_html): process_url(m)
                    for m in flv_pattern.findall(f_html): process_url(m)
                except: pass
        except: pass

        # Nếu quét X-Quang đã ra link, dừng luôn cho nhanh
        if streams:
            page.close()
            return [streams[-1]]

        # BƯỚC 2: Tiêu diệt lớp Khiên tàng hình & Ép Video chạy bằng Javascript
        try:
            page.evaluate('''() => {
                // Xóa mọi thẻ div lơ lửng đè lên trên màn hình (z-index cao)
                document.querySelectorAll('div').forEach(d => {
                    const z = parseInt(window.getComputedStyle(d).zIndex);
                    if(!isNaN(z) && z > 99) d.remove(); 
                });
                
                // Tìm thẻ video và ép nó Play
                const vids = document.querySelectorAll('video');
                vids.forEach(v => { 
                    v.muted = true; // Mute để lách luật Auto-play của trình duyệt
                    v.play().catch(e => console.log(e)); 
                });
            }''')
        except: pass
        
        # BƯỚC 3: Xóa Nút Bỏ Qua và Click vật lý
        for _ in range(2):
            try: page.locator("text=/Bỏ qua|Skip|Đóng/i").last.click(timeout=1000)
            except: pass
            page.wait_for_timeout(1000)
            
        for _ in range(3):
            try:
                vp = page.viewport_size
                if vp: page.mouse.click(vp["width"] // 2, vp["height"] // 2)
            except: pass
            page.wait_for_timeout(1500)
        
        deadline = time.time() + 10
        while time.time() < deadline:
            if len(streams) > 0: 
                time.sleep(2) 
                break
            time.sleep(1)
    except: pass
    finally: page.close()

    # LỌC LINK: Ưu tiên link có chứa stream/niues, loại bỏ link quá ngắn
    valid_streams = [s for s in streams if len(s) > 20]
    if not valid_streams: return []
    
    best_streams = [s for s in valid_streams if "stream" in s.lower() or "niues" in s.lower() or "pull" in s.lower()]
    if best_streams: return [best_streams[-1]]
    return [valid_streams[-1]]

def build_channel(m: dict, stream_urls: list) -> dict:
    home = m.get("home", "Unknown")
    away = m.get("away", "Unknown")
    
    cid = make_id(m["href"])
    title_clean = f"{home} vs {away}"
    display_name = f"⚽ {title_clean}"

    is_live = len(stream_urls) > 0
    label_text = "● Live" if is_live else "⏳ Chưa live"
    label_color = "#ff0000" if is_live else "#d54f1a"
    
    stream_type = "m3u8" if is_live and ".m3u8" in stream_urls[0].lower() else "mp4"

    return {
        "id": cid, "name": display_name, 
        "logo_nha": get_final_logo(home, m.get("homeLogo")), 
        "logo_khach": get_final_logo(away, m.get("awayLogo")),
        "type": "single", "display": "thumbnail-only", "enable_detail": False,
        "image": {"padding": 1, "background_color": "#ececec", "display": "contain", "url": get_final_logo(home, m.get("homeLogo")), "width": 1600, "height": 1200},
        "labels": [{"text": label_text, "position": "top-left", "color": "#00ffffff", "text_color": label_color}],
        "sources": [{
            "id": cid, "name": "Socolive",
            "contents": [{
                "id": cid, "name": title_clean,
                "streams": [{"id": cid, "name": "F", "stream_links": [{"id": make_link_id(), "name": "Link Stream", "type": stream_type, "default": True, "url": u} for u in stream_urls[:1]]}]
            }]
        }],
    }

def scrape_and_push():
    now_str = datetime.datetime.now(VN_TZ).strftime("%H:%M %d/%m/%Y")
    print(f"🚀 BẮT ĐẦU BOT SOCOLIVE (Giờ VN): {now_str}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=_HEADERS["User-Agent"], timezone_id="Asia/Ho_Chi_Minh")
        page = context.new_page()
        try: Stealth().apply_stealth_sync(page)
        except: pass

        try: 
            print("📺 Đang mở trang chủ Socolive...")
            page.goto(TARGET_SITE, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(4000) 
        except: pass

        print("⏳ Đang cuộn trang thu thập link...")
        for _ in range(6):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1000)

        raw_matches = page.evaluate(JS_EXTRACT)
        valid_matches = [m for m in raw_matches if m["home"] != "Đội nhà"][:LIMIT_MATCHES]
        
        print(f"\n🎥 TÌM THẤY {len(valid_matches)} TRẬN ĐẤU THẬT.")

        for idx, m in enumerate(valid_matches, 1):
            print(f"\n   [{idx}/{len(valid_matches)}] {m['home']} vs {m['away']}")
            print(f"      👉 Đang rình tại: {m['href']}")
            m["streams"] = capture_stream(context, m["href"])
            
            if m["streams"]: print(f"      ✅ BẮT ĐƯỢC LINK: {m['streams'][0][:80]}...")
            else: print(f"      ⚠️ Đã quét X-Quang nhưng luồng có thể chưa được phát.")

    channels = [build_channel(m, m["streams"]) for m in valid_matches]
    content = json.dumps({
        "id": "socolive", "name": "Socolive", "last_updated": now_str, 
        "groups": [{"id": "live", "name": "🔴 Trực tiếp (M3U8)", "channels": channels}]
    }, indent=2, ensure_ascii=False)
    
    if GITHUB_TOKEN:
        try:
            repo = Github(GITHUB_TOKEN).get_repo(REPO_NAME)
            msg = "⚽ Sync Socolive: " + now_str
            try:
                existing = repo.get_contents(FILE_PATH)
                repo.update_file(existing.path, msg, content, existing.sha)
                print("\n✅ Đã cập nhật thành công lên GitHub!")
            except:
                repo.create_file(FILE_PATH, msg, content)
                print("\n✅ Đã khởi tạo file mới trên GitHub!")
        except Exception as e:
            print(f"\n❌ Lỗi khi tải lên GitHub: {e}")
    else:
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✅ Đã lưu dữ liệu ra file {FILE_PATH} (Do không có GH_TOKEN)")

if __name__ == "__main__":
    scrape_and_push
