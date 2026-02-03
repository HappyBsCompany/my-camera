import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io, os, requests
from datetime import datetime
from streamlit_js_eval import get_geolocation
from notion_client import Client

# 1. 시크릿 정보 로드 및 디버깅 출력
def get_clean_secret(key):
    val = st.secrets.get(key)
    return str(val).strip().replace('"', '').replace("'", "") if val else None

NAVER_ID = get_clean_secret("NAVER_CLIENT_ID")
NAVER_SECRET = get_clean_secret("NAVER_CLIENT_SECRET")
NOTION_TOKEN = get_clean_secret("NOTION_TOKEN")
DATABASE_ID = get_clean_secret("DATABASE_ID")

# [디버그 창] 화면 상단에 현재 설정 상태 표시
with st.expander("🔍 디버깅 정보 확인 (문제 해결 후 닫으세요)"):
    st.write(f"📡 접속 주소: `https://krc-my-camera.streamlit.app`")
    st.write(f"🔑 ID 로드 상태: {'✅ 성공' if NAVER_ID else '❌ 실패'}")
    if NAVER_ID:
        st.write(f"🆔 ID 앞 3자리: `{NAVER_ID[:3]}***` / Secret 앞 3자리: `{NAVER_SECRET[:3]}***`")
    st.write("---")

# 2. 네이버 주소 변환 함수 (상세 로그 출력 버전)
def get_naver_address(lat, lon):
    if not NAVER_ID or not NAVER_SECRET:
        return "⚠️ Secrets에 키가 설정되지 않았습니다."

    url = f"https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc?coords={lon},{lat}&output=json&orders=addr,roadaddr"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_ID,
        "X-NCP-APIGW-API-KEY": NAVER_SECRET
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('results'):
                r = data['results'][0]['region']
                return f"{r['area1']['name']} {r['area2']['name']} {r['area3']['name']} {r['area4']['name']}".strip()
            return f"📍 주소 없음 ({lat:.4f}, {lon:.4f})"
        
        # 401, 403 등 에러 발생 시 상세 이유 출력
        st.error(f"🚫 네이버 API 에러 발생 (코드: {res.status_code})")
        st.json(res.json()) # 네이버가 보낸 상세 에러 메시지 출력
        return f"인증 실패 ({res.status_code})"
    except Exception as e:
        return f"📡 통신 에러: {str(e)}"

# --- 이후 UI 및 전송 로직 ---
st.title("📸 현장 정밀 기록기 (디버깅 모드)")

loc_info = get_geolocation()
lat, lon, final_address = 0, 0, "위치 확인 중..."

if loc_info and isinstance(loc_info, dict) and 'coords' in loc_info:
    lat, lon = loc_info['coords'].get('latitude'), loc_info['coords'].get('longitude')
    if lat and lon:
        if 'address' not in st.session_state or st.button("🔄 위치 새로고침"):
            st.session_state.address = get_naver_address(lat, lon)
        final_address = st.session_state.address
else:
    st.warning("⚠️ 위치 정보 권한을 '허용'해 주세요.")

img_file = st.camera_input("현장 촬영")
if img_file:
    # (이미지 처리/노션 전송 로직은 이전과 동일하게 유지)
    # 생략된 부분은 이전 코드의 4번, 5번 항목과 같습니다.
    pass
