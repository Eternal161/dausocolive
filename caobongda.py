import json
import re
import time
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

# ==========================================
# CONFIG COLATV (SOCOLIVE)
# ==========================================
TARGET_URL = "https://colatv62.live"
LIMIT_MATCHES = 10  # 💡 CHỈNH GIỚI HẠN SỐ TRẬN Ở ĐÂY ĐỂ TRÁNH QUÁ TẢI CHO BOT

def lay_m3u8(page, url_tran):
    # 💡 TẦNG 1 (ƯU TIÊN TUYỆT ĐỐI): CHEAT CODE TỐI THƯỢNG TỪ HOUSE_ID!
    # Lấy thẳng số houseId trên URL để tự chế link m3u8 cực nhanh, không tốn 1s chờ đợi!
    match_id = re.search(r'houseId=(\d+)', url_tran)
    if match_id:
        hid = match_id.group(1)
        link_cheat = f"https://live05.grita.app/live/{hid}.m3u8"
        print(f"      ⚡ [Cheat Code HouseID] Tạo link siêu tốc: {link_cheat}")
        return link_cheat

    # 💡 TẦNG 2 & 3: BẢO HIỂM - Chỉ chạy khi URL không chứa houseId (ví dụ link rút gọn/redirect)
    link_stream = ""
    BAD = [".mp4", "quangcao", "banner", "tvc", "google", "facebook", "segment", "/ad/", "/ads/"]
    
    def handle_request(request):
        nonlocal link_stream
        u = request.url.lower()
        if (".m3u8" in u or ".flv" in u or "grita.app" in u) and not any(b in u for b in BAD):
            if ".ts" not in u: # Bỏ qua các mảnh video nhỏ .ts
                link_stream = request.url

    page.on("request", handle_request)
    page.on("response", lambda res: handle_request(res))

    try:
        page.goto(url_tran, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(1500)
        
        # Kiểm tra lại URL sau khi vào trang xem có bị redirect ra houseId không
        match_id_after = re.search(r'houseId=(\d+)', page.url)
        if match_id_after:
            hid = match_id_after.group(1)
            link_stream = f"https://live05.grita.app/live/{hid}.m3u8"
            print(f"      ⚡ [Cheat Code sau Redirect]: {link_stream}")
            return link_stream
        
        # Click giữa màn hình để phá banner quảng cáo
        try:
            page.mouse.click(100, 100)
            page.wait_for_timeout(300)
            page.mouse.click(640, 360)
        except Exception:
            pass

        # Đợi tối đa 4 giây cho Network
        deadline = time.time() + 4.0
        while time.time() < deadline:
            if link_stream:
                print(f"      🎯 [Network] Tóm được link: {link_stream[:55]}...")
                break
            time.sleep(0.5)
            
        # Lục soát DOM / Iframe nếu Network không thấy
        if not link_stream:
            link_stream = page.evaluate('''() => {
                let html = document.documentElement.innerHTML;
                let match = html.match(/https?:\/\/[a-zA-Z0-9.\-_]+\/(live|hls|stream)\/[a-zA-Z0-9.\-_]+\.(m3u8|flv)/i);
                if (match) return match[0];
                let iframes = document.querySelectorAll('iframe');
                for (let f of iframes) {
                    let src = f.src || '';
                    if (src.includes('m3u8') || src.includes('grita') || src.includes('flv')) return src;
                }
                return "";
            }''')
            if link_stream:
                print(f"      🎯 [DOM/Iframe] Tìm thấy link: {link_stream[:55]}...")

    except Exception as e:
        pass 
    finally:
        try: page.remove_listener("request", handle_request)
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
        
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000) 
            
            cac_the_link = page.locator("a.link-match").all()
            for the_link in cac_the_link:
                href = the_link.get_attribute("href")
                if not href:
                    continue
                
                link_full = href if href.startswith("http") else f"{TARGET_URL}{href}"
                the_cha = the_link.locator("xpath=..")
                
                logo_nha = ""
                logo_khach = ""
                is_actually_live = False
                try:
                    giai_dau = the_cha.locator(".match-item__comp").text_content().strip()
                    thoi_gian_goc = the_cha.locator(".match-item__time").text_content().strip()
                    
                    # 💡 SỬA LỖI DÍNH CHỮ: Tách chuẩn thời gian từ "14:0025/06" thành "14:00 25/06"
                    thoi_gian = re.sub(r'(\d{1,2}:\d{2})\s*(\d{1,2}/\d{1,2})', r'\1 \2', thoi_gian_goc)
                    
                    logo_nha = the_cha.locator(".match-home img").get_attribute("src")
                    logo_khach = the_cha.locator(".match-away img").get_attribute("src")
                    
                    # 💡 KIỂM TRA TRẬN ĐẤU CÓ ĐANG ĐÁ THẬT KHÔNG (Dựa vào chữ live, hiệp, bù, hoặc tỷ số)
                    text_the = the_cha.text_content().lower()
                    if any(k in text_the for k in ['hiệp', 'live', 'ht', 'ft', 'bù']) or re.search(r'\d+\s*[:\-]\s*\d+', text_the):
                        is_actually_live = True
                except:
                    continue
                
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
            
            # 💡 ÁP DỤNG LIMIT MATCH TỪ CẤU HÌNH Ở TRÊN
            danh_sach_tran_phu_hop = danh_sach_tran_phu_hop[:LIMIT_MATCHES]
            print(f"✂️ Đã áp dụng Limit! Chỉ chui vào lấy m3u8 của {len(danh_sach_tran_phu_hop)} trận đầu tiên...\n")
            
            ket_qua_cuoi_cung = []
            
            for i, tran in enumerate(danh_sach_tran_phu_hop, 1):
                print(f"⏳ [{i}/{len(danh_sach_tran_phu_hop)}] Đang xử lý: {tran['ten_tran']}...")
                link_m3u8 = lay_m3u8(page, tran["url"])
                
                formatted_name = f"{tran['ten_tran']} | {tran['thoi_gian']}"
                
                # 💡 CHUẨN HÓA NHÃN: Đang đá thật -> ● LIVE. Chưa đá -> ⏳ Chưa live (Dù đã có link houseId)
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
