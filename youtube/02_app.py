import html
import os
import re
from collections import Counter
from urllib.parse import parse_qs, urlparse

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from wordcloud import WordCloud


st.set_page_config(
    page_title="유튜브 댓글 분석기",
    page_icon="📺",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        max-width: 1450px;
    }
    .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 20px;
        background: linear-gradient(135deg, #fff4f4 0%, #f7f8ff 100%);
        border: 1px solid #ececf3;
        margin-bottom: 1.1rem;
    }
    .hero-title {
        font-size: 2.25rem;
        font-weight: 850;
        margin-bottom: 0.35rem;
    }
    .hero-sub {
        color: #60636b;
        font-size: 1rem;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e9e9ef;
        padding: 15px;
        border-radius: 16px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.035);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

DEFAULT_FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanskr/"
    "NotoSansKR%5Bwght%5D.ttf"
)

POSITIVE_WORDS = {
    "좋다", "좋아요", "좋은", "최고", "멋지다", "멋져", "훌륭", "감동",
    "재밌다", "재미있다", "재밌어요", "웃기다", "웃겨", "사랑", "행복",
    "추천", "감사", "고맙", "응원", "대박", "완벽", "유익", "도움",
    "신기", "예쁘다", "예뻐", "귀엽", "성공", "기대", "존경", "공감",
    "깔끔", "정확", "awesome", "great", "best", "amazing", "excellent",
    "love", "like", "fun", "funny", "helpful", "useful", "thanks",
    "thank", "beautiful", "perfect", "wow", "nice",
}

NEGATIVE_WORDS = {
    "싫다", "싫어", "별로", "최악", "나쁘다", "나빠", "실망", "화나다",
    "화나", "짜증", "재미없다", "노잼", "답답", "불편", "문제", "오류",
    "거짓", "무섭", "슬프", "혐오", "망했다", "실패", "아쉽", "걱정",
    "비추천", "지루", "심각", "욕", "쓰레기", "bad", "worst", "hate",
    "boring", "disappointing", "angry", "annoying", "problem", "error",
    "fail", "failed", "sad", "terrible", "awful", "poor", "scam", "fake",
}

POSITIVE_EMOJIS = {"😀", "😃", "😄", "😁", "😊", "😍", "🥰", "👍", "❤️", "❤", "👏", "🔥", "✨"}
NEGATIVE_EMOJIS = {"😡", "😠", "😤", "😢", "😭", "👎", "💔", "🤬"}

STOPWORDS = {
    "이", "그", "저", "것", "수", "등", "더", "좀", "잘", "정말", "진짜",
    "너무", "영상", "유튜브", "유투브", "댓글", "사람", "하는", "하고",
    "해서", "하면", "있는", "없는", "입니다", "있다", "없다", "같다",
    "그리고", "하지만", "에서", "으로", "에게", "까지", "부터",
    "ㅋㅋ", "ㅋㅋㅋ", "ㅎㅎ", "ㅎㅎㅎ", "ㅠㅠ", "ㅜㅜ",
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "to", "of", "in", "on", "for", "with", "this", "that", "it", "you",
    "i", "we", "they", "my", "your", "video", "youtube", "comment",
}


def get_api_key() -> str:
    try:
        return str(st.secrets["YOUTUBE_API_KEY"]).strip()
    except Exception:
        return ""


def extract_video_id(url_or_id: str) -> str | None:
    value = url_or_id.strip()

    if re.fullmatch(r"[\w-]{11}", value):
        return value

    try:
        parsed = urlparse(value)
        host = parsed.netloc.lower().replace("www.", "")

        if host == "youtu.be":
            candidate = parsed.path.strip("/").split("/")[0]
        elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
            if parsed.path == "/watch":
                candidate = parse_qs(parsed.query).get("v", [""])[0]
            elif parsed.path.startswith(("/shorts/", "/embed/", "/live/")):
                parts = parsed.path.strip("/").split("/")
                candidate = parts[1] if len(parts) > 1 else ""
            else:
                candidate = ""
        else:
            candidate = ""

        return candidate if re.fullmatch(r"[\w-]{11}", candidate) else None
    except Exception:
        return None


def youtube_get(endpoint: str, params: dict) -> dict:
    response = requests.get(
        f"{YOUTUBE_API_BASE}/{endpoint}",
        params=params,
        timeout=30,
    )

    if response.ok:
        return response.json()

    try:
        error_data = response.json()
        message = error_data.get("error", {}).get("message", response.text)
    except ValueError:
        message = response.text

    raise RuntimeError(f"YouTube API 오류 ({response.status_code}): {message}")


@st.cache_data(ttl=600, show_spinner=False)
def get_video_info(api_key: str, video_id: str) -> dict:
    data = youtube_get(
        "videos",
        {
            "part": "snippet,statistics",
            "id": video_id,
            "key": api_key,
        },
    )

    if not data.get("items"):
        raise RuntimeError("영상을 찾을 수 없습니다. 링크, 공개 상태 또는 API 키를 확인하세요.")

    item = data["items"][0]
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})

    return {
        "title": snippet.get("title", ""),
        "channel": snippet.get("channelTitle", ""),
        "published_at": snippet.get("publishedAt", ""),
        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        "view_count": int(statistics.get("viewCount", 0)),
        "like_count": int(statistics.get("likeCount", 0)),
        "comment_count": int(statistics.get("commentCount", 0)),
    }


@st.cache_data(ttl=600, show_spinner=False)
def get_comments(
    api_key: str,
    video_id: str,
    requested_count: int,
    order: str,
) -> pd.DataFrame:
    rows = []
    next_page_token = None

    while len(rows) < requested_count:
        page_size = min(100, requested_count - len(rows))

        params = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": page_size,
            "order": order,
            "textFormat": "plainText",
            "key": api_key,
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        data = youtube_get("commentThreads", params)

        for item in data.get("items", []):
            thread_snippet = item.get("snippet", {})
            top = thread_snippet.get("topLevelComment", {}).get("snippet", {})

            rows.append(
                {
                    "author": top.get("authorDisplayName", ""),
                    "comment": html.unescape(top.get("textDisplay", "")),
                    "published_at": top.get("publishedAt"),
                    "updated_at": top.get("updatedAt"),
                    "like_count": int(top.get("likeCount", 0)),
                    "reply_count": int(thread_snippet.get("totalReplyCount", 0)),
                }
            )

            if len(rows) >= requested_count:
                break

        next_page_token = data.get("nextPageToken")

        if not next_page_token or not data.get("items"):
            break

    df = pd.DataFrame(rows)

    if not df.empty:
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df["updated_at"] = pd.to_datetime(df["updated_at"], utc=True, errors="coerce")

    return df


def tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"https?://\S+|www\.\S+", " ", str(text).lower())
    cleaned = re.sub(r"[^0-9a-zA-Z가-힣ㄱ-ㅎㅏ-ㅣ']", " ", cleaned)
    return [token for token in cleaned.split() if len(token) >= 2]


def sentiment_result(text: str) -> tuple[str, int]:
    tokens = tokenize(text)

    positive = sum(
        1
        for token in tokens
        if token in POSITIVE_WORDS
        or any(word in token for word in POSITIVE_WORDS if len(word) >= 2)
    )

    negative = sum(
        1
        for token in tokens
        if token in NEGATIVE_WORDS
        or any(word in token for word in NEGATIVE_WORDS if len(word) >= 2)
    )

    positive += sum(str(text).count(emoji) for emoji in POSITIVE_EMOJIS)
    negative += sum(str(text).count(emoji) for emoji in NEGATIVE_EMOJIS)

    score = positive - negative

    if score > 0:
        return "긍정", score
    if score < 0:
        return "부정", score
    return "중립", 0


def choose_time_granularity(df: pd.DataFrame) -> str:
    valid = df["published_at"].dropna()

    if valid.empty:
        return "일별"

    span = valid.max() - valid.min()

    if span <= pd.Timedelta(days=3):
        return "시간별"
    if span <= pd.Timedelta(days=120):
        return "일별"
    if span <= pd.Timedelta(days=730):
        return "월별"
    return "연도별"


def aggregate_time(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    temp = df.dropna(subset=["published_at"]).copy()

    if temp.empty:
        return pd.DataFrame(columns=["작성 시점", "댓글 수"])

    korea_time = temp["published_at"].dt.tz_convert("Asia/Seoul")

    if granularity == "시간별":
        temp["작성 시점"] = korea_time.dt.floor("h")
    elif granularity == "일별":
        temp["작성 시점"] = korea_time.dt.floor("d")
    elif granularity == "월별":
        temp["작성 시점"] = (
            korea_time.dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
        )
    else:
        temp["작성 시점"] = korea_time.dt.year.astype(str)

    return temp.groupby("작성 시점").size().reset_index(name="댓글 수")


@st.cache_data(ttl=3600, show_spinner=False)
def get_korean_font(font_url: str) -> str:
    candidates = [
        "youtube/NanumGothic.ttf",
        "fonts/NanumGothic.ttf",
        "fonts/NotoSansKR.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/malgun.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    os.makedirs("fonts", exist_ok=True)
    font_path = "fonts/NotoSansKR.ttf"

    response = requests.get(font_url, timeout=30)
    response.raise_for_status()

    with open(font_path, "wb") as file:
        file.write(response.content)

    return font_path


def make_word_frequencies(
    comments: pd.Series,
    extra_stopwords: set[str],
) -> Counter:
    frequencies = Counter()
    stopwords = STOPWORDS | extra_stopwords

    for text in comments.fillna(""):
        for token in tokenize(text):
            if token not in stopwords and not token.isdigit():
                frequencies[token] += 1

    return frequencies


st.markdown(
    """
    <div class="hero">
        <div class="hero-title">📺 유튜브 댓글 분석기</div>
        <div class="hero-sub">
            영상 정보, 댓글 작성 추이, 긍정·부정 반응과 한글 워드클라우드를 한 번에 분석합니다.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

api_key = get_api_key()

if not api_key:
    st.error("Streamlit Secrets에 YOUTUBE_API_KEY가 등록되어 있지 않습니다.")
    st.code('YOUTUBE_API_KEY = "발급받은_API_키"', language="toml")
    st.stop()

with st.sidebar:
    st.header("⚙️ 분석 설정")
    st.success("✅ API 키가 자동으로 연결되었습니다.")

    video_url = st.text_input(
        "유튜브 영상 링크",
        placeholder="https://www.youtube.com/watch?v=...",
    )

    requested_count = st.number_input(
        "가져올 댓글 개수",
        min_value=10,
        max_value=5000,
        value=300,
        step=50,
        help="공개된 최상위 댓글을 가져옵니다. API 페이지당 최대 100개씩 요청됩니다.",
    )

    order_label = st.radio(
        "댓글 수집 순서",
        ["최신순", "관련도순"],
        horizontal=True,
        help="관련도순은 유튜브가 판단한 대표 댓글을 우선 수집합니다.",
    )

    extra_stopwords_text = st.text_input(
        "추가 제외 단어",
        placeholder="예: 채널명, 출연자명",
        help="쉼표로 여러 단어를 구분하세요.",
    )

    font_url = st.text_input(
        "한글 폰트 URL",
        value=DEFAULT_FONT_URL,
        help="GitHub raw 형식의 TTF/OTF 주소를 입력할 수 있습니다.",
    )

    analyze_clicked = st.button(
        "🔍 댓글 분석하기",
        type="primary",
        use_container_width=True,
    )

video_id = extract_video_id(video_url) if video_url else None

if video_url and video_id:
    st.video(f"https://www.youtube.com/watch?v={video_id}")
elif video_url:
    st.warning("올바른 유튜브 영상 링크 또는 11자리 영상 ID를 입력하세요.")

if analyze_clicked:
    if not video_id:
        st.error("올바른 유튜브 영상 링크를 입력하세요.")
        st.stop()

    order = "time" if order_label == "최신순" else "relevance"

    try:
        with st.spinner("영상 정보와 댓글을 불러오는 중입니다..."):
            video_info = get_video_info(api_key, video_id)
            comments_df = get_comments(
                api_key,
                video_id,
                int(requested_count),
                order,
            )
    except Exception as error:
        st.error(str(error))
        st.info(
            "API 키 제한 설정, YouTube Data API v3 활성화 여부, "
            "영상의 댓글 허용 여부를 확인하세요."
        )
        st.stop()

    if comments_df.empty:
        st.warning(
            "가져올 수 있는 공개 댓글이 없습니다. "
            "댓글이 비활성화되었거나 공개 댓글이 없을 수 있습니다."
        )
        st.stop()

    comments_df[["sentiment", "sentiment_score"]] = comments_df["comment"].apply(
        lambda text: pd.Series(sentiment_result(text))
    )

    comments_df["engagement_score"] = (
        comments_df["like_count"] + comments_df["reply_count"] * 2
    )

    st.session_state["comments_df"] = comments_df
    st.session_state["video_info"] = video_info
    st.session_state["extra_stopwords"] = extra_stopwords_text
    st.session_state["font_url"] = font_url
    st.session_state["video_id"] = video_id

if "comments_df" in st.session_state:
    df = st.session_state["comments_df"].copy()
    info = st.session_state["video_info"]
    result_video_id = st.session_state["video_id"]

    extra_stopwords = {
        word.strip().lower()
        for word in st.session_state.get("extra_stopwords", "").split(",")
        if word.strip()
    }

    st.subheader(info["title"])
    st.caption(
        f"채널: {info['channel']} · 분석 댓글: {len(df):,}개 · "
        f"공개 전체 댓글: {info['comment_count']:,}개"
    )

    metric_cols = st.columns(5)
    metric_cols[0].metric("조회 수", f"{info['view_count']:,}")
    metric_cols[1].metric("영상 좋아요", f"{info['like_count']:,}")
    metric_cols[2].metric("분석 댓글", f"{len(df):,}")
    metric_cols[3].metric("댓글 좋아요 합계", f"{df['like_count'].sum():,}")
    metric_cols[4].metric("답글 합계", f"{df['reply_count'].sum():,}")

    st.divider()
    st.subheader("📈 댓글 작성 추이")

    default_granularity = choose_time_granularity(df)
    granularity_options = ["시간별", "일별", "월별", "연도별"]

    granularity = st.selectbox(
        "집계 단위",
        granularity_options,
        index=granularity_options.index(default_granularity),
    )

    trend_df = aggregate_time(df, granularity)

    if trend_df.empty:
        st.info("작성 시점 데이터가 없어 추이를 표시할 수 없습니다.")
    else:
        trend_fig = px.line(
            trend_df,
            x="작성 시점",
            y="댓글 수",
            markers=True,
            title=f"{granularity} 댓글 수",
        )
        trend_fig.update_layout(hovermode="x unified")
        st.plotly_chart(trend_fig, use_container_width=True)

    st.divider()
    st.subheader("😊 댓글 반응도")

    left, right = st.columns(2)

    with left:
        sentiment_counts = (
            df["sentiment"]
            .value_counts()
            .reindex(["긍정", "중립", "부정"], fill_value=0)
            .reset_index()
        )
        sentiment_counts.columns = ["감성", "댓글 수"]

        sentiment_fig = px.pie(
            sentiment_counts,
            names="감성",
            values="댓글 수",
            hole=0.45,
            title="댓글 감성 분포",
        )
        st.plotly_chart(sentiment_fig, use_container_width=True)

    with right:
        reaction_summary = pd.DataFrame(
            {
                "반응": ["댓글 좋아요", "답글"],
                "수": [
                    int(df["like_count"].sum()),
                    int(df["reply_count"].sum()),
                ],
            }
        )

        reaction_fig = px.bar(
            reaction_summary,
            x="반응",
            y="수",
            text_auto=True,
            title="좋아요·답글 반응",
        )
        st.plotly_chart(reaction_fig, use_container_width=True)

    positive_ratio = (df["sentiment"] == "긍정").mean() * 100
    neutral_ratio = (df["sentiment"] == "중립").mean() * 100
    negative_ratio = (df["sentiment"] == "부정").mean() * 100
    avg_likes = df["like_count"].mean()

    score_cols = st.columns(4)
    score_cols[0].metric("긍정 비율", f"{positive_ratio:.1f}%")
    score_cols[1].metric("중립 비율", f"{neutral_ratio:.1f}%")
    score_cols[2].metric("부정 비율", f"{negative_ratio:.1f}%")
    score_cols[3].metric("평균 댓글 좋아요", f"{avg_likes:.1f}")

    st.caption(
        "감성 분류는 한국어·영어 키워드와 이모지를 활용한 간단한 사전 기반 분석입니다. "
        "반어법, 신조어, 문맥에 따라 실제 의미와 다를 수 있습니다."
    )

    st.divider()
    st.subheader("☁️ 댓글 한글 워드클라우드")

    frequencies = make_word_frequencies(df["comment"], extra_stopwords)

    min_frequency = st.slider(
        "워드클라우드 최소 등장 횟수",
        min_value=1,
        max_value=20,
        value=2,
    )

    filtered_freq = Counter(
        {
            word: count
            for word, count in frequencies.items()
            if count >= min_frequency
        }
    )

    if not filtered_freq:
        st.info("조건을 만족하는 단어가 없습니다. 최소 등장 횟수를 낮춰보세요.")
    else:
        try:
            font_path = get_korean_font(st.session_state.get("font_url", DEFAULT_FONT_URL))

            wordcloud = WordCloud(
                width=1400,
                height=700,
                background_color="white",
                font_path=font_path,
                max_words=150,
                collocations=False,
                random_state=42,
            ).generate_from_frequencies(filtered_freq)

            fig, ax = plt.subplots(figsize=(14, 7))
            ax.imshow(wordcloud, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

            top_words = pd.DataFrame(
                frequencies.most_common(20),
                columns=["단어", "등장 횟수"],
            )

            top_words_fig = px.bar(
                top_words.sort_values("등장 횟수"),
                x="등장 횟수",
                y="단어",
                orientation="h",
                title="상위 20개 단어",
                text_auto=True,
            )
            st.plotly_chart(top_words_fig, use_container_width=True)

        except Exception as error:
            st.error("한글 폰트를 불러오지 못했습니다.")
            st.code(str(error))

    st.divider()
    st.subheader("🔥 반응이 큰 댓글")

    top_n = st.slider(
        "표시할 댓글 수",
        min_value=5,
        max_value=30,
        value=10,
    )

    display_df = (
        df.nlargest(top_n, "engagement_score")[
            [
                "author",
                "comment",
                "published_at",
                "like_count",
                "reply_count",
                "sentiment",
            ]
        ]
        .rename(
            columns={
                "author": "작성자",
                "comment": "댓글",
                "published_at": "작성 시각",
                "like_count": "좋아요",
                "reply_count": "답글",
                "sentiment": "감성",
            }
        )
    )

    display_df["작성 시각"] = (
        display_df["작성 시각"]
        .dt.tz_convert("Asia/Seoul")
        .dt.strftime("%Y-%m-%d %H:%M")
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    csv_df = df.rename(
        columns={
            "author": "작성자",
            "comment": "댓글",
            "published_at": "작성 시각",
            "updated_at": "수정 시각",
            "like_count": "좋아요",
            "reply_count": "답글",
            "sentiment": "감성",
            "sentiment_score": "감성 점수",
            "engagement_score": "반응 점수",
        }
    )

    csv_data = csv_df.to_csv(
        index=False,
        encoding="utf-8-sig",
    ).encode("utf-8-sig")

    st.download_button(
        "⬇️ 분석 댓글 CSV 다운로드",
        data=csv_data,
        file_name=f"youtube_comments_{result_video_id}.csv",
        mime="text/csv",
        use_container_width=True,
    )

else:
    st.info(
        "왼쪽 설정에서 영상 링크와 댓글 개수를 설정한 뒤 "
        "**댓글 분석하기**를 누르세요."
    )

with st.expander("YouTube Data API 설정 안내"):
    st.markdown(
        """
        1. Google Cloud Console에서 프로젝트를 만듭니다.
        2. **API 및 서비스 → 라이브러리**에서 **YouTube Data API v3**를 활성화합니다.
        3. **사용자 인증 정보 → 사용자 인증 정보 만들기 → API 키**를 선택합니다.
        4. Streamlit Cloud 앱의 **Settings → Secrets**에 다음과 같이 저장합니다.

        ```toml
        YOUTUBE_API_KEY = "발급받은_API_키"
        ```

        공개 배포 시 Google Cloud Console에서 API 키 사용 제한을 설정하는 것이 좋습니다.
        """
    )
