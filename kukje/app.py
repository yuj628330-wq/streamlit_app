# 난민 보온 가이드 (Streamlit) - 보온재 냉각 실험 기반
# 실행: pip install streamlit numpy pandas  →  streamlit run app.py
import numpy as np, pandas as pd, streamlit as st

st.set_page_config(page_title="체온 지킴이", page_icon="🧣", layout="wide")

# ---------- 1. 실험 데이터 → 열저항 배율 ----------
Ta, C = 22.0, 150 * 4.18
t = np.array([0, 5, 10, 15, 20])
DATA = {"맨몸(대조군)": [45, 42.4, 39.4, 37.0, 35.5], "극세사 담요": [45, 44.3, 42.7, 40.9, 39.4],
        "양모": [45, 43.8, 41.6, 39.8, 38.3], "은박지": [45, 43.6, 40.7, 38.6, 36.9],
        "신문지": [45, 42.7, 39.4, 38.0, 36.4], "비닐/에어캡": [45, 40.8, 39.1, 38.2, 36.5]}
COST = {"맨몸(대조군)": "없음", "극세사 담요": "보통", "양모": "높음", "은박지": "매우 낮음",
        "신문지": "무료", "비닐/에어캡": "낮음"}

@st.cache_data
def fit():
    k = {n: -np.polyfit(t, np.log(np.array(v) - Ta), 1)[0] for n, v in DATA.items()}
    return {n: k["맨몸(대조군)"] / k[n] for n in k}  # 열저항 배율(대조군=1)
RATIO = fit()

# ---------- 2. 환경·사람 계수 (가정값: 보고서에 근거 명시 필요) ----------
WIND = {"바람 없음(실내·텐트)": 1.0, "약한 바람": 1.4, "강한 바람": 2.0}
WET = {"마름": 1.0, "약간 젖음": 1.5, "흠뻑 젖음": 2.5}
GROUND = {"깔개 있음": 1.0, "맨바닥·흙": 1.3, "눈·얼음 바닥": 1.6}
PEOPLE = {"성인": (60, 100, 6.0), "노인": (55, 80, 5.8), "어린이(약 8세)": (25, 60, 3.8),
          "영유아": (10, 35, 2.2)}  # 체중kg, 열생산W, 맨몸 열전달 W/℃

def simulate(ratio_total, Tenv, person, wind, wet, ground, hours=24, dt=30):
    m, P, G0 = PEOPLE[person]
    G = G0 * WIND[wind] * WET[wet] * GROUND[ground] / ratio_total
    Cb = m * 3500; T = 37.0; ts, Ts = [0], [T]
    for i in range(int(hours * 3600 / dt)):
        T += (P - G * (T - Tenv)) / Cb * dt
        T = min(T, 37.0)  # 더우면 땀 등으로 37℃ 유지(항상성)
        ts.append((i + 1) * dt / 3600); Ts.append(T)
    ts, Ts = np.array(ts), np.array(Ts)
    hit = np.where(Ts < 35)[0]
    return ts, Ts, (ts[hit[0]] if len(hit) else None), min(Tenv + P / G, 37.0)

def layered(mats):  # 직렬 단열: 열저항 증가분을 더함 (가정)
    return 1 + sum(RATIO[x] - 1 for x in mats) if mats else 1.0

# ---------- 3. 화면 ----------
st.title("🧣 체온 지킴이: 추위 속 보온 가이드")
st.caption("고등학교 동아리 실험(보온재별 냉각 실험)에 기반한 단순화 모델입니다. 의료적 판단을 대신하지 않습니다.")

with st.sidebar:
    st.header("① 환경")
    Tenv = st.slider("바깥 기온(℃)", -10, 35, 0)
    wind = st.radio("바람", list(WIND)); wet = st.radio("옷 상태", list(WET)); ground = st.radio("바닥", list(GROUND))
    st.header("② 사람")
    person = st.selectbox("누구인가요?", list(PEOPLE))
    st.header("③ 가진 보온재")
    mats = st.multiselect("겹쳐 쓸 재료", [m for m in RATIO if m != "맨몸(대조군)"], default=["신문지"])

tab1, tab2, tab3 = st.tabs(["🚨 위험도 진단", "📊 보온재 비교", "🔬 실험 근거"])

with tab1:
    ts, Ts, t35, Teq = simulate(layered(mats), Tenv, person, wind, wet, ground)
    _, Ts0, t35_0, _ = simulate(1.0, Tenv, person, wind, wet, ground)
    c1, c2, c3 = st.columns(3)
    c1.metric("35℃ 도달까지(현재 보온)", f"{t35:.1f}시간" if t35 else "24시간 내 안전")
    c2.metric("보온 없을 때", f"{t35_0:.1f}시간" if t35_0 else "24시간 내 안전")
    c3.metric("예상 평형 체온", f"{Teq:.1f}℃")
    if Tenv >= 25: st.info("🌞 기온이 높아 보온재가 필요하지 않습니다. 오히려 더위·탈수에 주의하고 그늘과 물을 확보하세요.")
    elif t35 is None: st.success("현재 조건에서는 24시간 안에 저체온증 기준에 도달하지 않을 것으로 예상됩니다.")
    elif t35 < 3: st.error("⚠️ 매우 위험: 즉시 바람을 피하고, 젖은 옷을 벗고, 보온재를 더하세요.")
    else: st.warning("주의: 시간이 지나면 위험해질 수 있습니다.")
    st.line_chart(pd.DataFrame({"현재 보온": Ts, "보온 없음": Ts0, "저체온증 기준": 35}, index=ts.round(2)),
                  x_label="시간(h)", y_label="심부 체온(℃)")
    st.subheader("✅ 지금 할 수 있는 행동")
    tips = []
    if WET[wet] > 1: tips.append("젖은 옷부터 벗기기 — 젖음은 열 손실을 크게 늘립니다.")
    if WIND[wind] > 1: tips.append("바람 막기 — 비닐/에어캡을 가장 바깥에 둘러 바람을 차단하세요.")
    if GROUND[ground] > 1: tips.append("바닥 단열 — 신문지·골판지를 여러 겹 깔아 전도를 막으세요.")
    if "극세사 담요" not in mats: tips.append("담요를 구할 수 있다면 극세사 담요가 실험에서 가장 효과적이었습니다.")
    if person != "성인": tips.append(f"{person}은(는) 체구가 작거나 열 생산이 적어 더 빨리 식습니다. 먼저 보호하세요.")
    tips.append("여러 명이 붙어 앉기, 머리·목 덮기, 따뜻한 음식 섭취(열 생산 연료).")
    for x in tips: st.markdown(f"- {x}")
    extra = (PEOPLE[person][2] * WIND[wind] * WET[wet] * GROUND[ground] * (37 - Tenv)) * (1 - 1 / layered(mats)) * 86400 / 4184
    if Tenv < 25: st.info(f"🍙 현재 보온재가 하루 동안 아껴 주는 열량 ≈ **{extra:,.0f} kcal** (주먹밥 약 {extra/180:.0f}개 분량, 항상성 유지 부담 감소)")

with tab2:
    rows = []
    for m in RATIO:
        _, _, h, _ = simulate(RATIO[m], Tenv, person, wind, wet, ground)
        rows.append({"보온재": m, "열저항 배율": round(RATIO[m], 2), "35℃까지(h)": round(h, 1) if h else ">24",
                     "비용": COST[m]})
    st.dataframe(pd.DataFrame(rows).sort_values("열저항 배율", ascending=False), hide_index=True)
    st.bar_chart(pd.Series(RATIO).sort_values(), horizontal=True)

with tab3:
    st.markdown("**뉴턴 냉각 법칙** T(t)=Tₐ+(T₀−Tₐ)e^(−kt), 실내 22℃, 물 150 mL")
    st.line_chart(pd.DataFrame(DATA, index=t), x_label="시간(분)", y_label="물 온도(℃)")
    st.markdown("""**한계**: 물병은 혈관 수축 등 음성 피드백이 없음 / 바람·젖음·바닥 계수와 인체 값은 문헌 기반 가정치 /
    겹침 효과는 단순 합산 가정 / 20분·1회 실험.""")
