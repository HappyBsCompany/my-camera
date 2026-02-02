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

# 1. .env 파일로부터 보안 정보 로드
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

notion = Client(auth=NOTION_TOKEN)

def get_font(size):
    font_path = "C:/Windows/Fonts/malgun.ttf" 
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

# --- 사진 용량 압축 함수 (5MB 제한 준수) ---
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

def send_to_notion(date, loc, note):
    try:
        # 노션의 컬럼 이름(일시, 장소, 비고)과 반드시 똑같아야 합니다!
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "일시": {"title": [{"text": {"content": date}}]},
                "장소": {"rich_text": [{"text": {"content": loc}}]},
                "비고": {"rich_text": [{"text": {"content": note}}]},
            }
        )
        return True
    except Exception as e:
        st.error(f"노션 전송 오류: {e}")
        return False

# --- UI 및 앱 로직 ---
st.title("📸 서우배드민턴 클럽 현장 기록기")

loc_info = get_geolocation()
if loc_info:
    lat, lon = loc_info['coords']['latitude'], loc_info['coords']['longitude']
    if 'address' not in st.session_state:
        # (기존 주소 추출 함수 get_korean_address는 생략, 이전 코드 참조)
        st.session_state.address = f"{lat:.4f}, {lon:.4f}" # 예시 좌표
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

    # 이미지 합성 및 압축 (하단 밀착 레이아웃)
    # ... (합성 로직은 이전과 동일) ...
    overlay = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    # 합성 완료 후:
    combined = base_img # (실제로는 합성된 이미지)
    
    compressed_file, final_size = resize_image(combined.convert("RGB"))
    
    st.image(compressed_file, caption=f"최적화 완료 ({final_size:.2f}MB)")

    if st.button("🚀 노션 데이터베이스로 전송"):
        if send_to_notion(val_date, val_loc, val_note):
            st.success("노션에 기록이 성공적으로 저장되었습니다!")
            st.balloons()
