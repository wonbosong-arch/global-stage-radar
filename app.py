import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(
    page_title="Global Stage 2 Trend Radar",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (모바일 반응형 & 파이낸스 터미널 스타일)
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e222d; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39; }
    .stage2-badge { background-color: #0e6251; color: #2ecc71; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .stage1-badge { background-color: #7d6608; color: #f1c40f; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .stage4-badge { background-color: #78281f; color: #e74c3c; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 스탠 와인스타인 Stage Analysis 핵심 엔진
# ---------------------------------------------------------
@st.cache_data(ttl=3600*12)  # 12시간 캐싱
def fetch_and_analyze(ticker, benchmark_df=None):
    try:
        # 주봉 데이터 수집 (최근 2년치)
        stock = yf.Ticker(ticker)
        df = stock.history(period="2y", interval="1wk")
        if len(df) < 35:
            return None
        
        # 30주 이동평균선 (SMA 30)
        df['SMA30'] = df['Close'].rolling(window=30).mean()
        # 10주 평균 거래량
        df['Vol_MA10'] = df['Volume'].rolling(window=10).mean()
        # 30주선 기울기 (4주 전 대비 변화율 %)
        df['SMA30_Slope'] = ((df['SMA30'] - df['SMA30'].shift(4)) / df['SMA30'].shift(4)) * 100
        
        # Mansfield RS (벤치마크 대비 상대강도)
        if benchmark_df is not None:
            combined = pd.DataFrame({'Stock': df['Close'], 'Bench': benchmark_df['Close']}).dropna()
            r_ratio = combined['Stock'] / combined['Bench']
            base_ma = r_ratio.rolling(window=30).mean()
            df['Mansfield_RS'] = ((r_ratio / base_ma) - 1) * 100
        else:
            df['Mansfield_RS'] = 0.0

        latest = df.iloc[-1]
        prev_4wk = df.iloc[-5] if len(df) >= 5 else df.iloc[0]

        # Stage 판별 로직
        price_above_sma = latest['Close'] > latest['SMA30']
        sma_sloping_up = latest['SMA30_Slope'] > 0.3
        volume_surge = latest['Volume'] > (latest['Vol_MA10'] * 1.3)
        rs_positive = latest['Mansfield_RS'] > 0

        # 최근 52주 박스권 돌파 여부
        recent_52w_high = df['Close'].iloc[-52:-1].max() if len(df) >= 52 else df['Close'].iloc[:-1].max()
        is_breakout = latest['Close'] >= (recent_52w_high * 0.98)

        # Stage 정의
        if price_above_sma and sma_sloping_up:
            if volume_surge and is_breakout:
                stage = "🔥 Stage 2 초입 (Breakout)"
            else:
                stage = "Stage 2 (상승 진행)"
        elif not price_above_sma and latest['SMA30_Slope'] < -0.3:
            stage = "Stage 4 (하락기)"
        else:
            stage = "Stage 1/3 (바닥/고점 혼조)"

        return {
            'ticker': ticker,
            'price': round(latest['Close'], 2),
            'sma30': round(latest['SMA30'], 2),
            'slope': round(latest['SMA30_Slope'], 2),
            'volume_ratio': round(latest['Volume'] / latest['Vol_MA10'], 2) if latest['Vol_MA10'] > 0 else 1.0,
            'rs': round(latest['Mansfield_RS'], 2),
            'stage': stage,
            'df': df
        }
    except Exception as e:
        return None

# ---------------------------------------------------------
# 2. 유니버스 정의
# ---------------------------------------------------------
MACRO_UNIVERSE = {
    'S&P 500': '^GSPC', 'NASDAQ': '^IXIC', 'KOSPI': '^KS11', 'Nikkei 225': '^N225',
    '구리 (Copper)': 'HG=F', '금 (Gold)': 'GC=F', 'WTI 원유': 'CL=F', '미국 10년물 금리': '^TNX'
}

SECTOR_UNIVERSE = {
    '반도체 (SMH)': 'SMH', '정보기술 (XLK)': 'XLK', '에너지 (XLE)': 'XLE',
    '금융 (XLF)': 'XLF', '산업재/방산 (XLI)': 'XLI', '유틸리티/전력 (XLU)': 'XLU',
    '한국 반도체 (KODEX)': '091160.KS', '한국 방산 (PLUS)': '445730.KS', '한국 2차전지 (TIGER)': '305540.KS'
}

# ---------------------------------------------------------
# 3. 대시보드 메인 UI
# ---------------------------------------------------------
st.title("🛡️ Global Stage 2 TrendRadar")
st.caption("스탠 와인스타인(Stan Weinstein) Stage Analysis 기반 글로벌 장기 추세 포착 시스템")

# 벤치마크 (S&P 500) 기본 수집
sp500_raw = yf.Ticker('^GSPC').history(period="2y", interval="1wk")

tabs = st.tabs(["🌐 1단계: 거시 시장 & 독립 원자재", "🏭 2단계: 주도 업종/섹터 RS", "🔍 3단계: Stage 2 초입 스크리너"])

# --- Tab 1: 거시 시장 ---
with tabs[0]:
    st.subheader("글로벌 핵심 지수 및 독립 원자재 국면")
    cols = st.columns(4)
    idx = 0
    for name, symbol in MACRO_UNIVERSE.items():
        res = fetch_and_analyze(symbol, sp500_raw)
        if res:
            with cols[idx % 4]:
                st.metric(label=name, value=f"${res['price']:,}" if '=' in symbol or '^' in symbol else f"{res['price']:,}", delta=f"30주선 기울기: {res['slope']}%")
                st.caption(f"상태: **{res['stage']}**")
            idx += 1

# --- Tab 2: 주도 업종 ---
with tabs[1]:
    st.subheader("섹터 및 업종별 상대강도(Mansfield RS) 및 Stage")
    sector_data = []
    for name, symbol in SECTOR_UNIVERSE.items():
        res = fetch_and_analyze(symbol, sp500_raw)
        if res:
            sector_data.append({
                "업종/섹터명": name,
                "현재가": res['price'],
                "30주 이동평균": res['sma30'],
                "30주선 기울기(%)": res['slope'],
                "거래량 급증 비율": f"{res['volume_ratio']}x",
                "Mansfield RS": res['rs'],
                "Stage 국면": res['stage']
            })
    if sector_data:
        st.dataframe(pd.DataFrame(sector_data), use_container_width=True)

# --- Tab 3: 최종 스크리너 ---
with tabs[2]:
    st.subheader("🔥 현재 Stage 2 초입 (Breakout) 포착 자산")
    all_symbols = {**MACRO_UNIVERSE, **SECTOR_UNIVERSE}
    breakout_list = []
    for name, symbol in all_symbols.items():
        res = fetch_and_analyze(symbol, sp500_raw)
        if res and "Stage 2" in res['stage']:
            breakout_list.append(res)
    
    if breakout_list:
        for item in breakout_list:
            with st.expander(f"📌 {item['ticker']} - {item['stage']} (RS: {item['rs']})", expanded=True):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.write(f"**현재가:** {item['price']}")
                    st.write(f"**30주선 기울기:** {item['slope']}%")
                    st.write(f"**주봉 거래량:** 평소 대비 {item['volume_ratio']}배")
                with col2:
                    # 차트 시각화
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=item['df'].index, open=item['df']['Open'], high=item['df']['High'], low=item['df']['Low'], close=item['df']['Close'], name='주가'))
                    fig.add_trace(go.Scatter(x=item['df'].index, y=item['df']['SMA30'], mode='lines', name='30주선 (SMA30)', line=dict(color='orange', width=2)))
                    fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("현재 Stage 2 초입 조건(돌파+거래량 폭증)을 만족하는 자산이 없습니다.")