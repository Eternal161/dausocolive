import json
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

TARGET_URL = "https://colatv48.live"

def lay_m3u8(page, url_tran):
    link_m3u8 = ""
    def handle_request(request):
        nonlocal link_m3u8
        if ".m3u8" in request.url:
            link_m3u8 = request.url

    page.on("request", handle_request)
    try:
        page.goto(url_tran, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000) 
    except Exception as e:
        print(f"    ❌ Lỗi tải trang: {e}")
    finally:
        page.remove_listener("request", handle_request)
    return link_m3u8

def cao_colatv():
    danh_sach_tran_phu_hop = []
    
    with sync_playwright() as p:
        print("🚀 Khởi động Thợ Săn ColaTV trên GitHub Actions...")
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-web-security"]) 
        
        # 💡 SỬA LỖI GIỜ Ở ĐÂY: Ép trình duyệt ảo dùng múi giờ Việt Nam
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
                
                try:
                    giai_dau = the_cha.locator(".match-item__comp").text_content().strip()
                    # Do trình duyệt đang ở múi giờ VN, biến thoi_gian sẽ lấy đúng 22:00
                    thoi_gian = the_cha.locator(".match-item__time").text_content().strip()
                except:
                    continue
                
                if "bóng rổ" in giai_dau.lower():
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
                    "ten_tran": ten_tran_dau
                })
            
            print(f"✅ Đã lọc ra {len(danh_sach_tran_phu_hop)} trận Bóng đá. Bắt đầu lấy link m3u8...\n")
            ket_qua_cuoi_cung = []
            
            for i, tran in enumerate(danh_sach_tran_phu_hop, 1):
                print(f"⏳ [{i}/{len(danh_sach_tran_phu_hop)}] Đang rình: {tran['ten_tran']}...")
                link_m3u8 = lay_m3u8(page, tran["url"])
                
                if link_m3u8:
                    formatted_name = f"{tran['ten_tran']} | {tran['thoi_gian']}"
                    channel_data = {
                        "name": formatted_name,
                        "tournament": tran["giai_dau"],
                        "labels": [{"text": "LIVE"}],
                        "sources": [{"contents": [{"streams": [{"stream_links": [{"url": link_m3u8}]}]}]}]
                    }
                    ket_qua_cuoi_cung.append(channel_data)
                    
        except Exception as e:
            print(f"❌ Lỗi tổng: {e}")
            
        browser.close()
        
    if ket_qua_cuoi_cung:
        mui_gio_vn = timezone(timedelta(hours=7))
        ngay_hom_nay = datetime.now(mui_gio_vn).strftime("%d/%m/%Y - %H:%M")
        
        socolive_json = {
            "playlist_name": "Cola TV (Socolive)",
            "last_updated": f"Cập nhật: {ngay_hom_nay}",
            "groups": [{"name": "Live Bóng Đá", "channels": ket_qua_cuoi_cung}]
        }
        
        with open("socolive.json", "w", encoding="utf-8") as f:
            json.dump(socolive_json, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 THÀNH CÔNG! Đã đóng gói {len(ket_qua_cuoi_cung)} trận vào socolive.json")
    else:
        print("\n⚠️ Chuyến đi trắng tay, không có trận nào đang phát.")

if __name__ == "__main__":
    cao_colatv()
