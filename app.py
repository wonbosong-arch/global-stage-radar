import streamlit as st
import hmac
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from stage_engine import weekly_bars, relative_return_difference, classify_stage
from kis_provider import KISDomesticPrices, KISError
from universe import read_universe
from market_data import normalize_ohlcv
from data_providers import KISUSProvider, KISKoreaProvider

st.set_page_config(page_title="Global Stage Analysis", page_icon="📈", layout="wide")
st.title("🌍 Global Stage Analysis Radar")
st.caption("데이터 정확성 우선 MVP · 주간 장기 추세 · 최종 판단은 투자자가 수행")
st.warning("KIS API 모드는 미국·한국 주식/ETF의 소규모 조회용 초기 연동입니다. 권리·호출 제한 검증 전에는 개인 연구용으로만 사용하세요. 데모는 가상 데이터입니다.")

PRICE_COLS = {"date", "symbol", "open", "high", "low", "close", "volume"}

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

def get_secret(name):
    try:
        return st.secrets.get(name)
    except Exception:
        return None

def read_prices(file):
    d = pd.read_csv(file)
    d.columns = [str(x).strip().lower() for x in d.columns]
    missing = PRICE_COLS - set(d.columns)
    if missing: raise ValueError("가격 CSV 필수 열 누락: " + ", ".join(sorted(missing)))
    return normalize_ohlcv(d)

with st.sidebar:
    st.header("데이터")
    mode = st.radio("모드", ["가상 데모", "CSV 업로드", "KIS API · 미국주식"])
    if mode == "KIS API · 미국주식":
        expected_password = get_secret("APP_PASSWORD")
        if not expected_password:
            st.error(
                "보안을 위해 KIS 실시간 조회가 잠겨 있습니다. "
                "Streamlit 앱 Settings → Secrets에 APP_PASSWORD를 강한 비밀번호로 설정하세요."
            )
            st.stop()
        if not st.session_state.get("kis_authenticated", False):
            with st.form("kis_access_form"):
                entered_password = st.text_input("KIS 모드 비밀번호", type="password")
                submitted = st.form_submit_button("잠금 해제")
            if submitted:
                if hmac.compare_digest(entered_password.encode("utf-8"), str(expected_password).encode("utf-8")):
                    st.session_state["kis_authenticated"] = True
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")
            st.info("KIS API 키가 호스팅된 앱에서 사용되므로, 본인만 아는 강한 비밀번호로 보호합니다.")
            st.stop()
        if st.button("KIS 모드 잠그기"):
            st.session_state["kis_authenticated"] = False
            st.rerun()
    pf = uf = None
    fetch_kis = False
    if mode == "CSV 업로드":
        pf = st.file_uploader("일별 가격 CSV", type=["csv"])
        uf = st.file_uploader("종목 유니버스 CSV", type=["csv"])
    elif mode == "KIS API · 미국주식":
        uf = st.file_uploader("미국·한국 주식/ETF 유니버스 CSV", type=["csv"])
        st.caption("미국: NAS / NYS / AMS · 한국: KRX. 기타 시장과 원자재 시리즈는 CSV 모드를 사용하세요.")
        fetch_kis = st.button("KIS에서 가격 조회", type="primary")
    st.divider()
    min_cap_b = st.number_input(
        "최소 시가총액 (USD, $B)",
        min_value=0.0,
        value=1.0,
        step=0.5,
        help="예: 1.0 = 10억 달러, 1000 = 1조 달러",
    )
    min_cap = min_cap_b * 1_000_000_000

try:
    if mode == "가상 데모":
        universe, prices = demo_data()
    elif mode == "CSV 업로드":
        if pf is None or uf is None:
            st.info("가격 CSV와 종목 유니버스 CSV를 모두 업로드하세요.")
            st.stop()
        universe, prices = read_universe(uf), read_prices(pf)
    else:
        if uf is None:
            st.info("미국주식 종목 유니버스 CSV를 업로드하세요.")
            st.stop()
        universe = read_universe(uf)
        if fetch_kis:
            try:
                kis = KISDomesticPrices(
                    app_key=get_secret("KIS_APP_KEY"),
                    app_secret=get_secret("KIS_APP_SECRET"),
                )
                us_provider = KISUSProvider(kis)
                kr_provider = KISKoreaProvider(kis)
                unsupported = universe[~universe.apply(
                    lambda row: (
                        us_provider.supports(row["market"], row["asset_type"])
                        or kr_provider.supports(row["market"], row["asset_type"])
                    ),
                    axis=1,
                )]
                if not unsupported.empty:
                    examples = ", ".join(unsupported["symbol"].astype(str).head(10))
                    st.error(
                        "현재 KIS 연동은 미국 및 한국 상장 주식·ETF만 지원합니다. "
                        f"CSV 모드로 기타 시장/원자재 시리즈를 불러오세요. 지원되지 않는 예시: {examples}"
                    )
                    st.stop()
                frames = []
                targets = universe[["symbol", "exchange"]].drop_duplicates()
                # The current KIS adapter is a small-watchlist pilot. Avoid
                # accidental long-running bulk requests until quotas are verified.
                if len(targets) > 50:
                    st.error(
                        f"KIS API 모드는 현재 최대 50개 종목까지 지원합니다. "
                        f"현재 유니버스: {len(targets)}개. 작은 목록으로 나누어 조회하세요."
                    )
                    st.stop()
                if targets.empty:
                    st.error("조회할 종목이 없습니다.")
                    st.stop()
                progress = st.progress(0, text="KIS 일봉 데이터 조회 중...")
                fetch_errors = []
                for i, item in enumerate(targets.itertuples(index=False), start=1):
                    row = universe.loc[universe["symbol"].eq(item.symbol)].iloc[0]
                    provider = (
                        kr_provider
                        if kr_provider.supports(row["market"], row["asset_type"])
                        else us_provider
                    )
                    try:
                        bars = provider.fetch_daily(
                            item.symbol,
                            market=row["market"],
                            asset_type=row["asset_type"],
                            exchange=item.exchange,
                            max_pages=10,
                        )
                        if not bars.empty:
                            frames.append(bars)
                        else:
                            fetch_errors.append({"symbol": item.symbol, "error": "조회 결과가 비어 있습니다."})
                    except Exception as symbol_error:
                        fetch_errors.append({
                            "symbol": item.symbol,
                            "error": f"{type(symbol_error).__name__}: {str(symbol_error)[:250]}",
                        })
                    progress.progress(i / len(targets), text=f"KIS 조회: {item.symbol} ({i}/{len(targets)})")
                progress.empty()
                st.session_state["kis_fetch_errors"] = fetch_errors
                if not frames:
                    st.error("시세를 가져온 종목이 없습니다. 아래 조회 오류를 확인하세요.")
                    st.dataframe(pd.DataFrame(fetch_errors), use_container_width=True, hide_index=True)
                    st.stop()
                st.session_state["kis_prices"] = pd.concat(frames, ignore_index=True)
                st.session_state["kis_universe_symbols"] = tuple(
                    map(tuple, universe[["symbol", "exchange", "market", "asset_type"]].astype(str).to_numpy())
                )
            except Exception as e:
                st.error(f"KIS 조회 실패: {e}")
                st.stop()
        cached_symbols = st.session_state.get("kis_universe_symbols")
        requested_symbols = tuple(
            map(tuple, universe[["symbol", "exchange", "market", "asset_type"]].astype(str).to_numpy())
        )
        if "kis_prices" not in st.session_state or cached_symbols != requested_symbols:
            st.info("종목 유니버스를 확인한 뒤 왼쪽의 'KIS에서 가격 조회'를 누르세요.")
            st.stop()
        prices = st.session_state["kis_prices"]
        fetch_errors = st.session_state.get("kis_fetch_errors", [])
        if fetch_errors:
            st.warning(f"KIS 조회에 실패했거나 데이터가 없는 종목: {len(fetch_errors)}개")
            with st.expander("종목별 KIS 조회 오류"):
                st.dataframe(pd.DataFrame(fetch_errors), use_container_width=True, hide_index=True)
except Exception as e:
    st.error(str(e)); st.stop()

# Enforce the same OHLCV quality contract for demo, CSV and live-provider data.
try:
    prices = normalize_ohlcv(prices)
except ValueError as e:
    st.error(f"가격 데이터 검증 실패: {e}")
    st.stop()

symbols = set(prices.symbol.unique())
universe = universe[universe.symbol.isin(symbols)].copy()
weekly_by_symbol = {s: weekly_bars(g) for s,g in prices.groupby("symbol")}
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
            w["rs_"+key+"_26w_pct"] = relative_return_difference(w, weekly_by_symbol[bench], 26).to_numpy()
        else:
            # A benchmark compared with itself has no meaningful relative-return value.
            w["rs_"+key+"_26w_pct"] = np.nan
    last = w.iloc[-1]
    label = classify_stage(
        close=last.close,
        ma30=last.ma30,
        slope4_pct=last.slope4_pct,
        market_rs=last.rs_market_26w_pct,
        sector_rs=last.rs_sector_26w_pct,
        asset_type=item.asset_type,
    )
    rows.append({**item.to_dict(),"last_date":last.date,"close":last.close,"ma30":last.ma30,"slope4_pct":last.slope4_pct,"ret13_pct":last.ret13_pct,"ret26_pct":last.ret26_pct,"rs_market_26w_pct":last.rs_market_26w_pct,"rs_sector_26w_pct":last.rs_sector_26w_pct,"vol_ratio":last.vol_ratio,"stage_label":label})
    weekly_by_symbol[s] = w

screen = pd.DataFrame(rows)
if screen.empty:
    st.error("분석할 종목이 없습니다. 종목별 35주 이상의 가격 데이터가 필요합니다."); st.stop()
stock = screen.asset_type.astype(str).str.lower().eq("stock")
screen = screen[~stock | (screen.market_cap_usd.notna() & (screen.market_cap_usd >= min_cap))]
asset_type = st.selectbox("자산 유형", ["전체","주식","시장 ETF","업종 ETF","원자재 ETF","원자재 시리즈"])
type_map = {"주식":"stock","시장 ETF":"market_etf","업종 ETF":"sector_etf","원자재 ETF":"commodity_etf","원자재 시리즈":"commodity"}
if asset_type != "전체": screen = screen[screen.asset_type.astype(str).str.lower() == type_map[asset_type]]

if mode == "가상 데모": st.info("가상 데이터입니다. 실제 시세·시장 분류·시가총액을 반영하지 않습니다.")
elif mode == "KIS API · 미국주식": st.info("KIS 미국/한국 실제 시세를 조회합니다. 시가총액·업종 분류는 업로드한 유니버스 CSV의 값이며 자동 검증되지 않습니다.")
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
display_view = view[[x for x in cols if x in view.columns]].copy()
if "market_cap_usd" in display_view.columns:
    display_view["market_cap_usd"] = (display_view["market_cap_usd"] / 1_000_000_000).round(2)
    display_view = display_view.rename(columns={"market_cap_usd": "market_cap ($B)"})
st.dataframe(display_view.sort_values("rs_market_26w_pct",ascending=False,na_position="last"),use_container_width=True,hide_index=True)

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
    st.write("asset_type 값: stock, market_etf, sector_etf, commodity_etf, commodity")
    st.write("벤치마크 심볼도 가격 CSV에 포함해야 시장 및 업종 대비 상대강도를 계산할 수 있습니다.")
    st.write("Stage 2 후보: 종가가 30주선 위, 30주선의 4주 기울기 양수, 시장 및 업종 대비 26주 상대수익률 양수.")
    st.write("Stage 2A 관찰 후보는 초기 스크리닝을 위한 내부 분류명이며 와인스타인의 공식 단계 명칭이 아닙니다.")
    st.write("이 로직은 초기 규칙이며, 수익성 검증 또는 투자 권고가 아닙니다.")

st.download_button("현재 스크리닝 CSV 다운로드",screen.to_csv(index=False).encode("utf-8-sig"),file_name="stage_screen.csv",mime="text/csv")
