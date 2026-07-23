import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="초보자용 주식 분석기", layout="wide")

# 제목 부분
st.title("🌱 주식 초보를 위한 친절한 분석기")
st.write("어려운 용어 없이 주식 정보를 쉽게 풀어서 알려드립니다.")

# 1. 주식 입력 받기
# 한국 주식은 종목코드.KS (예: 005930.KS), 미국 주식은 티커 (예: AAPL)를 입력해야 정확합니다.
stock_name = st.text_input("분석하고 싶은 주식의 코드나 이름을 입력하세요.", value="005930.KS")
st.caption("팁: 삼성전자는 005930.KS, 애플은 AAPL, 테슬라는 TSLA를 입력해보세요!")

if stock_name:
    try:
        # 데이터 불러오기
        ticker = yf.Ticker(stock_name)
        
        # 회사 정보 및 주가 데이터 가져오기 (최근 1년치)
        info = ticker.info
        hist = ticker.history(period="1y")
        
        if hist.empty:
            st.error("주식 정보를 찾을 수 없습니다. 코드를 확인해주세요.")
        else:
            # --- [A] 회사 설명 (3줄 요약) ---
            st.subheader(f"🏢 '{info.get('longName', stock_name)}'은 어떤 회사인가요?")
            full_desc = info.get('longBusinessSummary', '회사 설명 정보가 없습니다.')
            
            # 초보자를 위해 영문 설명을 간단히 3줄 정도로 요약 (앞부분 발췌)
            # (실제 한국어 번역 API는 유료가 많아 여기서는 앞부분을 잘라 보여줍니다)
            desc_lines = full_desc.split('.')[:3]
            summary = ".\n".join(desc_lines) + "."
            st.info(summary)

            # --- [B] 현재 주가 및 전일 대비 변동 ---
            current_price = hist['Close'].iloc[-1]
            yesterday_price = hist['Close'].iloc[-2]
            change_percent = ((current_price - yesterday_price) / yesterday_price) * 100
            
            currency = info.get('currency', '단위')
            
            st.divider()
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(label="현재 가격", value=f"{current_price:,.0f} {currency}", 
                          delta=f"{change_percent:.2f}% (어제 대비)")
            
            # --- [C] 과거 가격 비교 (3, 6, 9개월, 1년 전) ---
            def get_past_price(days_ago):
                target_date = datetime.now() - timedelta(days=days_ago)
                closest_price = hist.iloc[hist.index.get_indexer([target_date], method='nearest')[0]]['Close']
                return closest_price

            with col2:
                st.write("📅 **과거에는 얼마였을까요?**")
                p3 = get_past_price(90)
                p6 = get_past_price(180)
                p9 = get_past_price(270)
                p1y = get_past_price(365)
                
                past_df = pd.DataFrame({
                    "시점": ["3개월 전", "6개월 전", "9개월 전", "1년 전"],
                    "가격": [f"{p3:,.0f}", f"{p6:,.0f}", f"{p9:,.0f}", f"{p1y:,.0f}"]
                })
                st.table(past_df)

            # --- [D] 주가 시각화 ---
            st.subheader("📈 지난 1년간의 주가 흐름")
            st.line_chart(hist['Close'])

            # --- [E] 어려운 용어 풀이 (PSR, PER, PBR) ---
            st.divider()
            st.subheader("📊 이 주식은 지금 비싼가요, 싼가요?")
            st.write("어려운 용어 대신 쉽게 풀어서 설명해 드릴게요.")

            # 1. PSR 풀이
            psr = info.get('priceToSalesTrailing12Months', 0)
            if psr:
                psr_status = "높은" if psr > 5 else "낮은"
                st.success(f"**1. 매출액과 비교하기 (PSR):**\n\n 현재 이 회사의 전체 몸값은 1년 동안 물건을 팔아서 번 돈의 **{psr:.2f}배** 입니다. "
                           f"다른 비슷한 회사들과 비교했을 때 주가가 조금 **{psr_status}** 편에 속합니다.")

            # 2. PER 풀이
            per = info.get('trailingPE', 0)
            if per:
                per_status = "높은" if per > 20 else "낮은"
                st.warning(f"**2. 벌어들인 이익과 비교하기 (PER):**\n\n 현재 이 회사의 전체 몸값은 1년 동안 순수하게 남긴 이익의 **{per:.2f}배** 입니다. "
                           f"회사가 버는 돈에 비해 주가가 **{per_status}** 편입니다.")

            # 3. PBR 풀이
            pbr = info.get('priceToBook', 0)
            if pbr:
                pbr_status = "높은" if pbr > 1 else "낮은"
                st.info(f"**3. 회사가 가진 재산과 비교하기 (PBR):**\n\n 이 회사가 가진 모든 재산(건물, 기계 등)을 다 팔았을 때 나오는 돈보다 주가가 **{pbr:.2f}배** 비쌉니다. "
                        f"보통 1보다 낮으면 재산보다 주가가 싸다는 뜻인데, 현재는 **{pbr_status}** 상태입니다.")

    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
