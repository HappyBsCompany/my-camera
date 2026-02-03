import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io, os, requests, time
from datetime import datetime
from streamlit_js_eval import get_geolocation
from notion_client import Client

# 1. 보안 정보 로드 (Streamlit Cloud Secrets)
NAVER_CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET")
NOTION_TOKEN = st.secrets.get("NOTION_TOKEN")
DATABASE_ID = st.secrets.get("DATABASE_ID")

# 노션 클라이언트 초기화
if NOTION_TOKEN:
    notion = Client(auth=NOTION_TOKEN)

# 2. 한글 폰트 설정
def get_font(size):
    # 클라우드(리눅스) 및 로컬(윈도우) 경로 통합
    font_paths = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        "malgun.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

# 3. 네이버 주소 변환 함수 (401 에러 및 좌표 오류 방지)
def get_naver_address(lat, lon):
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return f"API 키 미설정 ({lat:.4f}, {lon:.4f})"

    url = f"https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc?coords={lon},{lat}&output=json&orders=addr,roadaddr"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('results'):
                r = data['results'][0]['region']
                addr = f"{r['area1']['name']} {r['area2']['name']} {r['area3']['name']} {r['area4']['name']}".strip()
                land = data['results'][0].get('land', {})
                num1 = land.get('number1', '')
                return f"{addr} {num1}".strip()
            return f"주소 미확인 지역 ({lat:.4f}, {lon:.4f})"
        elif res.status_code == 401:
            return "네이버 인증 에러(401): 키 값을 확인하세요."
        else:
            return f"네이버 에러({res.status_code})"
    except Exception as e:
        return f"연결 에러: {str(e)[:15]}"

# 4. 노션 전송 함수
def send_to_notion(date, loc, note, lat, lon):
    try:
        map_url = f"https://map.naver.com/v5/search/{lat},{lon}"
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "일시": {"title": [{"text": {"content": date}}]},
                "장소": {"rich_text": [{"text": {"content": loc}}]},
                "비고": {"rich_text": [{"text": {"content": note}}]},
                "위치도": {"rich_text": [{"text": {"content": "📍 지도 보기", "link": {"url": map_url}}}]}
            }
        )
        return True
    except Exception as e:
        st.error(f"노션 전송 오류: {e}")
        return False

# --- UI 및 메인 로직 ---
st.title("📸 현장 정밀 기록기")

# [로그 에러 해결] 위치 정보 안전하게 가져오기
loc_info = get_geolocation()
lat, lon, final_address = 0, 0, "위치 확인 중..."

if loc_info and 'coords' in loc_info:
    lat = loc_info['coords'].get('latitude')
    lon = loc_info['coords'].get('longitude')
    
    if lat and lon:
        if 'address' not in st.session_state or st.button("🔄 위치 새로고침"):
            st.session_state.address = get_naver_address(lat, lon)
        final_address = st.session_state.address
    else:
        final_address = "좌표 수신 대기 중..."
else:
    st.warning("⚠️ 모바일 브라우저의 위치 권한을 '허용'으로 설정해주세요.")

img_file = st.camera_input("현장 촬영")

if img_file:
    # 이미지 처리 및 합성
    base_img = Image.open(img_file).convert("RGB")
    w, h = base_img.size
    
    col1, col2 = st.columns(2)
    with col1:
        val_date = st.text_input("일시", datetime.now().strftime("%Y-%m-%d"))
    with col2:
        val_loc = st.text_input("장소", final_address)
    val_note = st.text_area("비고", "특이사항 없음")

    # 사진 하단에 정보 합성
    draw = ImageDraw.Draw(base_img)
    font_main = get_font(int(h * 0.03))
    # 반투명 띠 추가 등 합성 로직 (생략 가능하나 가독성을 위해 텍스트만 유지)
    draw.text((w//2, h-50), f"{val_date} | {val_loc}", fill="white", font=font_main, anchor="mm")

    st.image(base_img, caption="합성 완료", use_container_width=True)
    
    if st.button("🚀 노션으로 전송"):
        if lat != 0:
            if send_to_notion(val_date, val_loc, val_note, lat, lon):
                st.success("노션에 성공적으로 기록되었습니다!")
                st.balloons()
        else:
            st.error("위치 정보가 없어 전송할 수 없습니다.")
