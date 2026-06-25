import json
import re
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

# ==========================================
# CONFIG COLATV (SOCOLIVE)
# ==========================================
TARGET_URL = "https://colatv48.live"
LIMIT_MATCHES = 10  # 💡 CHỈNH GIỚI HẠN SỐ TRẬN Ở ĐÂY ĐỂ TRÁNH QUÁ TẢI CHO BOT

def lay_m3u8(page, url_tran):
    link_m3u8 = ""
    # 💡 DANH SÁCH ĐEN ĐỂ LỌC QUẢNG CÁO CỦA COLATV
    BAD = ["video2/output.m3u8", "output.m3u8", ".mp4", "quangcao", "banner", "live05"]
    
    def handle_request(request):
        nonlocal link_m3u8
        u = request.url.lower()
        if ".m3u8" in u and not any(b in u for b in BAD):
            link_m3u8 = request.url

    page.on("request", handle_request)
    try:
        # Giảm timeout xuống 20s để tăng tốc độ lướt qua các trận chưa live
        page.goto(url_tran, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000) 
    except Exception as e:
        pass # Bỏ qua lỗi timeout nếu trang load chậm
    finally:
        page.remove_listener("request", handle_request)
    return link_m3u8

def cao_colatv():
    danh_sach_tran_phu_hop = []
    
    with sync_playwright() as p:
        print("🚀 Khởi động Thợ Săn ColaTV (Socolive)...")
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-web-security"]) 
        
        # Ép trình duyệt ảo dùng múi giờ Việt Nam để lấy đúng giờ đá
        context = browser.new_context(timezone_id="Asia/Ho_Chi_Minh")
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
                try:
                    giai_dau = the_cha.locator(".match-item__comp").text_content().strip()
                    thoi_gian_goc = the_cha.locator(".match-item__time").text_content().strip()
                    
                    # 💡 SỬA LỖI DÍNH CHỮ: Tách chuẩn thời gian từ "14:0025/06" thành "14:00 25/06"
                    thoi_gian = re.sub(r'(\d{1,2}:\d{2})\s*(\d{1,2}/\d{1,2})', r'\1 \2', thoi_gian_goc)
                    
                    logo_nha = the_cha.locator(".match-home img").get_attribute("src")
                    logo_khach = the_cha.locator(".match-away img").get_attribute("src")
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
                    "logo_khach": logo_khach
                })
            
            print(f"✅ Đã lọc ra {len(danh_sach_tran_phu_hop)} trận Bóng đá.")
            
            # 💡 ÁP DỤNG LIMIT MATCH TỪ CẤU HÌNH Ở TRÊN
            danh_sach_tran_phu_hop = danh_sach_tran_phu_hop[:LIMIT_MATCHES]
            print(f"✂️ Đã áp dụng Limit! Chỉ chui vào lấy m3u8 của {len(danh_sach_tran_phu_hop)} trận đầu tiên...\n")
            
            ket_qua_cuoi_cung = []
            
            for i, tran in enumerate(danh_sach_tran_phu_hop, 1):
                print(f"⏳ [{i}/{len(danh_sach_tran_phu_hop)}] Đang rình: {tran['ten_tran']}...")
                link_m3u8 = lay_m3u8(page, tran["url"])
                
                formatted_name = f"{tran['ten_tran']} | {tran['thoi_gian']}"
                
                # 💡 Nếu có link -> LIVE. Nếu không có link -> Chưa live
                label_text = "● LIVE" if link_m3u8 else "⏳ Chưa live"
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
        
        # Đóng gói cấu trúc chuẩn xác như Lương Sơn
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
