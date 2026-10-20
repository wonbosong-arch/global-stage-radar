import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Global Stage Analysis", page_icon="📈", layout="wide")
st.title("🌍 Global Stage Analysis Radar")
st.caption("데이터 정확성 우선 MVP · 주간 장기 추세 · 최종 판단은 투자자가 수행")
st.warning("실제 시세 API는 아직 연결하지 않았습니다. 데모는 가상 데이터이며 실제 투자 판단에 사용하지 마세요.")

PRICE_COLS = {"date", "symbol", "open", "high", "low", "close", "volume"}
UNIVERSE_COLS = {"symbol", "name", "market", "sector", "asset_type", "market_cap_usd", "market_benchmark", "sector_benchmark"}

@st.cache_data
def demo_data():
    rng = np.random.default_rng(42)
    rows = [
        ("USMKT","US Market Proxy","United States","Market","market_etf",np.nan,"USMKT","USMKT"),
        ("TECH","Technology Proxy","United States","Technology","sector_etf",np.nan,"USMKT","TECH"),
        ("SEMI","Semiconductor Proxy","United States","Semiconductors","sector_etf",np.nan,"USMKT","TECH"),
        ("GOLD","Gold Proxy","Commodities","Precious Metals","commodity",np.nan,"USMKT","GOLD"),
        ("OIL","Oil Proxy","Commodities","Energy","commodity",np.nan,"USMKT","OIL"),
        ("ALFA","Example Semiconductor Co.","United States","Semiconductors","stock",8e9,"USMKT","TECH"),
        ("BETA","Example Equipment Co.","United States","Semiconductors","stock",2.5e9,"USMKT","TECH"),
        ("GAMMA","Example Software Co.","United States","Technology","stock",15e9,"USMKT","TECH"),
        ("DELTA","Example Small Co.","United States","Technology","stock",650e6,"USMKT","TECH"),
    ]
    u = pd.DataFrame(rows, columns=["symbol","name","market","sector","asset_type","market_cap_usd","market_benchmark","sector_benchmark"])
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=1000)
    prices = []
    drift = {"USMKT":.0004,"TECH":.00065,"SEMI":.0009,"GOLD":.0002,"OIL":.0001,"ALFA":.0009,"BETA":.0007,"GAMMA":.0006,"DELTA":-.0001}
    for sym in u.symbol:
        r = rng.normal(drift[sym], .015, len(dates))
        if sym in ["SEMI","ALFA","BETA"]:
            r[int(len(dates)*.72):] += .001
        c = 80*np.exp(np.cumsum(r))
        o = c*(1+rng.normal(0,.003,len(dates)))
        prices.append(pd.DataFrame({"date":dates,"symbol":sym,"open":o,"high":np.maximum(o,c)*1.01,"low":np.minimum(o,c)*.99,"close":c,"volume":rng.integers(200000,1800000,len(dates))}))
    return u, pd.concat(prices, ignore_index=True)

def read_universe(file):
    d = pd.read_csv(file)
    d.columns = [str(x).strip().lower() for x in d.columns]
    missing = UNIVERSE_COLS - set(d.columns)
    if missing: raise ValueError("종목 유니버스 필수 열 누락: " + ", ".join(sorted(missing)))
    d["symbol"] = d.symbol.astype(str).str.strip()
    d["market_cap_usd"] = pd.to_numeric(d.market_cap_usd, errors="coerce")
    return d.drop_duplicates("symbol")

def read_prices(file):
    d = pd.read_csv(file)
    d.columns = [str(x).strip().lower() for x in d.columns]
    missing = PRICE_COLS - set(d.columns)
    if missing: raise ValueError("가격 CSV 필수 열 누락: " + ", ".join(sorted(missing)))
    d["date"] = pd.to_datetime(d.date, errors="coerce")
    d["symbol"] = d.symbol.astype(str).str.strip()
    for c in ["open","high","low","close","volume"]: d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["date","symbol","close"])
    return d[d.close > 0].drop_duplicates(["symbol","date"]).sort_values(["symbol","date"])

def weekly(d):
    d = d.sort_values("date").set_index("date")
    w = d.resample("W-FRI").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna(subset=["close"]).reset_index()
    if len(w) < 35: return None
    w["ma30"] = w.close.rolling(30).mean()
    w["slope4_pct"] = (w.ma30 / w.ma30.shift(4) - 1)*100
    w["ret13_pct"] = w.close.pct_change(13)*100
    w["ret26_pct"] = w.close.pct_change(26)*100
    w["vol_ratio"] = w.volume / w.volume.rolling(10).mean()
    return w

with st.sidebar:
    st.header("데이터")
    mode = st.radio("모드", ["가상 데모", "CSV 업로드"])
    if mode == "CSV 업로드":
        pf = st.file_uploader("일별 가격 CSV", type=["csv"])
        uf = st.file_uploader("종목 유니버스 CSV", type=["csv"])
    else:
        pf = uf = None
    st.divider()
    min_cap = st.number_input("최소 시가총액 (USD)", min_value=0, value=1_000_000_000, step=500_000_000)

try:
    if mode == "가상 데모":
        universe, prices = demo_data()
    else:
        if pf is None or uf is None:
            st.info("가격 CSV와 종목 유니버스 CSV를 모두 업로드하세요.")
            st.stop()
        universe, prices = read_universe(uf), read_prices(pf)
except Exception as e:
    st.error(str(e)); st.stop()

symbols = set(prices.symbol.unique())
universe = universe[universe.symbol.isin(symbols)].copy()
weekly_by_symbol = {s: weekly(g) for s,g in prices.groupby("symbol")}
weekly_by_symbol = {s:w for s,w in weekly_by_symbol.items() if w is not None}

rows = []
for _, item in universe.iterrows():
    s = item.symbol
    if s not in weekly_by_symbol: continue
    w = weekly_by_symbol[s].copy()
    last = w.iloc[-1]
    mkt, sec = item.market_benchmark, item.sector_benchmark
    for key, bench in [("market",mkt),("sector",sec)]:
        if bench in weekly_by_symbol and bench != s:
            b = weekly_by_symbol[bench].set_index("date").close.pct_change(26)*100
            own = w.set_index("date").close.pct_change(26)*100
            w["rs_"+key+"_26w_pct"] = own - b.reindex(w.date).to_numpy()
        else:
            w["rs_"+key+"_26w_pct"] = np.nan
    last = w.iloc[-1]
    above = pd.notna(last.ma30) and last.close > last.ma30
    slope_up = pd.notna(last.slope4_pct) and last.slope4_pct > 0
    rs_m = pd.notna(last.rs_market_26w_pct) and last.rs_market_26w_pct > 0
    rs_s = pd.notna(last.rs_sector_26w_pct) and last.rs_sector_26w_pct > 0
    if above and slope_up and rs_m and rs_s: label = "Stage 2 후보"
    elif above and pd.notna(last.slope4_pct) and last.slope4_pct > -0.5 and rs_m: label = "Stage 2A 관찰 후보"
    elif not above and pd.notna(last.slope4_pct) and last.slope4_pct < -0.5: label = "하락 추세 관찰"
    else: label = "중립 / 추가 확인"
    rows.append({**item.to_dict(),"last_date":last.date,"close":last.close,"ma30":last.ma30,"slope4_pct":last.slope4_pct,"ret13_pct":last.ret13_pct,"ret26_pct":last.ret26_pct,"rs_market_26w_pct":last.rs_market_26w_pct,"rs_sector_26w_pct":last.rs_sector_26w_pct,"vol_ratio":last.vol_ratio,"stage_label":label})
    weekly_by_symbol[s] = w

screen = pd.DataFrame(rows)
if screen.empty:
    st.error("분석할 종목이 없습니다. 종목별 35주 이상의 가격 데이터가 필요합니다."); st.stop()
stock = screen.asset_type.astype(str).str.lower().eq("stock")
screen = screen[~stock | (screen.market_cap_usd.notna() & (screen.market_cap_usd >= min_cap))]
asset_type = st.selectbox("자산 유형", ["전체","주식","시장 ETF","업종 ETF","원자재"])
type_map = {"주식":"stock","시장 ETF":"market_etf","업종 ETF":"sector_etf","원자재":"commodity"}
if asset_type != "전체": screen = screen[screen.asset_type.astype(str).str.lower() == type_map[asset_type]]

if mode == "가상 데모": st.info("가상 데이터입니다. 실제 시세·시장 분류·시가총액을 반영하지 않습니다.")
markets = sorted(screen.market.dropna().astype(str).unique())
m = st.selectbox("① 시장 선택", ["전체 시장"]+markets)
view = screen if m == "전체 시장" else screen[screen.market == m]
sectors = sorted(view.sector.dropna().astype(str).unique())
sec = st.selectbox("② 업종 / 원자재 그룹", ["전체 그룹"]+sectors)
view = view if sec == "전체 그룹" else view[view.sector == sec]

a,b,c,d = st.columns(4)
a.metric("표시 자산",len(view))
b.metric("Stage 2 후보",int((view.stage_label=="Stage 2 후보").sum()))
c.metric("Stage 2A 관찰",int((view.stage_label=="Stage 2A 관찰 후보").sum()))
d.metric("데이터 기준일",str(pd.to_datetime(view.last_date).max().date()) if len(view) else "N/A")

cols = ["symbol","name","market","sector","asset_type","market_cap_usd","close","ma30","slope4_pct","rs_market_26w_pct","rs_sector_26w_pct","vol_ratio","stage_label","last_date"]
st.subheader("③ 스크리닝 결과")
st.dataframe(view[[x for x in cols if x in view.columns]].sort_values("rs_market_26w_pct",ascending=False,na_position="last"),use_container_width=True,hide_index=True)

if len(view):
    labels = (view.symbol.astype(str)+" — "+view.name.astype(str)).tolist()
    selected = st.selectbox("차트 열기",labels)
    sym = selected.split(" — ",1)[0]
    chart = weekly_by_symbol[sym]
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=chart.date,open=chart.open,high=chart.high,low=chart.low,close=chart.close,name="주간 가격"))
    fig.add_trace(go.Scatter(x=chart.date,y=chart.ma30,name="30주 이동평균선",line=dict(width=2)))
    fig.update_layout(height=500,xaxis_rangeslider_visible=False)
    st.plotly_chart(fig,use_container_width=True)
    st.line_chart(chart.set_index("date")[["rs_market_26w_pct","rs_sector_26w_pct"]])
    st.bar_chart(chart.set_index("date")[["volume"]])

with st.expander("CSV 형식 및 판정 로직"):
    st.write("가격 CSV 열: date, symbol, open, high, low, close, volume")
    st.write("유니버스 CSV 열: symbol, name, market, sector, asset_type, market_cap_usd, market_benchmark, sector_benchmark")
    st.write("asset_type 값: stock, market_etf, sector_etf, commodity")
    st.write("벤치마크 심볼도 가격 CSV에 포함해야 시장 및 업종 대비 상대강도를 계산할 수 있습니다.")
    st.write("Stage 2 후보: 종가가 30주선 위, 30주선의 4주 기울기 양수, 시장 및 업종 대비 26주 상대수익률 양수.")
    st.write("Stage 2A 관찰 후보는 초기 스크리닝을 위한 내부 분류명이며 와인스타인의 공식 단계 명칭이 아닙니다.")
    st.write("이 로직은 초기 규칙이며, 수익성 검증 또는 투자 권고가 아닙니다.")

st.download_button("현재 스크리닝 CSV 다운로드",screen.to_csv(index=False).encode("utf-8-sig"),file_name="stage_screen.csv",mime="text/csv")
