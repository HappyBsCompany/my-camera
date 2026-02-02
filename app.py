import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
from datetime import datetime
import re
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
from notion_client import Client
import time
from dotenv import load_dotenv

# [cite_start]1. 보안 정보 로드 (.env 파일이 같은 폴더에 있어야 함) 
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

notion = Client(auth=NOTION_TOKEN)

# 2. 한글 폰트 설정
def get_font(size):
    # [cite_start]윈도우 환경 기본 폰트 경로 (malgun.ttf 또는 nanum.ttf) 
    font_path = "C:/Windows/Fonts/malgun.ttf" 
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

# [cite_start]3. 상세 주소 변환 함수 (생략되었던 부분) [cite: 1]
def get_korean_address(lat, lon):
    for i in range(3):
        try:
            # [cite_start]Nominatim 서비스 사용 시 유니크한 user_agent 설정 [cite: 1]
            geolocator = Nominatim(user_agent=f"seowoo_final_{int(time.time())}")
            location = geolocator.reverse(f"{lat}, {lon}", language='ko', timeout=10)
            if location:
                raw = location.raw.get('address', {})
                # 한국식 지번/도로명 주소 구성 요소 추출
                p = raw.get('province', raw.get('city', ''))
                c = raw.get('county', raw.get('borough', ''))
                t = raw.get('town', raw.get('village', raw.get('suburb', '')))
                r = raw.get('road', raw.get('neighbourhood', ''))
                h = raw.get('house_number', '')  # 번지수
                
                addr_list = [p, c, t, r, h]
                filtered = [item for item in addr_list if item and item not in ['대한민국']]
                if filtered:
                    return " ".join(filtered).strip()
            return f"좌표 기록 ({lat:.4f}, {lon:.4f})"
        except:
            time.sleep(1)
            continue
    return f"좌표 기록 ({lat:.4f}, {lon:.4f})"

# [cite_start]4. 사진 용량 압축 함수 (5MB 제한 준수) [cite: 1]
def resize_image(image, max_size_mb=4.8):
    quality = 95
    while True:
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=quality)
        size_mb = len(output.getvalue()) / (1024 * 1024)
        if size_mb <= max_size_mb or quality <= 20:
            output.seek(0)
            return output, size_mb
        quality -= 5

# 5. 노션 전송 함수
def send_to_notion(date, loc, note):
    try:
        # [cite_start]노션 컬럼 이름: 일시, 장소, 비고와 일치해야 함 [cite: 1]
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "일시": {"title": [{"text": {"content": date}}]},
                "장소": {"rich_text": [{"text": {"content": loc}}]},
                "비고": {"rich_text": [{"text": {"content": note}}]},
            },
            # 2. 페이지 본문에 사진 추가 (이미지 URL이 있을 경우)
            children=[
                {
                    "object": "block",
                    "type": "image",
                    "image": {
                        "type": "external",
                        "external": {"url": image_url} if image_url else {"url": "https://via.placeholder.com/300"}
                    }
                }
            ] if image_url else []
        )
        return True
    except Exception as e:
        st.error(f"노션 전송 오류: {e}")
        return False

# --- UI 레이아웃 시작 ---
st.title("📸 서우배드민턴 클럽 정밀 기록기")

# [cite_start]위치 정보 가져오기 [cite: 1]
loc_info = get_geolocation()
if loc_info:
    lat, lon = loc_info['coords']['latitude'], loc_info['coords']['longitude']
    if 'address' not in st.session_state:
        st.session_state.address = get_korean_address(lat, lon)
    final_address = st.session_state.address
else:
    final_address = "위치 확인 중..."

img_file = st.camera_input("오늘의 활동 촬영")

if img_file:
    base_img = Image.open(img_file).convert("RGBA")
    w, h = base_img.size
    
    st.subheader("📝 기록 정보 확인")
    col1, col2 = st.columns(2)
    with col1:
        val_date = st.text_input("일시", datetime.now().strftime("%Y-%m-%d"))
    with col2:
        val_loc = st.text_input("장소", final_address)
    val_note = st.text_area("비고", "특이사항 없음")

    # --- 이미지 합성 (하단 밀착 정중앙) ---
    overlay = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    rect_h, margin = int(h * 0.15), 25
    rect_bottom = h - 15
    rect_top = rect_bottom - rect_h
    
    # [cite_start]반투명 배경 및 표 디자인 [cite: 1]
    draw.rectangle([(margin, rect_top), (w - margin, rect_bottom)], fill=(255, 255, 255, 200))
    font_main = get_font(int(h * 0.026))
    mid_y, mid_x = rect_top + (rect_h // 2), w // 2
    
    draw.line([(margin, rect_top), (w - margin, rect_top)], fill="black", width=4)
    draw.line([(margin, mid_y), (w - margin, mid_y)], fill="gray", width=2)
    draw.line([(margin, rect_bottom), (w - margin, rect_bottom)], fill="black", width=4)
    draw.line([(mid_x, rect_top + 5), (mid_x, mid_y - 5)], fill="gray", width=2)

    draw.text(((margin + mid_x) // 2, (rect_top + mid_y) // 2), f"일시: {val_date}", fill="black", font=font_main, anchor="mm")
    draw.text(((mid_x + (w - margin)) // 2, (rect_top + mid_y) // 2), f"장소: {val_loc}", fill="black", font=font_main, anchor="mm")
    draw.text((w // 2, (mid_y + rect_bottom) // 2), f"비고: {val_note}", fill="black", font=font_main, anchor="mm")

    combined = Image.alpha_composite(base_img, overlay).convert("RGB")
    
    # [cite_start]노션 업로드용 압축 실행 [cite: 1]
    compressed_file, final_size = resize_image(combined)
    st.image(compressed_file, caption=f"최적화 완료 ({final_size:.2f}MB)", use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(label="💾 사진첩 저장", data=compressed_file, file_name=f"{val_date}.jpg", mime="image/jpeg")
    with c2:
        if st.button("🚀 노션으로 전송"):
            if send_to_notion(val_date, val_loc, val_note):
                st.success("노션 전송 성공!")
                st.balloons()

