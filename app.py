"""
뉴스 URL → 15장 강의 PPT 자동생성 웹앱 (Streamlit).
청중: URL 붙여넣기 → [생성] → .pptx 다운로드.
API 키는 st.secrets["OPENAI_API_KEY"] (배포) 또는 환경변수/.env (로컬).
"""
import os
import re
import streamlit as st

from extractor import extract_article, ExtractError
from generator import generate_slides, N_SLIDES
from ppt_builder import build_pptx

st.set_page_config(page_title="뉴스 → 강의 PPT 15장", page_icon="📰", layout="centered")


def get_api_key() -> str | None:
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY")


# ---------- 스타일 ----------
st.markdown("""
<style>
  /* 다크 테마는 .streamlit/config.toml 이 처리. 여기선 버튼 강조색만. */
  .stButton button { background:#60A5FA; color:#0F172A; font-weight:700; border:none; padding:.6rem 1.4rem; }
  .stDownloadButton button { background:#4ADE80; color:#0F172A; font-weight:800; }
  .hint { color:#94A3B8 !important; font-size:.85rem; }
</style>
""", unsafe_allow_html=True)

st.title("📰 뉴스 기사 → 강의 PPT 10장")
st.markdown('<p class="hint">기사 링크만 넣으면 강의용 슬라이드 10장을 자동으로 만들어 드립니다. 다운로드해서 바로 쓰세요.</p>',
            unsafe_allow_html=True)

url = st.text_input("뉴스 기사 링크 (URL)", placeholder="https://n.news.naver.com/article/...")

cda, cdb = st.columns(2)
with cda:
    dept = st.text_input("수업 학과/전공", placeholder="예: 경영학과, 간호학과, 항공서비스")
with cdb:
    grade = st.selectbox("학년", ["선택 안 함", "1학년", "2학년", "3학년", "4학년", "대학원"])

emphasis = st.text_area(
    "교수자가 강조하고 싶은 부분 (이론·핵심 메시지)",
    placeholder="예: 행동경제학의 '손실 회피' 이론으로 해석 / \"데이터보다 사람이 먼저\"라는 메시지 강조",
    height=80)
st.markdown('<p class="hint">학과·학년·강조점을 넣으면 그 전공·이론에 맞춰 해석·토론질문이 달라집니다 (선택).</p>',
            unsafe_allow_html=True)

with st.expander("기사가 안 열리면? 본문을 직접 붙여넣기"):
    manual_title = st.text_input("기사 제목 (선택)", key="mt")
    manual_body = st.text_area("기사 본문 붙여넣기", height=160, key="mb")

col1, col2 = st.columns([3, 2])
with col1:
    go = st.button("🚀 10장 PPT 만들기", use_container_width=True)
with col2:
    use_mini = st.toggle("빠른 모드(mini)", value=False, help="gpt-4o-mini로 더 빠르고 저렴하게")

api_key = get_api_key()

if go:
    if not api_key:
        st.error("서버에 OpenAI API 키가 설정되지 않았습니다. (관리자: Secrets에 OPENAI_API_KEY 추가)")
        st.stop()

    # 입력 확보: 수동 본문 우선, 없으면 URL 추출
    title, body = "", ""
    manual_body_val = (st.session_state.get("mb") or "").strip()
    if manual_body_val:
        title = (st.session_state.get("mt") or "뉴스 기사").strip()
        body = manual_body_val
    elif url.strip():
        with st.spinner("기사를 불러오는 중…"):
            try:
                title, body = extract_article(url.strip())
            except ExtractError as e:
                st.warning(str(e))
                st.stop()
            except Exception as e:
                st.error(f"기사 추출 오류: {e}")
                st.stop()
    else:
        st.info("기사 링크를 넣거나, 위 펼치기에서 본문을 붙여넣어 주세요.")
        st.stop()

    st.success(f"기사 확보: **{title}**  (본문 {len(body):,}자)")

    model = "gpt-4o-mini" if use_mini else "gpt-4o"
    grade_val = "" if grade == "선택 안 함" else grade
    aud = " ".join(x for x in [dept.strip(), grade_val] if x) or "일반 학부생"
    with st.spinner(f"AI가 '{aud}' 대상 강의 슬라이드 {N_SLIDES}장을 구성하는 중… ({model})"):
        try:
            slides = generate_slides(title, body, model=model, api_key=api_key,
                                     dept=dept, grade=grade_val, emphasis=emphasis)
        except Exception as e:
            st.error(f"슬라이드 생성 오류: {e}")
            st.stop()

    with st.spinner("PPT 파일을 만드는 중…"):
        pptx_io = build_pptx(slides, source_url=url.strip(),
                             audience="" if aud == "일반 학부생" else aud)

    fname = re.sub(r"[^\w가-힣 ]", "", title)[:40].strip().replace(" ", "_") or "news_slides"
    st.success(f"✅ 완성! 슬라이드 {len(slides)}장 — 아래에서 다운로드하세요.")
    st.download_button("⬇️ PPT 다운로드 (.pptx)",
                       data=pptx_io,
                       file_name=f"{fname}.pptx",
                       mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                       use_container_width=True)

    with st.expander(f"미리보기 (슬라이드 {len(slides)}장)"):
        for i, s in enumerate(slides, 1):
            heads = [p.get("head", "") for p in s.get("points", [])][:4]
            st.markdown(f"**{i}. {s['title']}**  \n" + "  ·  ".join(heads))

st.markdown("---")
st.markdown('<p class="hint">교수공개강의 실습용 · 고민환 · 하루 한정 운영</p>', unsafe_allow_html=True)
