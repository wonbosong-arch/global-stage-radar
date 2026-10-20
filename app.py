import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 페이지 기본 설정
st.set_page_config(
    page_title="Global Stage 2 Trend Radar",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 가독성 최적화 커스텀 CSS (텍스트 명암 및 고대비)
# ---------------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #ffffff !important;
    }
    .stCaption {
        color: #b0b8c4 !important;
        font-size: 0.9rem !important;
    }
    [data-testid="stMetric"] {
        background-color: #1a1f2c !important;
        padding: 16px !important;
        border-radius: 10px !important;
        border: 1px solid #3a4150 !important;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.3) !important;
    }
    [data-testid="stMetricLabel"] {
        color: #9aa5b5 !important;
        font-size: 1.0rem !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    .stDataFrame {
        background-color: #1a1f2c !important;
        border-radius: 8px !important;
    }
    .streamlit-expanderHeader {
        background-color: #222938 !important;
        color: #ffffff !important;
        border-radius: 6px !important;
        font-size: 1.05rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 차트 생성 헬퍼 함수
# ---------------------------------------------------------
def draw_stage_chart(df, name):
    fig = go.Figure()
    # 캔들스틱 차트
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name='주가'
    ))
    # 30주 이동평균선
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['SMA30'],
        mode='lines',
        name='30주선 (SMA 30)',
        line=dict(color='#ff9f43', width=2.5)
    ))
    fig.update_layout(
        title=f"{name} (주봉 30주선 추세 분석)",
        height=320,
        margin=dict(l=10, r=10, t=35, b=10),
        template="plotly_dark",
        xaxis_rangeslider_visible=False
    )
    return fig

# ---------------------------------------------------------
# 1. 스탠 와인스타인 Stage Analysis 핵심 엔진
# ---------------------------------------------------------
@st.cache_data(ttl=3600*12)  # 12시간 캐싱
def fetch_and_analyze(ticker, benchmark_df=None):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2y", interval="1wk")
        
        # 데이터가 부족하거나 없을 경우 예외 처리
        if df.empty or len(df) < 35:
            return None
        
        # 30주 이동평균선 (SMA 30)
        df['SMA30'] = df['Close'].rolling(window=30).mean()
        # 10주 평균 거래량
        df['Vol_MA10'] = df['Volume'].rolling(window=10).mean()
        # 30주선 기울기 (4주 전 대비 변화율 %)
        df['SMA30_Slope'] = ((df['SMA30'] - df['SMA30'].shift(4)) / df['SMA30'].shift(4)) * 100
        
        # Mansfield RS (벤치마크 대비 상대강도)
        if benchmark_df is not None and not benchmark_df.empty:
            combined = pd.DataFrame({'Stock': df['Close'], 'Bench': benchmark_df['Close']}).dropna()
            r_ratio = combined['Stock'] / combined['Bench']
            base_ma = r_ratio.rolling(window=30).mean()
            df['Mansfield_RS'] = ((r_ratio / base_ma) - 1) * 100
        else:
            df['Mansfield_RS'] = 0.0

        latest = df.iloc[-1]

        # Stage 판별 로직
        price_above_sma = latest['Close'] > latest['SMA30']
        sma_sloping_up = latest['SMA30_Slope'] > 0.3
        volume_surge = latest['Volume'] > (latest['Vol_MA10'] * 1.2) if latest['Vol_MA10'] > 0 else False
        
        recent_52w_high = df['Close'].iloc[-52:-1].max() if len(df) >= 52 else df['Close'].iloc[:-1].max()
        is_breakout = latest['Close'] >= (recent_52w_high * 0.97)

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
            'sma30': round(latest['SMA30'], 2) if pd.notnull(latest['SMA30']) else 0,
            'slope': round(latest['SMA30_Slope'], 2) if pd.notnull(latest['SMA30_Slope']) else 0,
            'volume_ratio': round(latest['Volume'] / latest['Vol_MA10'], 2) if (pd.notnull(latest['Vol_MA10']) and latest['Vol_MA10'] > 0) else 1.0,
            'rs': round(latest['Mansfield_RS'], 2) if pd.notnull(latest['Mansfield_RS']) else 0,
            'stage': stage,
            'df': df
        }
    except Exception:
        return None

# ---------------------------------------------------------
# 2. 유니버스 정의 (안정적인 글로벌 ETF 중심 리밸런싱)
# ---------------------------------------------------------
MACRO_UNIVERSE = {
    'S&P 500': '^GSPC', 
    'NASDAQ': '^IXIC', 
    'KOSPI': '^KS11', 
    'Nikkei 225': '^N225',
    '구리 ETF (CPER)': 'CPER', 
    '금 ETF (GLD)': 'GLD', 
    '원유 ETF (USO)': 'USO', 
    '미국 10년물 금리': '^TNX'
}

SECTOR_UNIVERSE = {
    '반도체 (SMH)': 'SMH', 
    '정보기술 (XLK)': 'XLK', 
    '에너지 (XLE)': 'XLE',
    '금융 (XLF)': 'XLF', 
    '산업재/방산 (XLI)': 'XLI', 
    '유틸리티/전력 (XLU)': 'XLU',
    '한국 반도체 (KODEX)': '091160.KS', 
    '한국 방산 (PLUS)': '445730.KS', 
    '한국 2차전지 (TIGER)': '305540.KS'
}

# ---------------------------------------------------------
# 3. 대시보드 메인 UI
# ---------------------------------------------------------
st.title("🛡️ Global Stage 2 TrendRadar")
st.caption("스탠 와인스타인(Stan Weinstein) Stage Analysis 기반 글로벌 장기 추세 포착 시스템")

# 벤치마크 (S&P 500) 데이터 수집
sp500_raw = yf.Ticker('^GSPC').history(period="2y", interval="1wk")

tabs = st.tabs(["🌐 1단계: 거시 시장 & 독립 원자재", "🏭 2단계: 주도 업종/섹터 RS", "🔍 3단계: Stage 2 초입 스크리너"])

# --- Tab 1: 거시 시장 ---
with tabs[0]:
    st.markdown("### 📌 글로벌 핵심 지수 및 독립 원자재 국면")
    
    macro_results = {}
    cols = st.columns(4)
    idx = 0
    
    for name, symbol in MACRO_UNIVERSE.items():
        res = fetch_and_analyze(symbol, sp500_raw)
        if res:
            macro_results[name] = res
            with cols[idx % 4]:
                st.metric(
                    label=name, 
                    value=f"${res['price']:,}" if symbol not in ['^KS11', '^N225'] else f"{res['price']:,}", 
                    delta=f"30주선 기울기: {res['slope']}%"
                )
                st.caption(f"상태: **{res['stage']}**")
            idx += 1
        else:
            with cols[idx % 4]:
                st.warning(f"{name} 데이터 로딩 실패")
            idx += 1

    st.markdown("---")
    st.markdown("### 📊 거시 자산별 상세 차트 확인")
    selected_macro = st.selectbox("차트를 볼 지수/원자재를 선택하세요:", list(macro_results.keys()))
    if selected_macro and selected_macro in macro_results:
        m_item = macro_results[selected_macro]
        st.plotly_chart(draw_stage_chart(m_item['df'], selected_macro), use_container_width=True)

# --- Tab 2: 주도 업종 ---
with tabs[1]:
    st.markdown("### 📌 섹터 및 업종별 상대강도(Mansfield RS) 및 Stage")
    
    sector_results = {}
    sector_table_data = []
    
    for name, symbol in SECTOR_UNIVERSE.items():
        res = fetch_and_analyze(symbol, sp500_raw)
        if res:
            sector_results[name] = res
            sector_table_data.append({
                "업종/섹터명": name,
                "현재가": res['price'],
                "30주 이동평균": res['sma30'],
                "30주선 기울기(%)": res['slope'],
                "거래량 급증 비율": f"{res['volume_ratio']}x",
                "Mansfield RS": res['rs'],
                "Stage 국면": res['stage']
            })
            
    if sector_table_data:
        st.dataframe(pd.DataFrame(sector_table_data), use_container_width=True)

    st.markdown("---")
    st.markdown("### 📊 섹터/업종별 상세 차트 확인")
    selected_sector = st.selectbox("차트를 볼 섹터/업종을 선택하세요:", list(sector_results.keys()))
    if selected_sector and selected_sector in sector_results:
        s_item = sector_results[selected_sector]
        st.plotly_chart(draw_stage_chart(s_item['df'], selected_sector), use_container_width=True)

# --- Tab 3: 최종 스크리너 ---
with tabs[2]:
    st.markdown("### 🔥 현재 Stage 2 (상승 진입 및 진행) 포착 자산")
    
    all_symbols = {**MACRO_UNIVERSE, **SECTOR_UNIVERSE}
    breakout_list = []
    
    for name, symbol in all_symbols.items():
        res = fetch_and_analyze(symbol, sp500_raw)
        if res and "Stage 2" in res['stage']:
            res['display_name'] = name
            breakout_list.append(res)
    
    if breakout_list:
        for item in breakout_list:
            with st.expander(f"📌 [{item['display_name']}] - {item['stage']} (RS: {item['rs']})", expanded=True):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.write(f"**티커:** {item['ticker']}")
                    st.write(f"**현재가:** {item['price']}")
                    st.write(f"**30주선 기울기:** {item['slope']}%")
                    st.write(f"**주봉 거래량:** 평소 대비 {item['volume_ratio']}배")
                    st.write(f"**Mansfield RS:** {item['rs']}")
                with col2:
                    st.plotly_chart(draw_stage_chart(item['df'], item['display_name']), use_container_width=True)
    else:
        st.info("현재 Stage 2 조건(30주선 우상향 및 돌파)을 만족하는 자산이 없습니다.")