import json
import re
import time
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

# =========================================================
# 💡 BỘ GIÁP STEALTH BẤT TỬ (Chống bị web lậu khóa API)
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

def lay_m3u8(page, url_tran):
    link_stream = ""
    BAD = [".mp4", "quangcao", "banner", "tvc", "google", "facebook", "segment", "/ad/", "/ads/"]
    
    # 💡 LƯỚI QUÉT TỐI THƯỢNG: ĐỌC TRỘM PHẢN HỒI API TỪ MÁY CHỦ
    def handle_response(response):
        nonlocal link_stream
        if link_stream: return
        
        try:
            u = response.url.lower()
            
            # 1. Bắt trực tiếp link M3U8/FLV
            if (".m3u8" in u or ".flv" in u or "grita.app" in u) and not any(b in u for b in BAD):
                if ".ts" not in u: 
                    link_stream = response.url
                    return

            # 2. HACKER API: Đọc trộm JSON
            if response.request.resource_type in ["fetch", "xhr"] and response.status == 200:
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type or "text/" in content_type:
                    text = response.text()
                    
                    # Tìm link m3u8 lộ liễu
                    m3u8_match = re.search(r'https?:\/\/[^"\'\s<>]+?\.(m3u8|flv)[^"\'\s<>]*', text)
                    if m3u8_match:
                        link_stream = m3u8_match.group(0).replace('\\/', '/')
                        return
                    
                    # 💡 FIX LỖI CHÍ MẠNG: ÉP BUỘC CHỈ LẤY ID LÀ SỐ NGUYÊN (\d{7,12}), BỎ QUA HASH CHỮ!
                    id_match = re.search(r'["\']?(?:houseId|room_id|roomId|match_id)["\']?\s*[:=]\s*["\']?(\d{7,12})["\']?', text, re.IGNORECASE)
                    if id_match:
                        link_stream = f"https://live05.grita.app/live/{id_match.group(1)}.m3u8"
                        return
        except Exception:
            pass

    page.on("response", handle_response)

    try:
        page.goto(url_tran, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Click phá banner
        try:
            page.mouse.click(100, 100)
            page.wait_for_timeout(300)
            page.mouse.click(640, 360)
        except: pass

        # 💡 TẦNG 1: Chờ Network (Bắt API & XHR)
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if link_stream:
                print(f"      🎯 [API/Network] Tóm được link: {link_stream[:55]}...")
                return link_stream
            time.sleep(0.5)
            
        # 💡 TẦNG 2: Lục soát Iframe ẩn
        if not link_stream:
            iframes = page.locator("iframe").all()
            for f in iframes:
                src = f.get_attribute("src")
                if src:
                    if "m3u8" in src.lower() or "flv" in src.lower():
                        link_stream = src
                        print(f"      🎯 [Iframe SRC] Bắt sống link: {src[:55]}...")
                        return src
                    # CũnG CHỈ LẤY SỐ ở iframe
                    m = re.search(r'(?:id|room_id|live|houseId)=(\d{7,12})', src, re.IGNORECASE)
                    if m:
                        link_stream = f"https://live05.grita.app/live/{m.group(1)}.m3u8"
                        print(f"      ⚡ [Iframe ID] Ghép link từ ID: {link_stream}")
                        return link_stream

        # 💡 TẦNG 3: Khoan cắt HTML & NUXT
        if not link_stream:
            html = page.content()
            m3u8_match = re.search(r'https?:\/\/[^"\'\s<>]+?\.(m3u8|flv)[^"\'\s<>]*', html)
            if m3u8_match:
                link_stream = m3u8_match.group(0).replace('\\/', '/')
                print(f"      🎯 [DOM HTML] Tóm được link: {link_stream[:55]}...")
                return link_stream
            
            # CHỈ LẤY SỐ ở DOM
            id_match = re.search(r'(?:houseId|room_id|roomId|match_id)["\'=:\s\/]+(\d{7,12})', html, re.IGNORECASE)
            if id_match:
                link_stream = f"https://live05.grita.app/live/{id_match.group(1)}.m3u8"
                print(f"      ⚡ [DOM ID] Ghép link từ ID ẩn: {link_stream}")
                return link_stream

    except Exception as e:
        pass 
    finally:
        try: page.remove_listener("response", handle_response)
        except: pass
        
    return link_stream

def cao_colatv():
    danh_sach_tran_phu_hop = []
    
    with sync_playwright() as p:
        print("🚀 Khởi động Thợ Săn ColaTV (Socolive)...")
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
        
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000) 
            
            cac_the_link = page.locator("a.link-match").all()
            for the_link in cac_the_link:
                href = the_link.get_attribute("href")
                if not href: continue
                
                link_full = href if href.startswith("http") else f"{TARGET_URL}{href}"
                the_cha = the_link.locator("xpath=..")
                
                logo_nha = ""
                logo_khach = ""
                is_actually_live = False
                
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
                slug = link_full.split("/")[-1]
                if "-luc-" in slug:
                    chuoi_ten = slug.split("-luc-")[0]
                    ten_tran_dau = chuoi_ten.replace("-", " ").title().replace(" Vs ", " vs ")
                
                danh_sach_tran_phu_hop.append({
                    "url": link_full,
                    "giai_dau": giai_dau,
                    "thoi_gian": thoi_gian,
                    "ten_tran": ten_tran_dau,
                    "logo_nha": logo_nha,
                    "logo_khach": logo_khach,
                    "is_live": is_actually_live
                })
            
            print(f"✅ Đã lọc ra {len(danh_sach_tran_phu_hop)} trận Bóng đá.")
            
            danh_sach_tran_phu_hop = danh_sach_tran_phu_hop[:LIMIT_MATCHES]
            print(f"✂️ Đã áp dụng Limit! Chỉ chui vào lấy m3u8 của {len(danh_sach_tran_phu_hop)} trận đầu tiên...\n")
            
            ket_qua_cuoi_cung = []
            
            for i, tran in enumerate(danh_sach_tran_phu_hop, 1):
                print(f"⏳ [{i}/{len(danh_sach_tran_phu_hop)}] Đang xử lý: {tran['ten_tran']}...")
                link_m3u8 = lay_m3u8(page, tran["url"])
                
                formatted_name = f"{tran['ten_tran']} | {tran['thoi_gian']}"
                
                if tran['is_live'] and link_m3u8:
                    label_text = "● LIVE"
                elif link_m3u8:
                    label_text = "⏳ Chưa live"
                else:
                    label_text = "⏳ Chưa có link"
                    
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
        print("\n⚠️ Chuyến đi trắng tay, không có trận nào đang phát.")

if __name__ == "__main__":
    cao_colatv()
