import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="🌱 초보자용 주식 분석기", layout="centered")
st.title("🌱 주식 초보를 위한 친절한 분석기")
st.write("궁금한 회사의 이름을 입력하면, 어려운 용어 없이 쉽게 설명해 드릴게요!")

# 한글 주식명을 종목 코드(Ticker)로 바꿔주는 간단한 사전
# (실제 서비스 시에는 더 많은 종목이나 한국투자증권/네이버금융 API 연동을 추천합니다)
TICKER_MAP = {
    "삼성전자": "005930.KS",
    "애플": "AAPL",
    "테슬라": "TSLA",
    "마이크로소프트": "MSFT",
    "카카오": "035720.KS",
    "네이버": "035420.KS"
}

# 2. 사용자 검색창
user_input = st.text_input("🔍 주식 이름 입력 (예: 삼성전자, 애플)", "")

if user_input:
    # 딕셔너리에 있으면 코드를 가져오고, 없으면 입력한 영문 티커를 그대로 사용
    ticker_symbol = TICKER_MAP.get(user_input, user_input)
    
    with st.spinner('정보를 꼼꼼히 모으고 있어요... ⏳'):
        try:
            stock = yf.Ticker(ticker_symbol)
            info = stock.info
            
            # 화폐 단위 설정 (한국 주식은 ₩, 미국은 $)
            currency = "₩" if info.get('currency') == 'KRW' else "$"
            
            st.divider()
            
            # --- [1] 회사 3줄 설명 ---
            st.subheader(f"🏢 {user_input} (은)는 어떤 회사인가요?")
            # yfinance는 기본적으로 영어 설명을 제공합니다. 
            # 초보자를 위해 주요 종목은 미리 준비된 한글 설명을 띄우고, 없으면 영문을 보여줍니다.
            kr_descriptions = {
                "삼성전자": "1. 한국을 대표하는 세계적인 반도체 및 가전제품 기업입니다.\n2. 스마트폰(갤럭시)과 메모리 반도체 시장에서 전 세계 1, 2위를 다투고 있습니다.\n3. 안정적인 수익을 바탕으로 꾸준히 배당금을 지급하는 주식으로 유명해요.",
                "애플": "1. 아이폰, 아이패드, 맥북 등을 만드는 글로벌 1등 IT 기업입니다.\n2. 전 세계 수많은 사람들이 애플의 생태계 안에서 제품을 반복해서 구매합니다.\n3. 충성도 높은 고객들을 바탕으로 엄청난 현금을 벌어들이고 있어요."
            }
            if user_input in kr_descriptions:
                st.info(kr_descriptions[user_input])
            else:
                summary = info.get('longBusinessSummary', '회사 정보를 불러올 수 없습니다.')
                st.info(f"(영어 원문 요약)\n\n{summary[:300]}...") # 긴 영어는 잘라서 보여줌
            
            # --- [2] 현재 주가 및 어제와 비교 ---
            # 최근 1년(1y) 데이터를 가져와서 활용
            hist = stock.history(period="1y")
            
            if len(hist) >= 2:
                current_price = hist['Close'].iloc[-1]
                yesterday_price = hist['Close'].iloc[-2]
                pct_change = ((current_price - yesterday_price) / yesterday_price) * 100
                
                st.subheader("💰 현재 주가")
                # st.metric을 사용하면 자동으로 화살표와 색상(빨강/초록)을 넣어줍니다.
                st.metric(
                    label="오늘의 가격", 
                    value=f"{currency}{current_price:,.2f}", 
                    delta=f"어제보다 {pct_change:.2f}%"
                )
            
            # --- [3] 과거 주가 비교 (3, 6, 9, 12개월 전) ---
            st.write("📅 **시간이 지나면서 가격이 어떻게 변했을까요?**")
            
            # 오늘을 기준으로 날짜 계산
            today = hist.index[-1]
            dates = {
                "3개월 전": today - pd.DateOffset(months=3),
                "6개월 전": today - pd.DateOffset(months=6),
                "9개월 전": today - pd.DateOffset(months=9),
                "1년 전": today - pd.DateOffset(months=12)
            }
            
            cols = st.columns(4)
            for i, (label, target_date) in enumerate(dates.items()):
                # 해당 날짜와 가장 가까운 과거의 주가를 찾음
                past_data = hist[hist.index <= target_date]
                if not past_data.empty:
                    past_price = past_data['Close'].iloc[-1]
                    cols[i].metric(label=label, value=f"{currency}{past_price:,.0f}")
                else:
                    cols[i].metric(label=label, value="데이터 없음")

            # --- [4] 주가 시각화 (그래프) ---
            st.subheader("📈 1년간 주가 흐름 보기")
            # 초보자가 보기 쉽게 종가(Close)만 추출해서 선 그래프로 그림
            st.line_chart(hist['Close'])

            # --- [5] 어려운 용어(PER, PBR, PSR) 쉽게 풀어 쓰기 ---
            st.divider()
            st.subheader("📊 회사의 현재 가치 평가 (쉬운 설명)")
            st.write("주식이 지금 비싼 편인지, 싼 편인지 확인하는 3가지 마법의 숫자예요.")

            # 1. PSR (주가매출비율)
            psr = info.get('priceToSalesTrailing12Months')
            if psr:
                psr_eval = "높은 편(기대감이 큼)" if psr > 3 else "낮은 편(저평가 가능성)"
                st.success(
                    f"**🛒 매출 대비 가치 (기존 용어: PSR)**\n\n"
                    f"이 회사의 전체 덩치(시가총액)는 1년 동안 물건을 팔아서 번 돈(매출)의 **{psr:.1f}배** 수준입니다. "
                    f"다른 일반적인 회사들과 비교했을 때 **{psr_eval}**이에요."
                )
            
            # 2. PER (주가수익비율)
            per = info.get('trailingPE')
            if per:
                per_eval = "높은 편(인기가 많거나 고평가)" if per > 15 else "낮은 편(저렴함)"
                st.warning(
                    f"**💸 이익 대비 가치 (기존 용어: PER)**\n\n"
                    f"이 회사의 가치는 1년 동안 '순수하게 남긴 이익'의 **{per:.1f}배**로 평가받고 있어요. "
                    f"일반적으로 10~15배를 적당하다고 보는데, 현재는 **{per_eval}**입니다. 숫자가 낮을수록 돈 버는 능력에 비해 주가가 싸다는 뜻이에요."
                )

            # 3. PBR (주가순자산비율)
            pbr = info.get('priceToBook')
            if pbr:
                pbr_eval = "프리미엄을 받고 있어요" if pbr > 1 else "가진 재산보다 주가가 더 싸게 거래되고 있어요"
                st.info(
                    f"**🏢 재산 대비 가치 (기존 용어: PBR)**\n\n"
                    f"회사가 가진 순수한 재산(자본)에 비해 주가가 **{pbr:.1f}배**입니다. "
                    f"즉, 회사가 당장 문을 닫고 재산을 다 팔아치운다고 가정했을 때, **{pbr_eval}**. (1보다 낮으면 아주 저렴하다는 뜻입니다.)"
                )

        except Exception as e:
            st.error("앗! 데이터를 불러오는 데 문제가 생겼어요. 주식 이름이나 코드를 다시 확인해 주세요.")
