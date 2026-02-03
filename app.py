import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
import requests
from datetime import datetime
from streamlit_js_eval import get_geolocation
from notion_client import Client
import time
from dotenv import load_dotenv

# 1. 보안 정보 로드
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

notion = Client(auth=NOTION_TOKEN)

# 2. 한글 폰트 설정
def get_font(size):
    # 리눅스/클라우드 환경 대응을 위해 기본 폰트 설정 보강
    font_paths = ["C:/Windows/Fonts/malgun.ttf", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "malgun.ttf"]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

# 3. [체크 포인트] 네이버 주소 변환 함수
def get_naver_address(lat, lon):
    # 키가 비어있는지 확인
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return f"키 설정 오류 ({lat:.4f}, {lon:.4f})"

    url = f"https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc?coords={lon},{lat}&output=json&orders=addr,roadaddr"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data['results']:
                r = data['results'][0]['region']
                # 상세 지번까지 합치기
                addr = f"{r['area1']['name']} {r['area2']['name']} {r['area3']['name']} {r['area4']['name']}".strip()
                land = data['results'][0].get('land', {})
                num1 = land.get('number1', '')
                num2 = land.get('number2', '')
                
                final_addr = f"{addr} {num1}"
                if num2: final_addr += f"-{num2}"
                return final_addr.strip()
            else:
                return "주소를 찾을 수 없는 지역입니다."
        else:
            # API 호출 실패 시 에러 코드 확인용
            return f"API 오류 ({res.status_code})"
    except Exception as e:
        return f"연결 실패: {str(e)[:20]}"
    
    return f"좌표: {lat:.4f}, {lon:.4f}"

# 4. 사진 용량 압축 함수
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

# 5. [오류 수정] 노션 전송 함수 (위치도 링크 포함)
def send_to_notion(date, loc, note, lat, lon):
    try:
        # 네이버 지도 링크 생성
        naver_map_url = f"https://map.naver.com/v5/search/{lat},{lon}"
        
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "일시": {"title": [{"text": {"content": date}}]},
                "장소": {"rich_text": [{"text": {"content": loc}}]},
                "비고": {"rich_text": [{"text": {"content": note}}]},
                "위치도": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "📍 네이버 지도 보기", 
                                "link": {"url": naver_map_url}
                            },
                            "annotations": {"bold": True, "color": "blue"}
                        }
                    ]
                }
            }
        )
        return True
    except Exception as e:
        st.error(f"노션 전송 오류: {e}")
        return False

# --- UI 레이아웃 ---
st.title("📸 농어촌공사 현장 정밀 기록기")

loc_info = get_geolocation()
lat, lon = None, None

if loc_info and 'coords' in loc_info:
    lat = loc_info['coords']['latitude']
    lon = loc_info['coords']['longitude']
    if 'address' not in st.session_state:
        st.session_state.address = get_naver_address(lat, lon)
    final_address = st.session_state.address
else:
    final_address = "위치 확인 중..."

img_file = st.camera_input("현장 촬영")

if img_file:
    base_img = Image.open(img_file).convert("RGBA")
    w, h = base_img.size
    
    col1, col2 = st.columns(2)
    with col1:
        val_date = st.text_input("일시", datetime.now().strftime("%Y-%m-%d"))
    with col2:
        val_loc = st.text_input("장소", final_address)
    val_note = st.text_area("비고", "특이사항 없음")

    # 이미지 합성 로직
    overlay = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    rect_h, margin = int(h * 0.15), 25
    rect_bottom = h - 15
    rect_top = rect_bottom - rect_h
    
    draw.rectangle([(margin, rect_top), (w - margin, rect_bottom)], fill=(255, 255, 255, 200))
    font_main = get_font(int(h * 0.026))
    
    draw.text((w // 2, rect_top + rect_h // 4), f"일시: {val_date} | 장소: {val_loc}", fill="black", font=font_main, anchor="mm")
    draw.text((w // 2, rect_top + (rect_h * 3) // 4), f"비고: {val_note}", fill="black", font=font_main, anchor="mm")

    combined = Image.alpha_composite(base_img, overlay).convert("RGB")
    compressed_file, _ = resize_image(combined)
    st.image(compressed_file, use_container_width=True)
    
    if st.button("🚀 노션으로 전송"):
        if lat and lon:
            if send_to_notion(val_date, val_loc, val_note, lat, lon):
                st.success("노션에 성공적으로 기록되었습니다!")
                st.balloons()
        else:
            st.error("위치 정보가 잡히지 않았습니다.")
