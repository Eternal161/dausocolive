import json
import re
import time
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

# =========================================================
# 💡 BỘ GIÁP STEALTH BẤT TỬ
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

def lay_m3u8(page, url_tran, slug, nuxt_data_str):
    # 💡 CHIÊU 1: LỤC KHO DỮ LIỆU NUXT NGAY TẠI TRANG CHỦ
    # Không cần vào phòng xem, tóm sống ID nằm cạnh tên trận đấu trong bộ nhớ đệm
    if nuxt_data_str and slug:
        # Rình xem ID 7-12 số có nằm phía sau slug không
        pattern_forward = re.escape(slug) + r'.{0,300}?(?:houseId|room_id|roomId|match_id)["\']?\s*[:=]\s*["\']?(\d{7,12})["\']?'
        match = re.search(pattern_forward, nuxt_data_str, re.IGNORECASE)
        if not match:
            # Rình xem ID có nằm phía trước slug không
            pattern_backward = r'["\']?(?:houseId|room_id|roomId|match_id)["\']?\s*[:=]\s*["\']?(\d{7,12})["\']?.{0,300}?' + re.escape(slug)
            match = re.search(pattern_backward, nuxt_data_str, re.IGNORECASE)
            
        if match:
            link = f"https://live05.grita.app/live/{match.group(1)}.m3u8"
            print(f"      ⚡ [Chiêu 1 - NUXT Cache] Móc túi thành công ID: {match.group(1)}")
            return link

    # 💡 CHIÊU 2: DÙNG FETCH NGẦM (BYPASS TƯỜNG LỬA DATACENTER)
    # Lợi dụng thẻ VIP của trang chủ để tải ngầm dữ liệu phòng xem mà không bị khóa 404
    print(f"      > Đang dùng Fetch ngầm tải dữ liệu phòng xem...")
    js_fetch = f"""
    async () => {{
        try {{
            const res = await fetch("{url_tran}");
            return await res.text();
        }} catch(e) {{ return ""; }}
    }}
    """
    html_ngam = page.evaluate(js_fetch)
    
    if html_ngam:
        # Bắt ID số
        id_match = re.search(r'["\']?(?:houseId|room_id|roomId|match_id)["\']?\s*[:=]\s*["\']?(\d{7,12})["\']?', html_ngam, re.IGNORECASE)
        if id_match:
            link = f"https://live05.grita.app/live/{id_match.group(1)}.m3u8"
            print(f"      ⚡ [Chiêu 2 - Fetch Ngầm] Bắt được ID ẩn: {id_match.group(1)}")
            return link
            
        # Bắt link trực tiếp nếu lộ
        m3u8_match = re.search(r'https?:\/\/[^"\'\s<>]+?\.(m3u8|flv)[^"\'\s<>]*', html_ngam)
        if m3u8_match:
            link = m3u8_match.group(0).replace('\\/', '/')
            print(f"      🎯 [Chiêu 2 - Fetch Ngầm] Bắt được link thô: {link}")
            return link

    # 💡 CHIÊU 3: MỞ TAB MỚI LẤY HTML (Fallback cuối cùng nếu CF chặn Fetch)
    print(f"      > Bật Tab ẩn danh để cào HTML...")
    try:
        new_page = page.context.new_page()
        apply_stealth(new_page)
        new_page.goto(url_tran, wait_until="domcontentloaded", timeout=15000)
        html_tab = new_page.content()
        new_page.close()
        
        id_match = re.search(r'["\']?(?:houseId|room_id|roomId|match_id)["\']?\s*[:=]\s*["\']?(\d{7,12})["\']?', html_tab, re.IGNORECASE)
        if id_match:
            link = f"https://live05.grita.app/live/{id_match.group(1)}.m3u8"
            print(f"      ⚡ [Chiêu 3 - Tab HTML] Cào trúng ID: {id_match.group(1)}")
            return link
    except Exception:
        try: new_page.close()
        except: pass

    return ""

def cao_colatv():
    danh_sach_tran_phu_hop = []
    
    with sync_playwright() as p:
        print("🚀 Khởi động Thợ Săn ColaTV (Chiến thuật Bóng Ma)...")
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
            page.wait_for_timeout(4000) 
            
            # 💡 Bốc toàn bộ kho dữ liệu NUXT của trang chủ
            nuxt_data_str = page.evaluate("() => window.__NUXT__ ? JSON.stringify(window.__NUXT__) : ''")
            
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
                    "slug": slug, # 💡 Lưu lại slug để tìm ID
                    "giai_dau": giai_dau,
                    "thoi_gian": thoi_gian,
                    "ten_tran": ten_tran_dau,
                    "logo_nha": logo_nha,
                    "logo_khach": logo_khach,
                    "is_live": is_actually_live
                })
            
            print(f"✅ Đã lọc ra {len(danh_sach_tran_phu_hop)} trận Bóng đá.")
            danh_sach_tran_phu_hop = danh_sach_tran_phu_hop[:LIMIT_MATCHES]
            print(f"✂️ Đã áp dụng Limit! Chỉ móc link của {len(danh_sach_tran_phu_hop)} trận đầu tiên...\n")
            
            ket_qua_cuoi_cung = []
            
            for i, tran in enumerate(danh_sach_tran_phu_hop, 1):
                print(f"⏳ [{i}/{len(danh_sach_tran_phu_hop)}] Đang xử lý: {tran['ten_tran']}...")
                
                # 💡 Truyền thêm NUXT data và Slug vào để phá án
                link_m3u8 = lay_m3u8(page, tran["url"], tran["slug"], nuxt_data_str)
                
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
        print("\n⚠️ Chuyến đi trắng tay, không có trận nào đang phát.")

if __name__ == "__main__":
    cao_colatv()
