import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io, os, requests, time
from datetime import datetime
from streamlit_js_eval import get_geolocation
from notion_client import Client

# [중요] Streamlit Secrets와 이름을 100% 일치시켰습니다.
NAVER_CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET")
NOTION_TOKEN = st.secrets.get("NOTION_TOKEN")
DATABASE_ID = st.secrets.get("DATABASE_ID")

notion = Client(auth=NOTION_TOKEN)

def get_font(size):
    font_paths = ["C:/Windows/Fonts/malgun.ttf", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "malgun.ttf"]
    for path in font_paths:
        if os.path.exists(path): return ImageFont.truetype(path, size)
    return ImageFont.load_default()

# --- 네이버 주소 변환 함수 (디버깅 메시지 포함) ---
def get_naver_address(lat, lon):
    if not NAVER_CLIENT_ID:
        return "Secrets 설정 확인 필요"

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
                addr = f"{r['area1']['name']} {r['area2']['name']} {r['area3']['name']} {r['area4']['name']}".strip()
                land = data['results'][0].get('land', {})
                num1 = land.get('number1', '')
                return f"{addr} {num1}".strip()
            return "주소 결과 없음"
        else:
            # 사용량이 안 올라간다면 여기서 에러 코드가 뜰 것입니다.
            return f"네이버 에러: {res.status_code}"
    except Exception as e:
        return f"연결 에러: {str(e)[:15]}"

# --- UI 및 메인 로직 ---
st.title("📸 현장 정밀 기록기 (최종)")

loc_info = get_geolocation()
if loc_info and 'coords' in loc_info:
    lat, lon = loc_info['coords']['latitude'], loc_info['coords']['longitude']
    
    # 주소를 세션에 저장하여 API 중복 호출 방지
    if 'address' not in st.session_state or st.button("🔄 위치 새로고침"):
        st.session_state.address = get_naver_address(lat, lon)
    
    final_address = st.session_state.address
else:
    final_address = "위치 확인 중..."
    lat, lon = 0, 0

img_file = st.camera_input("현장 촬영")
if img_file:
    # (이미지 처리 부분은 동일...)
    val_date = st.text_input("일시", datetime.now().strftime("%Y-%m-%d"))
    val_loc = st.text_input("장소", final_address)
    val_note = st.text_area("비고", "특이사항 없음")

    if st.button("🚀 노션으로 전송"):
        # send_to_notion 호출 시 lat, lon 전달 확인
        # (기존 send_to_notion 함수 내용 그대로 사용)
        pass
