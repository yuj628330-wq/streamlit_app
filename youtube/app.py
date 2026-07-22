import streamlit as st

st.set_page_config(
    page_title="YouTube 댓글 분석기",
    page_icon="📊",
    layout="wide"
)

st.title("📊 YouTube 댓글 분석기")

st.markdown(
    """
유튜브 링크를 입력하면

- 댓글 수집
- 감성 분석
- 워드클라우드
- 다양한 시각화

를 자동으로 수행합니다.
"""
)

youtube_url = st.text_input(
    "유튜브 URL 입력",
    placeholder="https://www.youtube.com/watch?v=..."
)

max_comments = st.slider(
    "수집 댓글 수",
    100,
    1000,
    500,
    step=100
)

analyze = st.button(
    "댓글 분석 시작",
    use_container_width=True
)

if analyze:

    if youtube_url == "":
        st.warning("유튜브 링크를 입력해주세요.")

    else:

        st.success("URL 확인 완료")

        st.info("다음 단계에서 API를 호출합니다.")
