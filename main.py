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
# CONFIG SOCOLIVE - CHỐNG POPUP QUẢNG CÁO TÀNG HÌNH
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
# VÀO PHÒNG LIVE: DIỆT POPUP & SPAM CLICK
# =========================================================
def capture_stream(context, match_url: str) -> list:
    page = context.new_page()
    try: Stealth().apply_stealth_sync(page)
    except: pass
    streams = []

    # TRỊ TẬN GỐC POPUP: Bất kỳ Tab mới nào bật lên từ quảng cáo sẽ bị đóng ngay lập tức!
    page.on("popup", lambda p: p.close())

    def process_url(url):
        u = url.lower()
        if (".m3u8" in u or ".flv" in u) and url not in streams:
            streams.append(url)

    page.on("request",  lambda req: process_url(req.url))
    page.on("response", lambda res: process_url(res.url))

    try:
        page.goto(match_url, wait_until="load", timeout=60000)
        page.wait_for_timeout(4000) 
        
        # Tắt quảng cáo đếm ngược
        for _ in range(2):
            try:
                page.locator("text=/Bỏ qua|Skip|Đóng/i").last.click(timeout=1000)
            except: pass
            page.wait_for_timeout(1000)
            
        # CHIẾN THUẬT SPAM CLICK: Click 4 lần, mỗi lần cách nhau 1.5s
        # Nếu trúng quảng cáo tàng hình -> Tab mới mở ra -> Bị hàm popup ở trên tiêu diệt.
        # Click tiếp theo sẽ trúng video player!
        for _ in range(4):
            try:
                vp = page.viewport_size
                if vp: 
                    # Click hơi nhích lên trên (chiều cao / 3) để dễ trúng nút Play
                    page.mouse.click(vp["width"] // 2, vp["height"] // 3)
            except: pass
            page.wait_for_timeout(1500)
        
        # Ngồi rình mạng trong 10 giây
        deadline = time.time() + 10
        while time.time() < deadline:
            if len(streams) > 0: 
                time.sleep(2) # Chờ luồng ổn định để lấy link stream.m3u8 (tránh lấy nhầm master.m3u8)
                break
            time.sleep(1)
    except: pass
    finally: page.close()

    if not streams: return []
    # Thường cái link cuối cùng xuất hiện trong Network sẽ là link xịn nhất
    return [streams[-1]]

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
        # Bật tắt tuỳ ý: headless=True (ẩn) hoặc headless=False (để xem nó chạy)
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
            else: print(f"      ⚠️ Vẫn bị khiên quảng cáo chặn (Không thấy m3u8)")

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
    scrape_and_push()
