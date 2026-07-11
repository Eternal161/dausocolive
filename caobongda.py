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
LIMIT_MATCHES = 10  # 💡 CHỈNH GIỚI HẠN SỐ TRẬN Ở ĐÂY

def lay_m3u8_spa(page, url_path):
    link_stream = ""
    
    # Reset mảng chứa ID/Link của phiên trước
    page.evaluate("window.__botIds = []; window.__botLinks = [];")
    
    # 💡 LƯỚI QUÉT NGẦM TRONG QUÁ TRÌNH CHUYỂN TRANG
    def handle_response(response):
        nonlocal link_stream
        if link_stream: return
        try:
            u = response.url.lower()
            if (".m3u8" in u or ".flv" in u or "grita.app" in u) and "quangcao" not in u and ".ts" not in u:
                link_stream = response.url
                return
                
            if response.request.resource_type in ["fetch", "xhr"] and response.status == 200:
                text = response.text()
                m3u8_match = re.search(r'https?:\/\/[^"\'\s<>]+?\.(m3u8|flv)[^"\'\s<>]*', text)
                if m3u8_match:
                    link_stream = m3u8_match.group(0).replace('\\/', '/')
                    return
                # Ép buộc chỉ lấy ID số nguyên, bỏ qua mã Hash chữ!
                id_match = re.search(r'["\']?(?:houseId|room_id|roomId|match_id)["\']?\s*[:=]\s*["\']?(\d{7,12})["\']?', text, re.IGNORECASE)
                if id_match:
                    link_stream = f"https://live05.grita.app/live/{id_match.group(1)}.m3u8"
                    return
        except: pass

    page.on("response", handle_response)
    
    try:
        # 💡 CHIÊU CUỐI: CLICK ẢO ĐỂ LÁCH TƯỜNG LỬA CHẶN TRUY CẬP TRỰC TIẾP (404)
        page.evaluate('''([path]) => {
            let link = document.querySelector(`a[href="${path}"]`) || document.querySelector(`a[href="${window.location.origin + path}"]`);
            if (link) {
                link.click();
            } else if (window.$nuxt && window.$nuxt.$router) {
                window.$nuxt.$router.push(path);
            } else {
                window.location.href = path;
            }
        }''', [url_path])
        
        # Đợi trang chuyển cảnh và Api nhả dữ liệu
        deadline = time.time() + 6.0
        while time.time() < deadline:
            if link_stream: 
                print(f"      🎯 [SPA Network] Tóm được link: {link_stream[:55]}...")
                break
            
            # Kiểm tra xem mã Tiêm JS đã ăn trộm được ID chưa
            bot_ids = page.evaluate("window.__botIds || []")
            if bot_ids and len(bot_ids) > 0:
                link_stream = f"https://live05.grita.app/live/{bot_ids[-1]}.m3u8"
                print(f"      ⚡ [SPA JS Hack] Lấy được ID Số: {bot_ids[-1]}")
                break
                
            bot_links = page.evaluate("window.__botLinks || []")
            if bot_links and len(bot_links) > 0:
                link_stream = bot_links[-1]
                print(f"      🎯 [SPA JS Hack] Lấy được Link: {link_stream[:55]}...")
                break
                
            time.sleep(0.5)
            
        # Vét máng bằng DOM nếu tất cả đều trượt
        if not link_stream:
            html = page.content()
            id_match = re.search(r'["\']?(?:houseId|room_id|roomId|match_id)["\']?\s*[:=]\s*["\']?(\d{7,12})["\']?', html, re.IGNORECASE)
            if id_match:
                link_stream = f"https://live05.grita.app/live/{id_match.group(1)}.m3u8"
                print(f"      ⚡ [SPA DOM] Bóc được ID ẩn: {id_match.group(1)}")
                
    except Exception as e:
        print(f"      ⚠️ Lỗi chuyển trang ảo: {e}")
    finally:
        try: page.remove_listener("response", handle_response)
        except: pass
        
    return link_stream

def cao_colatv():
    danh_sach_tran_phu_hop = []
    
    with sync_playwright() as p:
        print("🚀 Khởi động Thợ Săn ColaTV (Chiến Thuật Người Dùng Ảo)...")
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
        
        # 💡 TIÊM MÃ ĐỘC VÀO LÕI TRÌNH DUYỆT ĐỂ BẮT API TỪ BÊN TRONG
        js_interceptor = r"""
        window.__botLinks = []; window.__botIds = [];
        function extractData(text) {
            try {
                const clean = text.replace(/\\\//g, '/');
                const lMatch = clean.match(/https?:\/\/[^"']+\.(m3u8|flv)[^"']*/i);
                if (lMatch) window.__botLinks.push(lMatch[0]);
                
                // KIÊN QUYẾT CHỈ LẤY ID LÀ CHUỖI SỐ NGUYÊN TỪ 7-12 KÝ TỰ
                const iMatch = clean.match(/["'](?:houseId|room_id|roomId|match_id|id|live_id)["']\s*[:=]\s*["']?(\d{7,12})["']?/i);
                if (iMatch) window.__botIds.push(iMatch[1]);
            } catch(e) {}
        }
        const origFetch = window.fetch;
        window.fetch = async function(...args) {
            const response = await origFetch.apply(this, args);
            try { response.clone().text().then(extractData).catch(()=>({})); } catch(e) {}
            return response;
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
                
                # Bóc tách đường dẫn đuôi để Lướt Web Ảo (vd: /truc-tiep/shandong...)
                url_path = href.replace(TARGET_URL, "") if href.startswith(TARGET_URL) else href
                
                the_cha = the_link.locator("xpath=..")
                logo_nha = ""; logo_khach = ""; is_actually_live = False
                
                try:
                    giai_dau = the_cha.locator(".match-item__comp").text_content().strip()
                    thoi_gian_goc = the_cha.locator(".match-item__time").text_content().strip()
                    thoi_gian = re.sub(r'(\d{1,2}:\d{2})\s*(\d{1,2}/\d{1,2})', r'\1 \2', thoi_gian_goc)
                    logo_nha = the_cha.locator(".match-home img").get_attribute("src")
                    logo_khach = the_cha.locator(".match-away img").get_attribute("src")
                    
                    text_the = the_cha.text_content().lower()
                    if any(k in text_the for k in ['hiệp', 'live', 'ht', 'ft', 'bù']) or re.search(r'\d+\s*[:\-]\s*\d+', text_the):
                        is_actually_live = True
                except: continue
                
                if "bóng rổ" in giai_dau.lower() or "basketball" in giai_dau.lower():
                    continue

                ten_tran_dau = "Đội A vs Đội B"
                slug = url_path.split("/")[-1]
                if "-luc-" in slug:
                    chuoi_ten = slug.split("-luc-")[0]
                    ten_tran_dau = chuoi_ten.replace("-", " ").title().replace(" Vs ", " vs ")
                
                danh_sach_tran_phu_hop.append({
                    "url_path": url_path, # 💡 LƯU LẠI PATH ĐỂ CLICK
                    "giai_dau": giai_dau,
                    "thoi_gian": thoi_gian,
                    "ten_tran": ten_tran_dau,
                    "logo_nha": logo_nha,
                    "logo_khach": logo_khach,
                    "is_live": is_actually_live
                })
            
            print(f"✅ Đã lọc ra {len(danh_sach_tran_phu_hop)} trận Bóng đá.")
            danh_sach_tran_phu_hop = danh_sach_tran_phu_hop[:LIMIT_MATCHES]
            print(f"✂️ Đã áp dụng Limit! Bắt đầu cào {len(danh_sach_tran_phu_hop)} trận...\n")
            
            ket_qua_cuoi_cung = []
            
            for i, tran in enumerate(danh_sach_tran_phu_hop, 1):
                # 1. Đảm bảo Bot luôn khởi hành từ Trang Chủ
                if TARGET_URL not in page.url:
                    page.goto(TARGET_URL, wait_until="domcontentloaded")
                    page.wait_for_timeout(1500)
                    
                print(f"⏳ [{i}/{len(danh_sach_tran_phu_hop)}] Đang Click Ảo: {tran['ten_tran']}...")
                link_m3u8 = lay_m3u8_spa(page, tran["url_path"])
                
                # 2. Xong việc thì Bấm Back quay lại Trang Chủ như người thật!
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
