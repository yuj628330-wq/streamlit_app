import os
import re
import urllib.request
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from wordcloud import WordCloud

# --- 1. 페이지 설정 및 한글 폰트 로드 ---
st.set_page_config(
    page_title="유튜브 댓글 분석기", page_icon="📊", layout="wide"
)

FONT_PATH = "NanumGothic.ttf"


@st.cache_resource
def download_korean_font():
    """스트림릿 클라우드 환경을 위한 나눔고딕 폰트 다운로드"""
    if not os.path.exists(FONT_PATH):
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        urllib.request.urlretrieve(font_url, FONT_PATH)


download_korean_font()


# --- 2. 유튜브 API 함수 정의 ---
def extract_video_id(url):
    """유튜브 URL에서 Video ID 추출"""
    regex = r"(?:v=|\/([0-9A-Za-z_-]{11}).*[\?&]v=|^you\.tu\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else None


def get_youtube_comments(api_key, video_id, max_results=200):
    """유튜브 댓글 수집"""
    youtube = build("youtube", "v3", developerKey=api_key)
    comments = []

    try:
        request = youtube.commentThreads().list(
            part="snippet", videoId=video_id, maxResults=100, textFormat="plainText"
        )

        while request and len(comments) < max_results:
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append(
                    {
                        "author": snippet["authorDisplayName"],
                        "comment": snippet["textDisplay"],
                        "like_count": snippet["likeCount"],
                        "published_at": snippet["publishedAt"],
                    }
                )

            # 다음 페이지 토큰 확인
            request = youtube.commentThreads().list_next(
                previous_request=request, previous_response=response
            )

    except Exception as e:
        st.error(f"댓글을 불러오는 중 오류가 발생했습니다: {e}")
        return None

    return pd.DataFrame(comments)


# --- 3. UI 레이아웃 ---
st.title("🎥 유튜브 댓글 분석기")
st.markdown("유튜브 영상 URL을 입력하면 댓글 데이터 시각화 결과를 제공합니다.")

# 사이드바: Secrets 또는 직접 입력받는 API 키
with st.sidebar:
    st.header("🔑 설정")
    # Streamlit Secrets에 저장된 키가 있으면 가져오고, 없으면 직접 입력받음
    default_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
    api_key = st.text_input(
        "YouTube API Key", value=default_api_key, type="password"
    )

video_url = st.text_input(
    "유튜브 영상 링크 입력",
    placeholder="https://www.youtube.com/watch?v=...",
)
max_comments = st.slider("수집할 최대 댓글 수", 50, 500, 200, step=50)

if st.button("댓글 분석 시작"):
    if not api_key:
        st.warning("YouTube API 키를 입력해 주세요.")
    elif not video_url:
        st.warning("유튜브 영상 링크를 입력해 주세요.")
    else:
        video_id = extract_video_id(video_url)

        if not video_id:
            st.error("올바른 유튜브 URL 형식이 아닙니다.")
        else:
            with st.spinner("댓글을 수집하고 분석 중입니다..."):
                df = get_youtube_comments(api_key, video_id, max_comments)

            if df is not None and not df.empty:
                st.success(f"총 {len(df)}개의 댓글을 성공적으로 가져왔습니다!")

                #탭 구분
                tab1, tab2, tab3 = st.tabs(
                    ["📊 데이터 요약 및 시각화", "☁️ 워드 클라우드", "📋 Raw 데이터"]
                )

                # TAB 1: 주요 지표 및 기본 차트
                with tab1:
                    col1, col2 = st.columns(2)
                    col1.metric("총 댓글 수", f"{len(df)}개")
                    col2.metric("총 좋아요 수", f"{df['like_count'].sum()}개")

                    st.subheader("👍 좋아요를 가장 많이 받은 상위 댓글 Top 5")
                    top_liked = df.sort_values(
                        by="like_count", ascending=False
                    ).head(5)
                    for idx, row in top_liked.iterrows():
                        st.write(
                            f"**{row['author']}** (👍 {row['like_count']})"
                        )
                        st.caption(f"{row['comment']}")
                        st.divider()

                    st.subheader("📈 댓글 좋아요 수 분포")
                    st.bar_chart(df["like_count"].value_counts().head(10))

                # TAB 2: 한글 워드 클라우드
                with tab2:
                    st.subheader("💬 자주 등장하는 단어 (Word Cloud)")
                    text = " ".join(df["comment"].dropna())

                    # 간단한 특수문자 제거
                    text = re.sub(r"[^\w\s]", "", text)

                    if text.strip():
                        wc = WordCloud(
                            font_path=FONT_PATH,
                            background_color="white",
                            width=800,
                            height=400,
                            max_words=100,
                        ).generate(text)

                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.imshow(wc, interpolation="bilinear")
                        ax.axis("off")
                        st.pyplot(fig)
                    else:
                        st.info("시각화할 텍스트 데이터가 부족합니다.")

                # TAB 3: 원본 데이터 테이블 및 CSV 다운로드
                with tab3:
                    st.dataframe(df)
                    csv = df.to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        label="CSV로 다운로드",
                        data=csv,
                        file_name=f"youtube_comments_{video_id}.csv",
                        mime="text/csv",
                    )
