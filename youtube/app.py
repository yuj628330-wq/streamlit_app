import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
import re
import os
from io import BytesIO
from datetime import datetime

# --------------------------------------------------
# Streamlit 설정
# --------------------------------------------------

st.set_page_config(
    page_title="YouTube 댓글 분석기",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# CSS
# --------------------------------------------------

st.markdown("""
<style>

.main{
    padding-top:20px;
}

.block-container{
    padding-top:1rem;
}

.metric-card{
    background:#f7f7f7;
    padding:15px;
    border-radius:15px;
}

.stButton>button{
    width:100%;
    border-radius:10px;
    height:45px;
    font-size:18px;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 제목
# --------------------------------------------------

st.title("📊 YouTube 댓글 분석기")

st.caption("YouTube 댓글을 수집하고 다양한 통계와 시각화를 제공합니다.")

# --------------------------------------------------
# Github Secret API
# --------------------------------------------------

try:
    API_KEY = st.secrets["YOUTUBE_API_KEY"]

except Exception:
    st.error("YOUTUBE_API_KEY가 secrets.toml에 없습니다.")
    st.stop()

# --------------------------------------------------
# Youtube API
# --------------------------------------------------

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)

# --------------------------------------------------
# 영상ID 추출
# --------------------------------------------------

def get_video_id(url):

    if "youtu.be/" in url:
        return url.split("/")[-1].split("?")[0]

    parsed = urlparse(url)

    if parsed.hostname in [
        "www.youtube.com",
        "youtube.com"
    ]:

        if parsed.path == "/watch":
            return parse_qs(parsed.query)["v"][0]

        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/")[2]

        if parsed.path.startswith("/embed/"):
            return parsed.path.split("/")[2]

    return None

# --------------------------------------------------
# 영상정보 가져오기
# --------------------------------------------------

def get_video_info(video_id):

    request = youtube.videos().list(
        part="snippet,statistics",
        id=video_id
    )

    response = request.execute()

    if len(response["items"]) == 0:
        return None

    item = response["items"][0]

    snippet = item["snippet"]
    stat = item["statistics"]

    return {

        "title":
            snippet["title"],

        "channel":
            snippet["channelTitle"],

        "published":
            snippet["publishedAt"],

        "thumbnail":
            snippet["thumbnails"]["high"]["url"],

        "views":
            int(stat.get("viewCount",0)),

        "likes":
            int(stat.get("likeCount",0)),

        "comments":
            int(stat.get("commentCount",0))

    }

# --------------------------------------------------
# 댓글 수집
# --------------------------------------------------

def get_comments(video_id):

    comments=[]

    next_page=None

    while True:

        request = youtube.commentThreads().list(

            part="snippet,replies",

            videoId=video_id,

            maxResults=100,

            pageToken=next_page,

            textFormat="plainText"

        )

        response=request.execute()

        for item in response["items"]:

            top=item["snippet"]["topLevelComment"]["snippet"]

            comments.append({

                "작성자":top["authorDisplayName"],

                "댓글":top["textDisplay"],

                "좋아요":top["likeCount"],

                "작성일":top["publishedAt"],

                "답글수":item["snippet"]["totalReplyCount"]

            })

            if "replies" in item:

                for reply in item["replies"]["comments"]:

                    r=reply["snippet"]

                    comments.append({

                        "작성자":r["authorDisplayName"],

                        "댓글":r["textDisplay"],

                        "좋아요":r["likeCount"],

                        "작성일":r["publishedAt"],

                        "답글수":0

                    })

        next_page=response.get("nextPageToken")

        if not next_page:
            break

    return pd.DataFrame(comments)

# --------------------------------------------------
# Sidebar
# --------------------------------------------------

st.sidebar.header("⚙️ 설정")

video_url = st.sidebar.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=..."
)

analyze = st.sidebar.button("🚀 댓글 분석 시작")

# --------------------------------------------------
# 메인 화면
# --------------------------------------------------

if not analyze:

    st.info("좌측에서 유튜브 URL을 입력한 후 '댓글 분석 시작' 버튼을 누르세요.")

    st.stop()

video_id = get_video_id(video_url)

if video_id is None:

    st.error("올바른 유튜브 URL이 아닙니다.")

    st.stop()

progress = st.progress(0)

status = st.empty()

status.info("영상 정보를 가져오는 중...")

progress.progress(10)

video = get_video_info(video_id)

if video is None:

    st.error("영상을 찾을 수 없습니다.")

    st.stop()

status.info("댓글을 수집하는 중입니다...")

progress.progress(30)

# --------------------------------------------------
# 댓글 수집
# --------------------------------------------------

df = get_comments(video_id)

progress.progress(70)

status.info("데이터를 정리하는 중입니다...")

if df.empty:

    st.warning("댓글이 존재하지 않는 영상입니다.")

    st.stop()

# --------------------------------------------------
# 데이터 전처리
# --------------------------------------------------

df["댓글"] = df["댓글"].astype(str)

df["댓글길이"] = df["댓글"].str.len()

df["작성일"] = pd.to_datetime(df["작성일"])

df["작성시간"] = df["작성일"].dt.hour

df["작성날짜"] = df["작성일"].dt.date

df = df.sort_values("작성일")

progress.progress(80)

status.info("통계를 계산하는 중입니다...")

# --------------------------------------------------
# 통계
# --------------------------------------------------

total_comments = len(df)

total_authors = df["작성자"].nunique()

avg_length = round(df["댓글길이"].mean(), 1)

avg_like = round(df["좋아요"].mean(), 2)

max_like = df["좋아요"].max()

total_reply = df["답글수"].sum()

progress.progress(90)

status.info("화면을 생성하는 중입니다...")

# --------------------------------------------------
# 영상 정보 출력
# --------------------------------------------------

st.image(video["thumbnail"], width=400)

st.subheader(video["title"])

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("조회수", f"{video['views']:,}")

with col2:
    st.metric("좋아요", f"{video['likes']:,}")

with col3:
    st.metric("댓글수", f"{video['comments']:,}")

st.write("---")

# --------------------------------------------------
# 댓글 통계
# --------------------------------------------------

st.header("📈 댓글 통계")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("총 댓글", f"{total_comments:,}")

with c2:
    st.metric("작성자 수", f"{total_authors:,}")

with c3:
    st.metric("평균 댓글 길이", avg_length)

c4, c5, c6 = st.columns(3)

with c4:
    st.metric("평균 좋아요", avg_like)

with c5:
    st.metric("최고 좋아요", max_like)

with c6:
    st.metric("답글 수", total_reply)

st.write("---")

# --------------------------------------------------
# 탭 생성
# --------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "💬 댓글",
        "📊 통계",
        "📈 그래프",
        "☁️ 워드클라우드",
        "😊 감성분석"
    ]
)

# --------------------------------------------------
# 탭1 댓글
# --------------------------------------------------

with tab1:

    st.subheader("댓글 목록")

    keyword = st.text_input("댓글 검색")

    temp = df.copy()

    if keyword:

        temp = temp[
            temp["댓글"].str.contains(
                keyword,
                case=False,
                na=False
            )
        ]

    st.dataframe(
        temp,
        use_container_width=True,
        height=600
    )

# --------------------------------------------------
# 탭2 통계
# --------------------------------------------------

with tab2:

    st.subheader("기초 통계")

    st.dataframe(
        df.describe(include="all"),
        use_container_width=True
    )

    st.subheader("상위 좋아요 댓글")

    st.dataframe(
        df.sort_values(
            "좋아요",
            ascending=False
        ).head(20),
        use_container_width=True
    )

progress.progress(100)

status.success("분석 완료!")

