import json
import re
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# LƯU Ý: Nhớ đổi thành link CỦA TRẬN ĐẤU (VD: https://socolive14.cv/room/12345)
TARGET_URL = "https://socolive14.cv" 

def ultimate_m3u8_hunter(url):
    found_links = set()

    with sync_playwright() as p:
        # BÍ QUYẾT Ở ĐÂY: Tắt tính năng cô lập iFrame của Chrome
        browser = p.chromium.launch(headless=False, args=[
            "--no-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process" 
        ])
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        # LỚP QUÉT 1: Lắng nghe mọi luồng mạng (đã được phá khiên iFrame)
        def handle_request(request):
            try:
                req_url = request.url
                if ".m3u8" in req_url or "footballfast" in req_url:
                    print(f"📡 [MẠNG] Bắt được: {req_url} - soco.py:32")
                    found_links.add(req_url)
            except:
                pass

        page.on("request", handle_request)

        print(f"🌐 Đang truy cập: {url} - soco.py:39")
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 💡 TUYỆT CHIÊU MỚI: Ép trình duyệt tự bấm vào nút Play
            # Thường nút Play của các web bóng đá nằm ở giữa màn hình
            print("🎬 Đang cố gắng bấm nút Play... - soco.py:45")
            try:
                # Bấm vào bất kỳ đâu ở giữa màn hình để kích hoạt trình phát
                page.mouse.click(640, 360) 
                page.wait_for_timeout(2000)
                # Hoặc tìm thẻ có class chứa từ 'vjs-big-play-button' (nếu dùng VideoJS)
                page.locator("button[class*='play']").first.click()
            except:
                pass

            print("⏳ Đợi 10 giây để Player phản hồi... - soco.py:55")
            page.wait_for_timeout(10000)

            # LỚP QUÉT 3: Quét X-Quang toàn bộ mã nguồn HTML
            print("🔍 Đang cào thẳng vào mã nguồn HTML... - soco.py:59")
            html_content = page.content()
            
            # Biểu thức chính quy bòn mót mọi text giống link .m3u8
            m3u8_regex = r"(https?://[^\s\"\'<>]+?\.m3u8[^\s\"\'<>]*)"
            matches = re.findall(m3u8_regex, html_content)
            for match in matches:
                print(f"📄 [HTML] Lôi ra từ code: {match} - soco.py:66")
                found_links.add(match)

        except Exception as e:
            print(f"❌ Lỗi truy cập: {e} - soco.py:70")
        finally:
            browser.close()

    return list(found_links)

if __name__ == "__main__":
    links = ultimate_m3u8_hunter(TARGET_URL)

    # Lọc chỉ lấy link chứa chữ m3u8 hoặc footballfast
    clean_links = [link for link in links if "m3u8" in link.lower() or "footballfast" in link.lower()]

    print("\n🎉 === KẾT QUẢ TỔNG HỢP === - soco.py:82")
    if not clean_links:
        print("⚠️ Vẫn không tìm thấy. Có thể trang web yêu cầu Captcha hoặc chặn bot. - soco.py:84")
    else:
        for link in clean_links:
            print(f"👉 {link} - soco.py:87")

    output_data = {
        "url_goc": TARGET_URL,
        "total_links": len(clean_links),
        "links": clean_links
    }
    
    with open("link_bongda.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print("\n✅ Đã lưu vào socolive.json! - soco.py:98")
