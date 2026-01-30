import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import os
from datetime import datetime

st.set_page_config(page_title="사진 하단 표 합성기", layout="centered")

def get_font(size):
    font_path = "malgun.ttf" 
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    else:
        return ImageFont.load_default()

st.title("📸 사진 내부 표 합성 도구")

img_file = st.camera_input("현장 사진 촬영")

if img_file:
    # 이미지를 RGBA(투명도 지원) 모드로 변환
    base_img = Image.open(img_file).convert("RGBA")
    w, h = base_img.size
    
    st.subheader("📝 기록 내용")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    col1, col2 = st.columns(2)
    with col1:
        val_date = st.text_input("일시", now)
        val_loc = st.text_input("장소", "서우배드민턴장")
    with col2:
        val_name = st.text_input("작성자", "김봉수")
        val_note = st.text_input("비고", "특이사항 없음")

    # --- 오버랩 레이어 생성 ---
    # 사진과 똑같은 크기의 투명한 캔버스를 만듭니다.
    overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    # 1. 하단 박스 영역 계산
    rect_height = int(h * 0.2)
    rect_top = h - rect_height
    
    # 2. 반투명 흰색 박스 그리기 (마지막 숫자 180이 불투명도입니다. 0~255 사이에서 조절 가능)
    # 사진이 아예 안 잘려 보이게 하려면 이 박스를 연하게 만들면 됩니다.
    draw.rectangle([(0, rect_top), (w, h)], fill=(255, 255, 255, 180)) 
    
    # 3. 폰트 및 간격 설정
    font_main = get_font(int(h * 0.035))
    padding = int(rect_height * 0.15)
    row_height = (rect_height - (padding * 2)) // 2
    
    # 4. 표 선 및 텍스트 그리기
    line_top = rect_top + padding
    line_mid_h = rect_top + padding + row_height
    line_bottom = h - padding
    
    # 선과 글씨는 불투명하게(255) 그립니다.
    draw.line([(20, line_top), (w-20, line_top)], fill=(0, 0, 0, 255), width=3)
    draw.line([(20, line_mid_h), (w-20, line_mid_h)], fill=(100, 100, 100, 255), width=1)
    draw.line([(20, line_bottom), (w-20, line_bottom)], fill=(0, 0, 0, 255), width=3)
    draw.line([(w//2, line_top), (w//2, line_bottom)], fill=(100, 100, 100, 255), width=2)

    text_y_offset = int(row_height * 0.15)
    draw.text((40, line_top + text_y_offset), f"일시: {val_date}", fill=(0, 0, 0, 255), font=font_main)
    draw.text((w//2 + 40, line_top + text_y_offset), f"작성자: {val_name}", fill=(0, 0, 0, 255), font=font_main)
    draw.text((40, line_mid_h + text_y_offset), f"장소: {val_loc}", fill=(0, 0, 0, 255), font=font_main)
    draw.text((w//2 + 40, line_mid_h + text_y_offset), f"비고: {val_note}", fill=(0, 0, 0, 255), font=font_main)

    # 5. 원본 이미지와 오버랩 레이어 합성
    combined = Image.alpha_composite(base_img, overlay).convert("RGB")

    # 결과 출력
    st.image(combined, caption="사진 내부 반투명 오버랩 결과", use_container_width=True)
    
    buf = io.BytesIO()
    combined.save(buf, format="JPEG", quality=95)
    st.download_button(label="💾 사진첩에 저장하기", data=buf.getvalue(), file_name="record.jpg", mime="image/jpeg")