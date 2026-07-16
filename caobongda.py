import json
import re
import time
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

# =========================================================
# 💡 BỘ GIÁP STEALTH
# =========================================================
def apply_stealth(page):
    try:
        from playwright_stealth import stealth_sync
        stealth_sync(page)
    except ImportError:
        try:
            from playwright_stealth import Stealth
            Stealth().apply_stealth_sync(page)
        except Exception: pass
    except Exception: pass

# ==========================================
# CONFIG COLATV (SOCOLIVE)
# ==========================================
TARGET_URL = "https://colatv62.live"
LIMIT_MATCHES = 20  # 💡 CHỈNH GIỚI HẠN SỐ TRẬN Ở ĐÂY

def lay_m3u8_spa(page, url_path, slug):
    link_stream = ""
    
    # 💡 XÓA SẠCH BỘ NHỚ TRƯỚC KHI VÀO TRẬN MỚI
    page.evaluate("window.__apiData = [];")
    
    def handle_response(response):
        nonlocal link_stream
        if link_stream: return
        try:
            req_url = response.url.lower()
            # 💡 Bắt cả flv và m3u8, nhưng sau đó sẽ ép đổi đuôi thành m3u8
            if (".m3u8" in req_url or ".flv" in req_url or "grita.app" in req_url) and "quangcao" not in req_url and ".ts" not in req_url:
                # Ép đuôi flv thành m3u8
                link_stream = req_url.replace(".flv", ".m3u8")
        except: pass

    page.on("response", handle_response)
    
    try:
        # Click chuyển trang ảo (Giả lập người dùng thật)
        page.evaluate(f'''([path]) => {{
            let link = document.querySelector(`a[href*="{slug}"]`) || document.querySelector(`a[href="${{window.location.origin + path}}"]`);
            if (link) link.click();
            else if (window.$nuxt && window.$nuxt.$router) window.$nuxt.$router.push(path);
            else window.location.href = path;
        }}''', [url_path])
        
        # 💡 CHỜ VÀ "LỌC TẠP CHẤT" KẾT QUẢ API
        deadline = time.time() + 6.0
        while time.time() < deadline:
            if link_stream: 
                print(f"      🎯 [Network] Tóm được link thô: {link_stream[:55]}...")
                break
            
            # Lôi toàn bộ API vớt được ra kiểm tra
            api_data = page.evaluate("window.__apiData || []")
            for item in api_data:
                req_url = item.get("url", "").lower()
                text = item.get("text", "")
                
                # Bỏ qua các API chạy ngầm gây lỗi trùng ID (danh sách, quảng cáo, top trending)
                if any(x in req_url for x in ["/list", "/home", "/config", "/schedule", "/banner", "hot"]):
                    continue
                    
                # 💡 KHÓA MỤC TIÊU: API này BẮT BUỘC phải chứa thông tin của trận đấu (slug)
                slug_short = slug.split('-luc-')[0]
                if slug in req_url or "detail" in req_url or "room" in req_url or slug_short in req_url or slug_short.replace("-", " ") in text.lower():
                    
                    # 💡 Bắt Link ẩn trong JSON, CHỦ ĐỘNG thay .flv thành .m3u8
                    m3u8_match = re.search(r'https?:\/\/[^"\'\s<>]+?\.(?:m3u8|flv)[^"\'\s<>]*', text)
                    if m3u8_match:
                        link_stream = m3u8_match.group(0).replace('\\/', '/').replace('.flv', '.m3u8')
                        print(f"      🎯 [JS API] Tóm được Link chuẩn: {link_stream[:55]}...")
                        break
                        
                    # Bắt ID Số (Đã loại bỏ chữ 'id' chung chung để khỏi bắt nhầm ID bài viết)
                    id_match = re.search(r'["\']?(?:houseId|room_id|roomId|match_id|live_id)["\']?\s*[:=]\s*["\']?(\d{7,12})["\']?', text, re.IGNORECASE)
                    if id_match:
                        link_stream = f"https://live05.grita.app/live/{id_match.group(1)}.m3u8"
                        print(f"      ⚡ [JS API] Bóc được ID Số ({id_match.group(1)}) từ nguồn: {req_url[:40]}...")
                        break
                        
            if link_stream: break
            time.sleep(0.5)
            
    except Exception as e:
        print(f"      ⚠️ Lỗi chuyển trang ảo: {e}")
    finally:
        try: page.remove_listener("response", handle_response)
        except: pass
        
    return link_stream

def cao_colatv():
    danh_sach_tran_phu_hop = []
    
    with sync_playwright() as p:
        print("🚀 Khởi động Thợ Săn ColaTV (Bản Lọc Trùng ID & Ép M3U8)...")
        browser = p.chromium.launch(headless=True, args=[
                "--no-sandbox", 
                "--disable-web-security",
                "--autoplay-policy=no-user-gesture-required", 
                "--mute-audio",                              
                "--allow-running-insecure-content",
                "--disable-blink-features=AutomationControlled"
            ]) 
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 720}, 
            timezone_id="Asia/Ho_Chi_Minh"
        )
        page = context.new_page()
        
        apply_stealth(page)
        
        # 💡 TIÊM MÃ ĐỘC ĐỂ GOM GÓI TIN API
        js_interceptor = r"""
        window.__apiData = [];
        const origFetch = window.fetch;
        window.fetch = async function(...args) {
            let reqUrl = (typeof args[0] === 'string') ? args[0] : (args[0] && args[0].url ? args[0].url : '');
            const response = await origFetch.apply(this, args);
            try { 
                response.clone().text().then(t => {
                    if (t.length > 50) window.__apiData.push({url: reqUrl, text: t});
                }).catch(()=>({})); 
            } catch(e) {}
            return response;
        };
        
        const origOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url) {
            this._reqUrl = url;
            this.addEventListener('load', function() {
                if (this.responseText && this.responseText.length > 50) {
                    window.__apiData.push({url: this._reqUrl, text: this.responseText});
                }
            });
            origOpen.apply(this, arguments);
        };
        """
        page.add_init_script(js_interceptor)
        
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000) 
            
            cac_the_link = page.locator("a.link-match").all()
            for the_link in cac_the_link:
                href = the_link.get_attribute("href")
                if not href: continue
                
                url_path = href.replace(TARGET_URL, "") if href.startswith(TARGET_URL) else href
                the_cha = the_link.locator("xpath=..")
                logo_nha = ""; logo_khach = ""; is_actually_live = False
                
                try:
                    giai_dau = the_cha.locator(".match-item__comp").text_content().strip()
                    
                    giai_dau_lower = giai_dau.lower()
                    if "bóng rổ" in giai_dau_lower or "basketball" in giai_dau_lower or "nba" in giai_dau_lower:
                        continue

                    thoi_gian_goc = the_cha.locator(".match-item__time").text_content().strip()
                    thoi_gian = re.sub(r'(\d{1,2}:\d{2})\s*(\d{1,2}/\d{1,2})', r'\1 \2', thoi_gian_goc)
                    logo_nha = the_cha.locator(".match-home img").get_attribute("src")
                    logo_khach = the_cha.locator(".match-away img").get_attribute("src")
                    
                    text_the = the_cha.text_content().lower()
                    if any(k in text_the for k in ['hiệp', 'live', 'ht', 'ft', 'bù']) or re.search(r'\d+\s*[:\-]\s*\d+', text_the):
                        is_actually_live = True
                except: continue

                ten_tran_dau = "Đội A vs Đội B"
                slug = url_path.split("/")[-1]
                if "-luc-" in slug:
                    chuoi_ten = slug.split("-luc-")[0]
                    ten_tran_dau = chuoi_ten.replace("-", " ").title().replace(" Vs ", " vs ")
                
                danh_sach_tran_phu_hop.append({
                    "url_path": url_path,
                    "slug": slug,
                    "giai_dau": giai_dau,
                    "thoi_gian": thoi_gian,
                    "ten_tran": ten_tran_dau,
                    "logo_nha": logo_nha,
                    "logo_khach": logo_khach,
                    "is_live": is_actually_live
                })
            
            print(f"✅ Đã lọc ra {len(danh_sach_tran_phu_hop)} trận Bóng đá (đã loại bóng rổ/NBA).")
            danh_sach_tran_phu_hop = danh_sach_tran_phu_hop[:LIMIT_MATCHES]
            print(f"✂️ Đã áp dụng Limit! Bắt đầu cào {len(danh_sach_tran_phu_hop)} trận...\n")
            
            ket_qua_cuoi_cung = []
            
            for i, tran in enumerate(danh_sach_tran_phu_hop, 1):
                # An toàn 100%: Luôn đảm bảo Bot đứng ở trang chủ trước khi click
                if TARGET_URL not in page.url or len(page.url) > len(TARGET_URL) + 5:
                    page.goto(TARGET_URL, wait_until="domcontentloaded")
                    page.wait_for_timeout(1500)
                    
                print(f"⏳ [{i}/{len(danh_sach_tran_phu_hop)}] Đang Click Ảo: {tran['ten_tran']}...")
                link_m3u8 = lay_m3u8_spa(page, tran["url_path"], tran["slug"])
                
                # Cào xong thì tự giác bấm lùi trang lại
                try: 
                    page.evaluate("window.history.back()")
                    page.wait_for_timeout(1500)
                except: pass
                
                formatted_name = f"{tran['ten_tran']} | {tran['thoi_gian']}"
                
                if tran['is_live'] and link_m3u8: label_text = "● LIVE"
                elif link_m3u8: label_text = "⏳ Chưa live"
                else: label_text = "⏳ Chưa có link"
                    
                stream_links = [{"url": link_m3u8}] if link_m3u8 else []

                channel_data = {
                    "name": formatted_name,
                    "tournament": tran["giai_dau"],
                    "logo_nha": tran["logo_nha"],     
                    "logo_khach": tran["logo_khach"], 
                    "labels": [{"text": label_text}],
                    "sources": [{"contents": [{"streams": [{"stream_links": stream_links}]}]}]
                }
                ket_qua_cuoi_cung.append(channel_data)
                
        except Exception as e:
            print(f"❌ Lỗi tổng: {e}")
            
        browser.close()
        
    if ket_qua_cuoi_cung:
        mui_gio_vn = timezone(timedelta(hours=7))
        ngay_hom_nay = datetime.now(mui_gio_vn).strftime("%H:%M %d/%m/%Y")
        
        socolive_json = {
            "id": "socolive",
            "name": "Socolive (Cola TV)",
            "last_updated": f"{ngay_hom_nay}",
            "groups": [{"id": "live", "name": "🔴 Trực tiếp & Sắp tới", "channels": ket_qua_cuoi_cung}]
        }
        
        with open("socolive.json", "w", encoding="utf-8") as f:
            json.dump(socolive_json, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 THÀNH CÔNG! Đã đóng gói {len(ket_qua_cuoi_cung)} trận vào socolive.json")
    else:
        print("\n⚠️ Chuyến đi trắng tay.")

if __name__ == "__main__":
    cao_colatv()
