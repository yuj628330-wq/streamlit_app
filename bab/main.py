import streamlit as st
import datetime
import random

# ==========================================
# 1. 페이지 기본 설정
# ==========================================
st.set_page_config(
    page_title="한대부고 급식 & 밸런스 게임",
    page_icon="🍱",
    layout="centered"
)

# ==========================================
# 2. 세션 상태(Session State) 초기화
# 데이터베이스 대신 데이터를 임시 저장하는 공간입니다.
# ==========================================
if 'lunch_reviews' not in st.session_state:
    st.session_state.lunch_reviews = []   # 중식 리뷰 저장 리스트
if 'dinner_reviews' not in st.session_state:
    st.session_state.dinner_reviews = []  # 석식 리뷰 저장 리스트
if 'votes_A' not in st.session_state:
    st.session_state.votes_A = 0          # 밸런스 게임 A 투표수
if 'votes_B' not in st.session_state:
    st.session_state.votes_B = 0          # 밸런스 게임 B 투표수
if 'bg_comments' not in st.session_state:
    st.session_state.bg_comments = []     # 밸런스 게임 댓글 저장 리스트

# ==========================================
# 3. 공통 함수: 리뷰 폼 및 목록 렌더링
# 중식과 석식 탭에서 공통으로 사용할 수 있도록 함수로 분리했습니다.
# ==========================================
def render_review_section(meal_type, reviews_list):
    # 리뷰 입력 폼
    with st.form(f"review_form_{meal_type}"):
        st.subheader(f"✏️ 오늘의 {meal_type} 평가하기")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            date = st.date_input("날짜", datetime.date.today(), key=f"date_{meal_type}")
        with col2:
            menu = st.text_input("주요 메뉴 (예: 마라탕, 꿔바로우)", key=f"menu_{meal_type}")
            
        rating = st.slider("별점 평가", min_value=1, max_value=5, value=5, help="1점: 아쉬워요, 5점: 최고예요!", key=f"rating_{meal_type}")
        review_text = st.text_input("한 줄 리뷰를 남겨주세요!", key=f"text_{meal_type}")
        
        submitted = st.form_submit_button("평가 등록 🚀")
        
        if submitted:
            if menu and review_text:
                # 새로운 리뷰 데이터를 딕셔너리 형태로 저장
                new_review = {
                    "date": date,
                    "menu": menu,
                    "rating": rating,
                    "review": review_text
                }
                # 최신 리뷰가 위로 오도록 리스트 맨 앞에 추가
                reviews_list.insert(0, new_review)
                st.success("성공적으로 등록되었습니다! 👏")
            else:
                st.warning("메뉴와 한 줄 리뷰를 모두 입력해주세요.")

    st.divider() # 구분선

    # 내일 급식 예상 만족도 (간단한 랜덤 + 평균 점수 로직)
    st.subheader("🔮 내일 급식 예상 만족도")
    if len(reviews_list) > 0:
        avg_rating = sum(r['rating'] for r in reviews_list) / len(reviews_list)
        expected_score = min(100, int((avg_rating * 15) + random.randint(10, 25)))
        st.info(f"지금까지의 평점을 분석한 결과, 내일 {meal_type} 만족도는 **{expected_score}%** 로 예상됩니다! 📈")
    else:
        st.info("평가 데이터가 쌓이면 내일의 급식 만족도를 예측해 드립니다! 🤔")

    st.divider()

    # 등록된 리뷰 표시 (최신순)
    st.subheader(f"💬 최근 {meal_type} 리뷰 모아보기")
    if not reviews_list:
        st.write("아직 등록된 리뷰가 없습니다. 첫 번째 리뷰를 남겨주세요! 😊")
    else:
        for idx, r in enumerate(reviews_list):
            # st.container(border=True)를 사용해 깔끔한 카드 UI 생성 (Streamlit 1.30+ 지원)
            with st.container(border=True):
                stars = "⭐" * r['rating'] + "🌑" * (5 - r['rating'])
                st.markdown(f"**🗓️ {r['date']}** | 🍽️ **{r['menu']}**")
                st.markdown(f"**평점:** {stars}")
                st.markdown(f"*{r['review']}*")

# ==========================================
# 4. 사이드바 (메뉴 네비게이션)
# ==========================================
st.sidebar.title("🦁 한대부고 급식 앱")
menu = st.sidebar.radio(
    "메뉴를 선택하세요👇",
    ["🍱 오늘의 급식 평가", "⚔️ 급식 밸런스 게임"]
)
st.sidebar.markdown("---")
st.sidebar.info("💡 **알림**: 이 앱은 새로고침 시 데이터가 초기화되는 테스트 버전입니다.")

# ==========================================
# 5. 메인 화면 구성
# ==========================================
if menu == "🍱 오늘의 급식 평가":
    st.title("🦁 한대부고 급식 평가 🍱")
    st.write("우리 학교 오늘 급식은 어땠나요? 솔직한 평가를 남겨주세요!")
    
    # 중식/석식 탭 분리
    tab1, tab2 = st.tabs(["🌞 중식 (점심)", "🌙 석식 (저녁)"])
    
    with tab1:
        render_review_section("중식", st.session_state.lunch_reviews)
        
    with tab2:
        render_review_section("석식", st.session_state.dinner_reviews)

elif menu == "⚔️ 급식 밸런스 게임":
    st.title("⚔️ 급식 밸런스 게임 📊")
    st.write("한대부고 학생들의 취향을 알아보는 시간! 당신의 선택은?")
    
    st.divider()
    
    # 밸런스 게임 질문
    st.subheader("🔥 Q. 평생 학교에서 한 가지 조합만 먹어야 한다면?")
    
    col1, col2 = st.columns(2)
    
    # 선택 버튼 및 투표 로직
    with col1:
        if st.button("🔴 제육볶음 + 포슬포슬 계란찜", use_container_width=True):
            st.session_state.votes_A += 1
    with col2:
        if st.button("🔵 바삭바삭 돈까스 + 매콤 쫄면", use_container_width=True):
            st.session_state.votes_B += 1

    # 투표 결과 실시간 계산
    total_votes = st.session_state.votes_A + st.session_state.votes_B
    if total_votes > 0:
        percent_A = int((st.session_state.votes_A / total_votes) * 100)
        percent_B = 100 - percent_A
        
        st.markdown("### 📊 실시간 투표 결과")
        
        # Streamlit 프로그레스 바를 활용한 시각화
        st.write(f"**🔴 제육+계란찜 ({percent_A}%)** - {st.session_state.votes_A}표")
        st.progress(percent_A / 100)
        
        st.write(f"**🔵 돈까스+쫄면 ({percent_B}%)** - {st.session_state.votes_B}표")
        st.progress(percent_B / 100)
    else:
        st.info("버튼을 눌러 첫 번째 투표자가 되어주세요! 👀")

    st.divider()

    # 댓글 기능
    st.subheader("💬 선택한 이유를 알려주세요!")
    with st.form("bg_comment_form"):
        col1, col2 = st.columns([1, 3])
        with col1:
            choice = st.selectbox("나의 선택", ["제육파", "돈까스파"])
        with col2:
            comment = st.text_input("이유 (예: 한국인은 밥심이지!)")
        
        comment_submitted = st.form_submit_button("댓글 남기기 ✍️")
        
        if comment_submitted and comment:
            st.session_state.bg_comments.insert(0, f"**[{choice}]** {comment}")

    # 댓글 목록 표시
    if st.session_state.bg_comments:
        for c in st.session_state.bg_comments:
            st.markdown(f"- {c}")
