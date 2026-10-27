import os
import json
from pathlib import Path
import streamlit as st
import hmac
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from stage_engine import weekly_bars, relative_return_difference, classify_stage, volume_confirmation, is_stale_daily_data, stage_data_freshness_status, stage_label_with_data_guards
from kis_provider import KISError
from kis_domestic_provider import KISDomesticPrices
from universe import read_universe
from candidate_stage_integration import extend_universe_with_approved_candidates
from market_data import normalize_ohlcv
from data_providers import KISUSProvider, KISKoreaProvider
from kis_universe import fetch_us_market_cap_candidates, fetch_korea_market_cap_candidates, fetch_us_security_master, audit_us_master_ranking_coverage, build_unranked_us_stock_master
from stock_mapping import proposed_stock_mapping
from krx_master import download_krx_master


def normalize_market_cap_candidates(raw: pd.DataFrame, min_cap_usd: float = 1_000_000_000,
                                    usdkrw=None) -> pd.DataFrame:
    """Normalize KIS ranking rows for review; instrument type is never auto-approved."""
    if min_cap_usd < 0:
        raise ValueError("min_cap_usd must be non-negative.")
    if usdkrw is not None and usdkrw <= 0:
        raise ValueError("usdkrw must be positive when supplied.")
    columns = [
        "symbol", "name", "exchange", "currency", "market_cap_native",
        "market_cap_usd", "instrument_type_guess", "master_instrument_type",
        "master_security_type_code", "is_adr_candidate", "master_dr_flag",
        "master_dr_country_code", "stock_eligible", "cap_threshold_pass",
        "review_status", "review_reason"
    ]
    if raw is None or raw.empty:
        return pd.DataFrame(columns=columns)

    frame = raw.copy()
    for col in ("listing_exchange", "symb", "ename", "name", "mksc_shrn_iscd",
                "hts_kor_isnm", "tomv", "stck_avls", "stck_prpr", "lstn_stcn", "last", "shar", "master_security_type", "master_dr_flag", "master_dr_country_code"):
        if col not in frame.columns:
            frame[col] = ""

    exchange = frame["listing_exchange"].astype(str).str.upper().str.strip()
    is_korea = exchange.eq("KRX")
    us_symbol = frame["symb"].astype(str).str.strip()
    kr_symbol = frame["mksc_shrn_iscd"].astype(str).str.strip()
    symbol = us_symbol.where(~is_korea, kr_symbol)
    name = frame["ename"].astype(str).str.strip().where(~is_korea,
                                                         frame["hts_kor_isnm"].astype(str).str.strip())
    name = name.where(name.ne(""), frame["name"].astype(str).str.strip())

    us_cap_raw = pd.to_numeric(frame["tomv"], errors="coerce")
    us_price = pd.to_numeric(frame["last"], errors="coerce")
    us_shares = pd.to_numeric(frame["shar"], errors="coerce")
    calculated_us_cap = us_price * us_shares
    us_unit_ratio = calculated_us_cap / us_cap_raw.where(us_cap_raw.ne(0))
    us_unit_verified = (
        us_unit_ratio.between(0.80, 1.20)
        & calculated_us_cap.notna()
        & us_cap_raw.gt(0)
    )
    us_cap = us_cap_raw.where(us_unit_verified)
    kr_cap_raw = pd.to_numeric(frame["stck_avls"], errors="coerce")
    kr_price = pd.to_numeric(frame.get("stck_prpr", pd.Series("", index=frame.index)), errors="coerce")
    kr_shares = pd.to_numeric(frame.get("lstn_stcn", pd.Series("", index=frame.index)), errors="coerce")
    calculated_kr_cap = kr_price * kr_shares
    unit_ratio = calculated_kr_cap / kr_cap_raw.where(kr_cap_raw.ne(0))
    kr_unit_verified = (
        unit_ratio.between(80_000_000, 120_000_000)
        & calculated_kr_cap.notna()
        & kr_cap_raw.gt(0)
    )
    kr_cap = (kr_cap_raw * 100_000_000).where(kr_unit_verified)
    native_cap = us_cap.where(~is_korea, kr_cap)
    currency = pd.Series("USD", index=frame.index).where(~is_korea, "KRW")
    cap_usd = us_cap.where(~is_korea, float("nan"))
    if usdkrw is not None:
        cap_usd = cap_usd.where(~is_korea, native_cap / float(usdkrw))

    searchable = (name.fillna("").astype(str) + " " +
                  frame["ename"].fillna("").astype(str) + " " +
                  frame["name"].fillna("").astype(str)).str.upper()
    fund_pattern = r"\b(?:ETF|ETN|TRUST|FUND|INDEX FUNDS|ISHARES|VANGUARD|SPDR|EXCHANGE TRADED|EXCHANGE-TRADED)\b"
    non_common_pattern = r"\b(?:CNV PREF|CONV(?:ERTIBLE)? PREF|PREFERRED|PREF SEC|GLOBAL NOTES|NOTES DUE|DEBENTURE|WARRANTS?|RIGHTS)\b"
    master_type = frame["master_security_type"].astype(str).str.strip()
    master_is_stock = master_type.eq("2")
    master_is_index = master_type.eq("1")
    master_is_etp = master_type.eq("3")
    master_is_warrant = master_type.eq("4")
    master_dr_flag = frame["master_dr_flag"].astype(str).str.strip().str.upper()
    master_dr_country_code = frame["master_dr_country_code"].astype(str).str.strip().str.upper()
    name_looks_adr = searchable.str.contains(
        r"\b(?:ADR|ADS|AMERICAN DEPOSITARY|DEPOSITARY RECEIPT|SPONSORED ADR|UNSPONSORED ADR)\b",
        regex=True, na=False,
    )
    master_marks_adr = master_dr_flag.isin({"1", "Y", "YES", "TRUE", "T"}) | (
        master_dr_country_code.ne("") & ~master_dr_country_code.isin({"US", "USA", "00", "0"})
    )
    is_adr = name_looks_adr | master_marks_adr
    # No depositary-ratio field is currently sourced, so do not pass ADR market cap
    # screening based on price × share-count consistency alone.
    native_cap = native_cap.where(~is_adr)
    cap_usd = cap_usd.where(~is_adr)
    likely_fund = searchable.str.contains(fund_pattern, regex=True, na=False) | master_is_etp
    likely_non_common = searchable.str.contains(non_common_pattern, regex=True, na=False) | master_is_warrant
    # The KIS master distinguishes stock, ETP, index and warrant; ordinary-common-equity status still needs review.
    type_guess = pd.Series("equity_candidate_unverified", index=frame.index)
    type_guess = type_guess.where(~likely_fund & ~likely_non_common, "fund_or_etf_likely")
    type_guess = type_guess.where(~(likely_non_common & ~likely_fund), "non_common_security_likely")
    type_guess = type_guess.where(~master_is_index, "index_security_master")
    type_guess = type_guess.where(~is_adr, "adr_candidate_unverified")
    master_instrument_type = master_type.map({
        "1": "index", "2": "stock", "3": "etp", "4": "warrant"
    }).fillna("unmatched_or_unknown")
    cap_pass = cap_usd.ge(float(min_cap_usd)).where(
        cap_usd.notna() & master_is_stock & ~likely_fund & ~likely_non_common & ~master_is_index & ~is_adr, pd.NA
    )
    reasons, statuses = [], []
    for idx in frame.index:
        why = []
        if not symbol.loc[idx]:
            why.append("missing_symbol")
        if master_is_index.loc[idx]:
            why.append("security_master_classifies_as_index")
        elif is_adr.loc[idx]:
            why.append("adr_retained_as_stock_candidate; verify depositary_ratio_and_market_cap")
        elif likely_fund.loc[idx]:
            why.append("security_master_classifies_as_etp" if master_is_etp.loc[idx] else "fund_or_etf_name_match")
            why.append("market_cap_threshold_not_applied_to_fund_or_etf")
        elif likely_non_common.loc[idx]:
            why.append("security_master_classifies_as_warrant" if master_is_warrant.loc[idx] else "non_common_security_name_match")
            why.append("exclude_from_ordinary_stock_universe_pending_confirmation")
        elif master_is_stock.loc[idx]:
            why.append("security_master_classifies_as_stock_but_common_equity_status_unverified")
        else:
            why.append("security_type_unverified")
        # Keep cap availability/rejection reasons consistent with kis_universe.py,
        # including rows whose security-master type is known but cap data is missing.
        if pd.isna(cap_usd.loc[idx]):
            why.append("usd_market_cap_unavailable")
        elif cap_usd.loc[idx] < min_cap_usd:
            why.append("below_minimum_market_cap")
        if is_korea.loc[idx] and pd.isna(native_cap.loc[idx]):
            why.append("krx_market_cap_unit_not_verified_against_price_times_shares")
        if not is_korea.loc[idx] and pd.isna(native_cap.loc[idx]):
            why.append(
                "adr_market_cap_requires_depositary_ratio_verification"
                if is_adr.loc[idx] else "us_market_cap_not_verified_against_price_times_shares"
            )
        if is_korea.loc[idx] and usdkrw is None and not likely_fund.loc[idx] and not likely_non_common.loc[idx]:
            why.append("fx_rate_required_for_usd_threshold")
        reasons.append(";".join(why))
        statuses.append("exclude_candidate" if (likely_fund.loc[idx] or likely_non_common.loc[idx] or master_is_index.loc[idx]) else "manual_review")

    result = pd.DataFrame({
        "symbol": symbol, "name": name, "exchange": exchange, "currency": currency,
        "market_cap_native": native_cap, "market_cap_usd": cap_usd,
        "instrument_type_guess": type_guess,
        "master_instrument_type": master_instrument_type,
        "master_security_type_code": master_type,
        "is_adr_candidate": is_adr,
        "master_dr_flag": master_dr_flag,
        "master_dr_country_code": master_dr_country_code,
        "stock_eligible": pd.Series("review_required", index=frame.index).where(
            ~likely_fund & ~likely_non_common & ~master_is_index, "exclude_from_stock_universe_pending_confirmation"),
        "cap_threshold_pass": cap_pass, "review_status": statuses, "review_reason": reasons,
    })
    result.loc[likely_non_common & ~likely_fund, "instrument_type_guess"] = "non_common_security_likely"
    result["market_cap_native"] = pd.to_numeric(result["market_cap_native"], errors="coerce")
    result["market_cap_usd"] = pd.to_numeric(result["market_cap_usd"], errors="coerce")
    return result.reset_index(drop=True)



# Deployment rebuild marker: 2026-10-22 KIS ranking request excludes legacy CURR_GB.
st.set_page_config(page_title="Global Stage Analysis", page_icon="📈", layout="wide")
st.title("🌍 Global Stage Analysis Radar")
st.caption("데이터 정확성 우선 MVP · 주간 장기 추세 · 최종 판단은 투자자가 수행")
st.warning("KIS 시세 우선: 국내 KRX 자산과 미국 상장 주식/ETF를 조회합니다. 해외시장·업종·원자재는 거래 가능한 상장 ETF를 프록시로 사용합니다. ETF의 실제 거래 가능 여부는 이용 증권사에서 확인하세요.")

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

@st.cache_data(ttl=86400, show_spinner=False)
def cached_us_security_master():
    """Cache official KIS security types for one day to avoid repeated master downloads."""
    return fetch_us_security_master()


def read_prices(file):
    d = pd.read_csv(file)
    d.columns = [str(x).strip().lower() for x in d.columns]
    missing = PRICE_COLS - set(d.columns)
    if missing: raise ValueError("가격 CSV 필수 열 누락: " + ", ".join(sorted(missing)))
    return normalize_ohlcv(d)

with st.sidebar:
    st.header("데이터")
    mode = st.radio("모드", ["가상 데모", "CSV 업로드", "KIS API · 미국·한국"])
    if mode == "KIS API · 미국·한국":
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
    discover_stocks = False
    if mode == "CSV 업로드":
        pf = st.file_uploader("일별 가격 CSV", type=["csv"])
        uf = st.file_uploader("종목 유니버스 CSV", type=["csv"])
    elif mode == "KIS API · 미국·한국":
        uf = st.file_uploader("선택: 사용자 지정 유니버스 CSV", type=["csv"])
        st.caption("기본 유니버스가 자동으로 로드됩니다. 미국 상장 ETF로 해외시장·업종·원자재를 추적하며, 필요하면 CSV를 업로드해 목록을 바꿀 수 있습니다.")
        fetch_kis = st.button("KIS에서 가격 조회", type="primary")
        discover_stocks = st.button("KIS 시가총액 후보 조회 (미국 거래소별 최대 50페이지)")
        discover_krx_master = st.button("한국 공식 종목 마스터 조회 (검토용)")
    st.divider()
    min_cap_b = st.number_input(
        "최소 시가총액 (USD, $B)",
        min_value=0.0,
        value=1.0,
        step=0.5,
        help="예: 1.0 = 10억 달러, 1000 = 1조 달러",
    )
    min_cap = min_cap_b * 1_000_000_000

if mode == "KIS API · 미국·한국" and locals().get("discover_krx_master", False):
    try:
        krx_frames = []
        for market in ("KOSPI", "KOSDAQ"):
            frame = download_krx_master(market, timeout=30, max_bytes=25_000_000)
            krx_frames.append(frame)
        krx_review = pd.concat(krx_frames, ignore_index=True, sort=False)
        # Keep every field review-only. Offer curated suggestions for ordinary-stock
        # candidates, but leave sector/benchmark proposals blank for other instrument types.
        krx_suggestions = [
            proposed_stock_mapping(row["symbol"], "KRX")
            if row.get("instrument_class") == "stock_candidate"
            else {
                "proposed_market": "South Korea",
                "proposed_sector": "",
                "proposed_market_benchmark": "",
                "proposed_sector_benchmark": "",
                "mapping_status": "instrument_type_review_required",
                "mapping_note": "Instrument is not classified as an ordinary-stock candidate; verify security type first.",
            }
            for _, row in krx_review.iterrows()
        ]
        krx_suggestions = pd.DataFrame(krx_suggestions, index=krx_review.index)
        krx_review["proposed_market"] = krx_suggestions["proposed_market"]
        krx_review["proposed_sector"] = krx_suggestions["proposed_sector"]
        krx_review["proposed_market_benchmark"] = krx_suggestions["proposed_market_benchmark"]
        krx_review["proposed_sector_benchmark"] = krx_suggestions["proposed_sector_benchmark"]
        krx_review["mapping_status"] = krx_suggestions["mapping_status"]
        krx_review["mapping_note"] = krx_suggestions["mapping_note"]
        krx_review["stage_approval_status"] = "manual_review_required"
        st.session_state["kis_krx_master_review"] = krx_review
        st.success(
            f"공식 KRX 마스터 {len(krx_review):,}개 행을 읽었습니다. "
            "이 자료는 검토용이며 활성 Stage 유니버스에는 자동 편입되지 않습니다."
        )
    except Exception as exc:
        st.error(f"공식 KRX 종목 마스터 조회 실패: {type(exc).__name__}: {str(exc)[:250]}")

if mode == "KIS API · 미국·한국" and "kis_krx_master_review" in st.session_state:
    krx_review = st.session_state["kis_krx_master_review"]
    st.markdown("### 한국 공식 종목 마스터 · 검토 전용")
    st.caption(
        "보통주/우선주/SPAC/ETF 구분은 KIS 마스터 필드를 보존해 검토합니다. "
        "업종과 업종 벤치마크는 자동 승인하지 않으며, 모든 행은 수동 검토 상태입니다."
    )
    st.dataframe(
        krx_review[[
            "symbol", "name_ko", "market", "standard_code", "group_code",
            "preferred_share", "spac", "etp", "instrument_class", "approval_status",
            "proposed_market", "proposed_sector", "proposed_market_benchmark",
            "proposed_sector_benchmark", "mapping_status", "mapping_note",
            "stage_approval_status",
        ]],
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "한국 공식 종목 마스터 검토 CSV 다운로드",
        krx_review.to_csv(index=False).encode("utf-8-sig"),
        file_name="kis_krx_master_review_only.csv",
        mime="text/csv",
    )

if mode == "KIS API · 미국·한국" and discover_stocks:
    try:
        client = KISDomesticPrices(
            app_key=get_secret("KIS_APP_KEY"),
            app_secret=get_secret("KIS_APP_SECRET"),
        )
        candidate_frames = []
        discovery_errors = []
        discovery_counts = []
        for exchange in ("NAS", "NYS", "AMS"):
            try:
                candidate = fetch_us_market_cap_candidates(client, exchange=exchange)
                returned_rows = len(candidate)
                discovery_counts.append({
                    "market": f"US {exchange}",
                    "returned_rows": returned_rows,
                    "pages_fetched": candidate.attrs.get("ranking_pages_fetched", 0),
                    "page_limit_reached": bool(candidate.attrs.get("ranking_page_limit_reached", False)),
                    "status": "ok",
                })
                if not candidate.empty:
                    candidate_frames.append(candidate)
            except Exception as exc:
                discovery_counts.append({
                    "market": f"US {exchange}", "returned_rows": 0,
                    "pages_fetched": 0, "page_limit_reached": False, "status": "error",
                })
                discovery_errors.append({"market": f"US {exchange}", "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
        # Query the KRX exchange and KOSDAQ ranking lists separately. A single
        # all-market ranking is not enough to establish broad coverage.
        for market_code, market_label in (("0001", "KRX 거래소"), ("1001", "KRX KOSDAQ")):
            try:
                korea_candidates = fetch_korea_market_cap_candidates(client, market=market_code)
                returned_rows = len(korea_candidates)
                discovery_counts.append({
                    "market": market_label,
                    "returned_rows": returned_rows,
                    "pages_fetched": korea_candidates.attrs.get("ranking_pages_fetched", 0),
                    "page_limit_reached": bool(korea_candidates.attrs.get("ranking_page_limit_reached", False)),
                    "status": "ok",
                })
                if not korea_candidates.empty:
                    candidate_frames.append(korea_candidates)
            except Exception as exc:
                discovery_counts.append({
                    "market": market_label, "returned_rows": 0,
                    "pages_fetched": 0, "page_limit_reached": False, "status": "error",
                })
                discovery_errors.append({
                    "market": market_label,
                    "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                })
        # Prefer KIS's official symbol master for stock/ETP/index/warrant classification.
        # Also compare ranking coverage with the master, without treating unmatched master
        # symbols as cap-eligible stocks (the master has no current market-cap values).
        security_master = pd.DataFrame()
        master_audit_error = ""
        if candidate_frames:
            try:
                security_master = cached_us_security_master()
                master_lookup = {
                    (str(row.listing_exchange).upper(), str(row.symbol).upper()): {
                        "master_security_type": str(row.master_security_type),
                        "master_dr_flag": str(row.master_dr_flag),
                        "master_dr_country_code": str(row.master_dr_country_code),
                    }
                    for row in security_master.itertuples(index=False)
                }
                for idx, candidate in enumerate(candidate_frames):
                    if "listing_exchange" in candidate.columns and "symb" in candidate.columns:
                        candidate = candidate.copy()
                        matched_master = [
                            master_lookup.get(
                                (str(exchange).upper(), str(symbol).strip().upper()), {}
                            )
                            for exchange, symbol in zip(candidate["listing_exchange"], candidate["symb"])
                        ]
                        candidate["master_security_type"] = [row.get("master_security_type", "") for row in matched_master]
                        candidate["master_dr_flag"] = [row.get("master_dr_flag", "") for row in matched_master]
                        candidate["master_dr_country_code"] = [row.get("master_dr_country_code", "") for row in matched_master]
                        candidate_frames[idx] = candidate
            except Exception as exc:
                master_audit_error = f"{type(exc).__name__}: {str(exc)[:200]}"
                discovery_errors.append({
                    "market": "US security master",
                    "error": master_audit_error,
                })
        combined_candidates = (
            pd.concat(candidate_frames, ignore_index=True, sort=False)
            if candidate_frames else pd.DataFrame()
        )
        st.session_state["kis_us_master_coverage"] = (
            audit_us_master_ranking_coverage(security_master, combined_candidates)
            if not security_master.empty else pd.DataFrame()
        )
        st.session_state["kis_us_unranked_master_stocks"] = (
            build_unranked_us_stock_master(security_master, combined_candidates)
            if not security_master.empty else pd.DataFrame()
        )
        st.session_state["kis_us_master_coverage_error"] = master_audit_error
        st.session_state["kis_stock_candidates"] = combined_candidates
        st.session_state["kis_stock_candidate_errors"] = discovery_errors
        st.session_state["kis_stock_candidate_counts"] = discovery_counts
    except Exception as exc:
        st.error(f"시가총액 후보 조회 실패: {type(exc).__name__}: {str(exc)[:250]}")

if mode == "KIS API · 미국·한국" and "kis_stock_candidates" in st.session_state:
    st.subheader("KIS 시가총액 상위 주식 후보")
    st.warning(
        "이 목록은 후보 탐색용이며 기본 Stage 유니버스에 자동 편입되지 않습니다. "
        "시가총액은 현재가 × 상장주식수와 대조가 맞는 경우에만 기준 판정에 사용하고, "
        "공식 종목 마스터에서 stock으로 확인된 종목도 보통주 여부와 업종·벤치마크는 추가 검토가 필요합니다. "
        "기준 통과는 Stage 유니버스 승인이나 Stage 판정을 의미하지 않습니다."
    )
    candidates = st.session_state["kis_stock_candidates"]
    counts = st.session_state.get("kis_stock_candidate_counts", [])
    if counts:
        st.markdown("#### 거래소별 조회 범위")
        counts_frame = pd.DataFrame(counts)
        st.dataframe(counts_frame, use_container_width=True, hide_index=True)
        if "page_limit_reached" in counts_frame.columns and counts_frame["page_limit_reached"].fillna(False).astype(bool).any():
            limited_markets = counts_frame.loc[
                counts_frame["page_limit_reached"].fillna(False).astype(bool), "market"
            ].astype(str).tolist()
            st.warning(
                "일부 미국 거래소의 시가총액 순위 조회가 페이지 상한에 도달했습니다: "
                + ", ".join(limited_markets)
                + ". 따라서 이 결과는 전체 종목 목록이 아니며, 기준 시가총액 이상인 모든 종목을 포함한다고 보장할 수 없습니다. "
                "조회 범위를 넓히기 위해 미국 거래소별 최대 50페이지(최대 약 500개 순위 행)까지 확인했지만, 상한 도달 시 전체 종목 목록을 보장하지 않습니다. 마스터 미반환 종목은 별도 조사 목록으로 관리합니다."
            )
        master_coverage = st.session_state.get("kis_us_master_coverage", pd.DataFrame())
        if not master_coverage.empty:
            st.markdown("#### 미국 종목 마스터 대비 순위 API 커버리지")
            st.dataframe(master_coverage, use_container_width=True, hide_index=True)
            st.caption(
                "‘마스터에 있지만 순위 API에는 없는 종목’은 누락된 시가총액 기준 통과 종목이라는 뜻이 아닙니다. "
                "마스터에는 ETF·워런트 등도 포함되고 현재 시가총액이 없으므로, 추가 후보로 자동 편입하지 않습니다. "
                "이 비교는 순위 API 결과가 마스터 전체 심볼 중 어느 정도를 반환했는지 확인하는 진단 지표입니다."
            )
        elif st.session_state.get("kis_us_master_coverage_error"):
            st.info(
                "미국 종목 마스터를 가져오지 못해 커버리지 비교는 생략했습니다. "
                "순위 API 후보는 유지되며、아래 조회 오류에 마스터 다운로드 오류가 표시됩니다."
            )
        unranked_master_stocks = st.session_state.get("kis_us_unranked_master_stocks", pd.DataFrame())
        if not unranked_master_stocks.empty:
            st.markdown("#### 순위 API 미반환 · 종목 마스터상 주식 심볼")
            st.caption(
                f"공식 마스터상 stock 유형이지만 이번 순위 API에는 없던 심볼 {len(unranked_master_stocks):,}개입니다. "
                "현재 시가총액이 확인되지 않아 기준 통과 여부는 알 수 없습니다. "
                "추가 조사 목록이며 기본 유니버스나 시가총액 통과 후보에 자동 편입하지 않습니다."
            )
            st.dataframe(unranked_master_stocks.head(100), use_container_width=True, hide_index=True)
            st.download_button(
                "미반환 종목 마스터 목록 CSV 다운로드",
                unranked_master_stocks.to_csv(index=False).encode("utf-8-sig"),
                file_name="kis_us_unranked_master_stock_symbols.csv",
                mime="text/csv",
            )
        st.caption(
            "반환 행 수는 KIS 순위 API가 이번 조회에서 제공한 후보 수입니다. "
            "page_limit_reached=True이면 페이지 상한에 도달한 상태에서 KIS가 다음 페이지도 있다고 알려준 것이므로, "
            "후보 목록이 잘렸다는 뜻입니다. False여도 순위 API의 전체 종목 커버리지가 보장되는 것은 아닙니다."
        )
    if candidates.empty:
        st.info("KIS가 반환한 후보 데이터가 없습니다. 아래 조회 오류를 확인하세요.")
    else:
        st.caption(
            f"후보 데이터 {len(candidates)}행 · 원본 KIS 필드 유지 · 시가총액 단위 검증 전. "
            "KIS 거래소별 시가총액 순위 API에서 반환된 상위 후보이며, 선택한 최소 시가총액 이상인 모든 종목의 완전한 목록은 아닙니다."
        )
        st.dataframe(candidates, use_container_width=True, hide_index=True)
        st.download_button(
            "주식 후보 원본 CSV 다운로드",
            candidates.to_csv(index=False).encode("utf-8-sig"),
            file_name="kis_market_cap_candidates_raw.csv",
            mime="text/csv",
        )
        st.markdown("#### 표준화 및 검토용 후보 목록")
        st.caption(
            "미국 tomv는 현재가 × 상장주식수와 대조해 단위가 일치할 때만 USD 시가총액으로 사용합니다. "
            "한국 stck_avls도 현재가 × 상장주식수로 단위를 검증하며, USD 시가총액은 환율 입력 전까지 비워 둡니다. "
            "KIS 공식 종목 마스터의 stock/ETP/index/warrant 구분을 우선 적용하고, 마스터 조회 실패 시 이름 기반 추정으로 대체합니다. "
            "마스터의 stock 구분도 보통주 여부를 최종 확정하지 않으므로 수동 검토가 필요합니다."
        )
        usdkrw_input = st.number_input(
            "KRW per USD 환율 (한국 후보의 USD 시가총액 계산용, 선택)",
            min_value=0.0,
            value=0.0,
            step=10.0,
            help="0이면 한국 종목의 USD 시가총액을 계산하지 않습니다. 검증된 기준일 환율을 입력하세요."
        )
        normalized = normalize_market_cap_candidates(
            candidates,
            min_cap_usd=float(min_cap),
            usdkrw=float(usdkrw_input) if usdkrw_input > 0 else None,
        )
        st.dataframe(normalized, use_container_width=True, hide_index=True)
        stock_candidates = normalized[
            normalized["instrument_type_guess"].isin([
                "equity_candidate_unverified", "adr_candidate_unverified"
            ])
        ]
        cap_results = stock_candidates["cap_threshold_pass"]
        eligible_by_cap = int(cap_results.fillna(False).sum())
        cap_fail = int((cap_results.notna() & ~cap_results.fillna(False)).sum())
        cap_pending = int(cap_results.isna().sum())
        adr_pending = int((
            normalized["is_adr_candidate"] & normalized["cap_threshold_pass"].isna()
        ).sum())
        likely_funds = int(normalized["instrument_type_guess"].eq("fund_or_etf_likely").sum())
        non_common = int(normalized["instrument_type_guess"].eq("non_common_security_likely").sum())
        index_candidates = int(normalized["instrument_type_guess"].eq("index_security_master").sum())
        st.markdown("#### 후보 검증 현황")
        st.dataframe(pd.DataFrame([
            {"구분": "주식/ADR 후보 · 시가총액 기준 통과", "종목 수": eligible_by_cap},
            {"구분": "주식/ADR 후보 · 기준 미달", "종목 수": cap_fail},
            {"구분": "주식/ADR 후보 · 시가총액 검증 대기", "종목 수": cap_pending},
            {"구분": "그중 ADR · 예탁비율/시가총액 확인 대기", "종목 수": adr_pending},
            {"구분": "ETF/펀드 추정 · 주식 시가총액 심사 제외", "종목 수": likely_funds},
            {"구분": "비보통주/워런트 추정 · 검토 필요", "종목 수": non_common},
            {"구분": "종목 마스터상 지수", "종목 수": index_candidates},
        ]), use_container_width=True, hide_index=True)
        st.caption(
            f"USD 시가총액 기준: {min_cap_b:.1f}B. "
            "통과는 후보 심사 기준의 통과일 뿐, 보통주 확정·Stage 유니버스 승인·Stage 판정을 뜻하지 않습니다. "
            "ETF에는 주식 시가총액 기준을 적용하지 않습니다. 공식 마스터 미매칭 종목은 이름 기반 추정만 적용됩니다. "
            "후보는 KIS 순위 API 반환 범위에 한정됩니다."
        )
        st.download_button(
            "표준화 후보 CSV 다운로드",
            normalized.to_csv(index=False).encode("utf-8-sig"),
            file_name="kis_market_cap_candidates_review.csv",
            mime="text/csv",
        )
        # This is a review worksheet, not a directly loadable approved universe.
        # Include cap-passing stock-like rows and ADRs whose cap needs depositary-ratio review.
        # Proposed metadata is separate from the blank, required fields used by Stage.
        review_rows = normalized[
            normalized["instrument_type_guess"].isin([
                "equity_candidate_unverified", "adr_candidate_unverified"
            ])
            & (
                normalized["cap_threshold_pass"].fillna(False)
                | (normalized["is_adr_candidate"] & normalized["cap_threshold_pass"].isna())
            )
        ].copy()
        mapping_suggestions = pd.DataFrame([
            proposed_stock_mapping(
                row["symbol"], row["exchange"], row.get("master_dr_country_code", "")
            )
            for _, row in review_rows.iterrows()
        ], index=review_rows.index, columns=[
            "proposed_market", "proposed_sector", "proposed_asset_type",
            "proposed_market_benchmark", "proposed_sector_benchmark",
            "mapping_status", "mapping_note",
        ])
        stock_review_template = pd.DataFrame({
            "symbol": review_rows["symbol"].astype(str).str.strip(),
            "name": review_rows["name"],
            # Required Stage fields remain blank until a human verifies the proposed values below.
            "market": "",
            "sector": "",
            "asset_type": "",
            "market_cap_usd": review_rows["market_cap_usd"],
            "market_cap_screen_status": review_rows.apply(
                lambda row: "pass" if pd.notna(row["cap_threshold_pass"]) and bool(row["cap_threshold_pass"])
                else ("pending_ADR_depositary_ratio_verification"
                      if bool(row["is_adr_candidate"]) and pd.isna(row["cap_threshold_pass"])
                      else "not_passed_or_unverified"),
                axis=1,
            ),
            "market_benchmark": "",
            "sector_benchmark": "",
            "exchange": review_rows["exchange"],
            # Issuer country is left blank for US-listed ADRs; exchange location is not issuer domicile.
            "country": review_rows["exchange"].map(
                lambda x: "South Korea" if str(x).upper() == "KRX" else ""
            ),
            "currency": review_rows["currency"],
            "instrument_type_review": review_rows.apply(
                lambda row: "ADR candidate; retain pending depositary-ratio/cap verification"
                if bool(row.get("is_adr_candidate", False)) else (
                    "KIS master: stock; common-equity status still needs review"
                    if row["master_instrument_type"] == "stock" else (
                        "KIS master: " + str(row["master_instrument_type"])
                        if row["master_instrument_type"] != "unmatched_or_unknown" else "unverified"
                    )
                ), axis=1
            ),
            "is_adr_candidate": review_rows["is_adr_candidate"],
            "master_dr_flag": review_rows["master_dr_flag"],
            "master_dr_country_code": review_rows["master_dr_country_code"],
            "review_reason": review_rows["review_reason"],
            "proposed_market": mapping_suggestions["proposed_market"],
            "proposed_sector": mapping_suggestions["proposed_sector"],
            "proposed_asset_type": mapping_suggestions["proposed_asset_type"],
            "proposed_market_benchmark": mapping_suggestions["proposed_market_benchmark"],
            "proposed_sector_benchmark": mapping_suggestions["proposed_sector_benchmark"],
            "mapping_status": mapping_suggestions["mapping_status"],
            "mapping_note": mapping_suggestions["mapping_note"],
        })
        st.caption(
            "추가된 proposed_* 열은 1차 제안일 뿐 검증된 메타데이터가 아닙니다. "
            "market/sector/asset_type/benchmark 필드는 의도적으로 비워 두었습니다. "
            "종목 유형과 업종·벤치마크를 확인해 필수 필드에 반영한 뒤에만 Stage 유니버스에 사용하세요."
        )
        st.download_button(
            "시가총액 기준 통과 주식 후보 검토 템플릿 다운로드",
            stock_review_template.to_csv(index=False).encode("utf-8-sig"),
            file_name="stock_universe_review_template.csv",
            mime="text/csv",
            disabled=stock_review_template.empty,
        )
    errors = st.session_state.get("kis_stock_candidate_errors", [])
    if errors:
        with st.expander("시장별 후보 조회 오류", expanded=True):
            st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)

try:
    if mode == "가상 데모":
        universe, prices = demo_data()
    elif mode == "CSV 업로드":
        if pf is None or uf is None:
            st.info("가격 CSV와 종목 유니버스 CSV를 모두 업로드하세요.")
            st.stop()
        universe, prices = read_universe(uf), read_prices(pf)
    else:
        # Use the curated repository starter list when the user does not
        # upload a custom universe. It contains KIS-fetchable US-listed ETF
        # proxies plus a small KRX ETF sample.
        universe = (
            read_universe(uf)
            if uf is not None
            else read_universe("data/monitoring_universe.csv")
        )
        base_universe_symbols = set(universe["symbol"].astype(str).str.strip().str.upper())
        candidate_prices_for_app = pd.DataFrame()
        candidate_stage_gate_errors = []
        # Candidate rows are a separate review registry. Only explicitly active
        # rows that pass the final evidence and price-history gates may join Stage.
        if uf is None and os.path.exists("data/stock_universe_candidates.csv"):
            try:
                candidate_registry = pd.read_csv(
                    "data/stock_universe_candidates.csv",
                    dtype={"symbol": "string"},
                )
                active_candidates = candidate_registry[
                    candidate_registry.get("activation_status", pd.Series(index=candidate_registry.index, dtype="string"))
                    .fillna("").astype(str).str.strip().str.lower().eq("active")
                ].copy()
                if not active_candidates.empty:
                    base_snapshot_for_gate = read_prices("data/daily_prices.csv")
                    candidate_prices_for_app = read_prices("data/candidate_daily_prices.csv")
                    gate_prices = pd.concat(
                        [base_snapshot_for_gate, candidate_prices_for_app],
                        ignore_index=True,
                    )
                    latest_snapshot_date = pd.to_datetime(
                        base_snapshot_for_gate["date"], errors="coerce"
                    ).max()
                    universe, candidate_stage_gate_errors = extend_universe_with_approved_candidates(
                        universe,
                        active_candidates,
                        gate_prices,
                        latest_snapshot_date=latest_snapshot_date,
                    )
                    if candidate_stage_gate_errors:
                        with st.expander(
                            f"개별 주식 후보 편입 보류: {len(candidate_stage_gate_errors)}개",
                            expanded=False,
                        ):
                            st.dataframe(
                                pd.DataFrame(candidate_stage_gate_errors),
                                use_container_width=True,
                                hide_index=True,
                            )
                    added = len(universe) - len(base_universe_symbols)
                    if added:
                        st.caption(f"검증 게이트를 통과한 개별 주식 후보 {added}개를 Stage 분석에 포함했습니다.")
            except Exception as candidate_load_error:
                st.warning(
                    "개별 주식 후보 연결을 건너뛰었습니다. 기존 시장·업종 유니버스는 유지됩니다. "
                    f"원인: {candidate_load_error}"
                )
                universe = read_universe("data/monitoring_universe.csv")
                candidate_prices_for_app = pd.DataFrame()
        # Prefer the repository's scheduled daily snapshot so ordinary app
        # visits never trigger a burst of KIS requests. Manual fetch remains
        # available for an explicit refresh or a custom universe.
        snapshot_path = "data/daily_prices.csv"
        snapshot_status_path = "data/daily_prices_status.json"
        requested_symbols = tuple(
            map(tuple, universe[["symbol", "exchange", "market", "asset_type"]].astype(str).to_numpy())
        )
        if (
            not fetch_kis
            and "kis_prices" not in st.session_state
            and uf is None
            and os.path.exists(snapshot_path)
        ):
            try:
                snapshot_prices = read_prices(snapshot_path)
                if not candidate_prices_for_app.empty:
                    added_symbols = set(universe["symbol"].astype(str).str.strip().str.upper()) - base_universe_symbols
                    candidate_price_rows = candidate_prices_for_app[
                        candidate_prices_for_app["symbol"].astype(str).str.strip().str.upper().isin(added_symbols)
                    ].copy()
                    if not candidate_price_rows.empty:
                        snapshot_prices = pd.concat(
                            [snapshot_prices, candidate_price_rows],
                            ignore_index=True,
                        )
                snapshot_symbols = tuple(
                    map(tuple, universe[["symbol", "exchange", "market", "asset_type"]].astype(str).to_numpy())
                )
                available_symbols = set(snapshot_prices["symbol"].astype(str).str.upper())
                if set(universe["symbol"].astype(str).str.upper()).issubset(available_symbols):
                    st.session_state["kis_prices"] = snapshot_prices
                    st.session_state["kis_universe_symbols"] = snapshot_symbols
                    st.session_state["kis_fetch_errors"] = []
                    if os.path.exists(snapshot_status_path):
                        import json
                        with open(snapshot_status_path, "r", encoding="utf-8") as status_file:
                            snapshot_status = json.load(status_file)
                        st.session_state["daily_snapshot_status"] = snapshot_status
                        st.caption(
                            "저장된 일일 종가 스냅샷 사용 · "
                            f"마지막 갱신(KST): {snapshot_status.get('updated_at_kst', '확인 불가')} · "
                            f"데이터 종목 수: {snapshot_status.get('symbols_with_data', '확인 불가')} · "
                            f"최근 갱신 오류: {snapshot_status.get('error_count', '확인 불가')}"
                        )
                    else:
                        st.session_state["daily_snapshot_status"] = {}
                        st.caption("저장된 일일 종가 스냅샷 사용 · 갱신 이력 파일 없음")
                else:
                    st.info("저장된 스냅샷에 일부 종목이 없습니다. 'KIS에서 가격 조회'를 눌러 수동 조회하세요.")
            except Exception as snapshot_error:
                st.warning(f"저장된 종가 스냅샷을 읽지 못했습니다: {snapshot_error}")
        if fetch_kis:
            # Do not mix the scheduled snapshot's status with a manual live fetch.
            st.session_state["daily_snapshot_status"] = {}
            try:
                kis = KISDomesticPrices(
                    app_key=get_secret("KIS_APP_KEY"),
                    app_secret=get_secret("KIS_APP_SECRET"),
                )
                us_provider = KISUSProvider(kis)
                kr_provider = KISKoreaProvider(kis)
                unsupported = universe[~universe.apply(
                    lambda row: (
                        (
                            str(row["exchange"]).strip().upper() == "KRX"
                            and kr_provider.supports(row["market"], row["asset_type"])
                        )
                        or (
                            str(row["exchange"]).strip().upper() in {"NAS", "NYS", "AMS"}
                            and us_provider.supports(row["market"], row["asset_type"])
                        )
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
                        if str(item.exchange).strip().upper() == "KRX"
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
            st.warning(f"KIS 조회에 실패했거나 데이터가 없는 종목: {len(fetch_errors)}개 / 요청 {len(requested_symbols)}개")
            with st.expander("종목별 KIS 조회 오류", expanded=(len(fetch_errors) > 0)):
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
universe_before_history_filter = universe.copy()
universe = universe[universe.symbol.isin(symbols)].copy()
exchange_by_symbol = {}
for _, universe_row in universe.iterrows():
    exchange = str(universe_row.get("exchange", "")).upper()
    if exchange in {"NYS", "NAS", "AMS"}:
        exchange_by_symbol[str(universe_row["symbol"])] = "XNYS"
    elif exchange in {"KRX", "KOSDAQ", "KOSPI"}:
        exchange_by_symbol[str(universe_row["symbol"])] = "XKRX"
weekly_by_symbol = {
    s: weekly_bars(g, calendar_name=exchange_by_symbol.get(str(s)))
    for s, g in prices.groupby("symbol")
}
weekly_by_symbol = {s:w for s,w in weekly_by_symbol.items() if w is not None}
price_symbol_count = len(symbols)
analysis_symbol_count = len(weekly_by_symbol)
if mode == "KIS API · 미국·한국":
    expected_count = len(universe_before_history_filter)
    st.subheader("데이터 수집 상태")
    st.caption(
        f"기본/업로드 유니버스 {expected_count}개 · 가격 데이터 수신 {price_symbol_count}개 · "
        f"주간 Stage 계산 가능 {analysis_symbol_count}개"
    )
    if price_symbol_count < expected_count:
        st.warning(
            "일부 종목의 가격 데이터가 없습니다. '종목별 KIS 조회 오류'를 펼쳐서 원인을 확인하세요. "
            "이 상태에서 일부 종목만 보이는 결과를 전체 시장 결과로 해석하지 마세요."
        )
    if analysis_symbol_count < price_symbol_count:
        short_history = sorted(symbols - set(weekly_by_symbol))
        st.warning(
            "가격은 받았지만 주간 Stage 계산에 필요한 과거 데이터가 부족하거나 주간 봉을 만들 수 없는 종목이 "
            f"{len(short_history)}개 있습니다. 예: {', '.join(short_history[:12])}"
        )

latest_daily_dates = (
    prices.assign(
        symbol=prices["symbol"].astype(str),
        date=pd.to_datetime(prices["date"], errors="coerce"),
    ).groupby("symbol")["date"].max().to_dict()
)

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
    symbol_daily = prices.loc[prices["symbol"].astype(str).eq(str(s)), "date"]
    last_daily_date = pd.to_datetime(symbol_daily, errors="coerce").max()
    label = classify_stage(
        close=last.close,
        ma30=last.ma30,
        slope4_pct=last.slope4_pct,
        market_rs=last.rs_market_26w_pct,
        sector_rs=last.rs_sector_26w_pct,
        asset_type=item.asset_type,
    )
    freshness_status = stage_data_freshness_status(
        symbol=str(s),
        asset_type=str(item.asset_type),
        market_benchmark=str(mkt),
        sector_benchmark=str(sec),
        latest_dates=latest_daily_dates,
    )
    stale_data = freshness_status == "asset_stale"
    market_benchmark_stale = freshness_status == "market_benchmark_stale"
    sector_benchmark_stale = freshness_status == "sector_benchmark_stale"
    market_rs_missing = (
        mkt not in weekly_by_symbol
        or (mkt != s and pd.isna(last.rs_market_26w_pct))
    )
    sector_rs_missing = (
        str(item.asset_type).lower() == "stock"
        and (sec not in weekly_by_symbol or pd.isna(last.rs_sector_26w_pct))
    )
    label = stage_label_with_data_guards(
        label=label,
        freshness_status=freshness_status,
        market_rs_missing=market_rs_missing,
        sector_rs_missing=sector_rs_missing,
    )
    rows.append({**item.to_dict(),"last_date":last.date,"last_daily_date":last_daily_date,"data_stale":stale_data,"benchmark_data_stale":market_benchmark_stale or sector_benchmark_stale,"benchmark_data_missing":market_rs_missing or sector_rs_missing,"close":last.close,"ma30":last.ma30,"slope4_pct":last.slope4_pct,"ret13_pct":last.ret13_pct,"ret26_pct":last.ret26_pct,"rs_market_26w_pct":last.rs_market_26w_pct,"rs_sector_26w_pct":last.rs_sector_26w_pct,"vol_ratio":last.vol_ratio,"volume_confirmation":volume_confirmation(last.vol_ratio),"stage_label":label})
    weekly_by_symbol[s] = w

screen = pd.DataFrame(rows)
if screen.empty:
    st.error("분석할 종목이 없습니다. 종목별 35주 이상의 가격 데이터가 필요합니다."); st.stop()
# Show how far each asset's latest daily bar trails the latest date in the loaded dataset.
snapshot_reference_date = pd.to_datetime(screen["last_daily_date"], errors="coerce").max()
screen["data_gap_calendar_days"] = (
    snapshot_reference_date - pd.to_datetime(screen["last_daily_date"], errors="coerce")
).dt.days
if pd.notna(snapshot_reference_date):
    st.caption(
        f"실제 가격 데이터 기준일: {snapshot_reference_date.date()} · "
        "스냅샷 갱신 시각과 구분되며, 주봉 Stage 판정은 완료된 주봉 기준입니다."
    )
screen["stage_analysis_status"] = np.where(
    screen["stage_label"].astype(str).str.contains("판정 보류|데이터 부족", regex=True, na=False),
    "판정 보류",
    "Stage 분류 표시",
)
# 주식에만 시가총액 기준을 적용한다. ETF/원자재 프록시는 이 필터에서 제외한다.
# 시가총액이 검증되지 않은 주식은 조용히 탈락시키지 않고 검토 대상으로 남긴다.
screen["asset_type_norm"] = screen["asset_type"].astype(str).str.lower()
initial_stock_mask = screen["asset_type_norm"].eq("stock")
initial_cap_unknown = initial_stock_mask & pd.to_numeric(screen["market_cap_usd"], errors="coerce").isna()
screen = screen[
    ~initial_stock_mask
    | initial_cap_unknown
    | (pd.to_numeric(screen["market_cap_usd"], errors="coerce") >= min_cap)
].copy()
if "market_cap_source_url" not in screen.columns:
    screen["market_cap_source_url"] = ""
# Recompute masks after filtering so row-index alignment remains correct.
stock_mask = screen["asset_type_norm"].eq("stock")
cap_unknown_mask = stock_mask & pd.to_numeric(screen["market_cap_usd"], errors="coerce").isna()
cap_unknown_count = int(cap_unknown_mask.sum())
screen["market_cap_review_status"] = "비주식 자산 · 시총 필터 제외"
screen.loc[stock_mask, "market_cap_review_status"] = "출처 기재 · 독립 검증 안 됨"
screen.loc[stock_mask & screen["market_cap_source_url"].fillna("").astype(str).str.strip().eq(""), "market_cap_review_status"] = "출처 미기재"
screen.loc[cap_unknown_mask, "market_cap_review_status"] = "USD 시총 검증 대기"
if cap_unknown_count:
    st.warning(
        f"시가총액 USD 환산 또는 출처 검증이 끝나지 않은 주식 {cap_unknown_count}개를 목록에 유지했어. "
        "이 종목은 최소 시가총액 기준 통과로 간주하지 말고, 시가총액 검증 대기 상태로 확인해."
    )

# 데이터 품질 요약: Stage 결과를 해석하기 전에 보류 원인을 먼저 확인할 수 있게 한다.
st.subheader("데이터 상태")
stage_hold_mask = screen["stage_label"].astype(str).str.contains("판정 보류|데이터 부족", regex=True, na=False)
status_cols = st.columns(6)
status_cols[0].metric("분석 자산", f"{len(screen):,}")
status_cols[1].metric("Stage 판정 보류", f"{int(stage_hold_mask.sum()):,}")
status_cols[2].metric("자산 데이터 오래됨", f"{int(screen['data_stale'].fillna(False).sum()):,}")
status_cols[3].metric("벤치마크 오래됨", f"{int(screen['benchmark_data_stale'].fillna(False).sum()):,}")
status_cols[4].metric("벤치마크 누락", f"{int(screen['benchmark_data_missing'].fillna(False).sum()):,}")
status_cols[5].metric("시총 검증 대기", f"{cap_unknown_count:,}")
if mode == "KIS API · 미국·한국":
    snapshot_status = st.session_state.get("daily_snapshot_status", {})
    if snapshot_status:
        updated_at = snapshot_status.get("updated_at_kst", "확인 불가")
        preserved = snapshot_status.get("symbols_preserved_from_previous_snapshot", [])
        errors = snapshot_status.get("errors", [])
        history_cols = st.columns(4)
        history_cols[0].metric("마지막 스냅샷 갱신(KST)", str(updated_at).replace("T", " ")[:19])
        history_cols[1].metric("갱신 오류", f"{int(snapshot_status.get('error_count', len(errors))):,}")
        history_cols[2].metric("이전 데이터 보존 종목", f"{len(preserved):,}")
        history_cols[3].metric("갱신 대상 종목", f"{int(snapshot_status.get('requested_symbols', 0)):,}")
        with st.expander("최근 갱신 이력 및 종목별 최신 기준일", expanded=False):
            st.caption(
                "갱신 시각은 스냅샷 작업이 실행된 시각이며, 각 거래소의 마지막 거래일과 같지 않을 수 있습니다. "
                "휴장일·시차 때문에 자산별 최신 일봉 날짜가 서로 다를 수 있습니다."
            )
            if errors:
                st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
            elif int(snapshot_status.get("error_count", 0)) == 0:
                st.success("기록된 마지막 갱신에서 종목별 조회 오류는 없었습니다.")
            if preserved:
                st.warning("아래 종목은 이번 갱신 실패로 인해 이전 스냅샷 이력이 유지됐습니다: " + ", ".join(map(str, preserved)))
            normalized_symbols = prices["symbol"].astype(str).str.upper()
            latest_by_symbol = prices.assign(_symbol=normalized_symbols).groupby("_symbol")["date"].max()
            first_by_symbol = prices.assign(_symbol=normalized_symbols).groupby("_symbol")["date"].min()
            row_count_by_symbol = normalized_symbols.value_counts()
            comparable_dates = pd.to_datetime(pd.Series(latest_by_symbol.to_dict()), errors="coerce")
            reference_date = comparable_dates.max()
            freshness_rows = []
            for item in universe.itertuples(index=False):
                symbol = str(item.symbol).upper()
                latest = pd.to_datetime(latest_by_symbol.get(symbol, pd.NaT), errors="coerce")
                gap_days = (reference_date - latest).days if pd.notna(reference_date) and pd.notna(latest) else np.nan
                freshness_rows.append({
                    "심볼": symbol,
                    "이름": str(getattr(item, "name", symbol)),
                    "거래소": str(getattr(item, "exchange", "")),
                    "최초 일봉 기준일": str(pd.to_datetime(first_by_symbol.get(symbol, pd.NaT), errors="coerce").date()) if pd.notna(pd.to_datetime(first_by_symbol.get(symbol, pd.NaT), errors="coerce")) else "데이터 없음",
                    "최신 일봉 기준일": str(latest.date()) if pd.notna(latest) else "데이터 없음",
                    "가격 행 수": int(row_count_by_symbol.get(symbol, 0)),
                    "기준일 차이(달력일)": int(gap_days) if pd.notna(gap_days) else np.nan,
                    "이번 갱신 오류": next((str(err.get("error", "오류")) for err in errors if str(err.get("symbol", "")).upper() == symbol), ""),
                    "이전 데이터 보존": symbol in {str(s).upper() for s in preserved},
                })
            freshness_table = pd.DataFrame(freshness_rows)
            freshness_table["_date_sort"] = pd.to_datetime(freshness_table["최신 일봉 기준일"], errors="coerce")
            freshness_table = freshness_table.sort_values(["_date_sort", "심볼"], na_position="first").drop(columns="_date_sort")
            valid_gaps = pd.to_numeric(freshness_table["기준일 차이(달력일)"], errors="coerce").dropna()
            if not valid_gaps.empty:
                st.caption(
                    f"최신 기준일: {reference_date.date()} · "
                    f"기준일 차이 최댓값: {int(valid_gaps.max())}일 · "
                    "달력일 기준 차이이므로 거래소 휴장일이 포함될 수 있습니다."
                )
            st.dataframe(freshness_table, use_container_width=True, hide_index=True)
            st.download_button(
                "종목별 최신 기준일 CSV 다운로드",
                freshness_table.to_csv(index=False).encode("utf-8-sig"),
                file_name="symbol_latest_dates.csv",
                mime="text/csv",
                key="symbol_latest_dates_download",
            )
with st.expander("추가 종목 후보 데이터 커버리지", expanded=False):
    candidate_status_path = Path("data/candidate_daily_prices_status.json")
    if candidate_status_path.exists():
        try:
            candidate_status = json.loads(candidate_status_path.read_text(encoding="utf-8"))
            failed_symbols = candidate_status.get("failed_symbols", [])
            run_level_failed = "*" in [str(symbol) for symbol in failed_symbols] or bool(candidate_status.get("refresh_attempt_run_level_failed", False))
            status_cols = st.columns(5)
            status_cols[0].metric("최근 후보 조회 시각(KST)", str(candidate_status.get("updated_at_kst", "기록 없음"))[:19].replace("T", " "))
            status_cols[1].metric("조회 요청 후보", str(candidate_status.get("requested_symbols", "—")))
            status_cols[2].metric("이번에 신규 확보", str(candidate_status.get("fresh_data_symbol_count", len(candidate_status.get("fresh_data_symbols", [])))))
            status_cols[3].metric("저장 스냅샷 포함", str(candidate_status.get("symbols_with_data", "—")))
            status_cols[4].metric("조회 오류", str(candidate_status.get("error_count", "—")))
            if run_level_failed:
                st.error("최근 후보 수집 작업 자체가 실패한 것으로 기록되어 있습니다. 아래 저장 스냅샷에는 이전 조회에서 보존된 가격 이력이 포함될 수 있으며, 이를 이번 실행의 성공으로 해석하면 안 됩니다.")
            elif int(candidate_status.get("error_count", 0) or 0) > 0:
                st.warning("일부 후보 조회에 오류가 있습니다. 신규 확보 종목 수와 기존 보존 이력을 구분해서 확인하세요.")
            status_errors = candidate_status.get("errors", [])
            if status_errors:
                st.caption("최근 후보 조회 오류 상세")
                st.dataframe(pd.DataFrame(status_errors), use_container_width=True, hide_index=True)
            st.caption(str(candidate_status.get("data_note", "후보 조회 상태 기록입니다.")))
        except Exception as exc:
            st.warning(f"후보 조회 상태 파일을 읽지 못했습니다: {exc}")
    else:
        st.info("아직 후보 전용 가격 조회 기록이 없습니다. 수동 후보 가격 검토 워크플로를 실행하면 결과가 여기에 표시됩니다.")
    candidate_report_path = Path("data/stock_candidate_coverage_report.csv")
    if candidate_report_path.exists():
        candidate_report = pd.read_csv(candidate_report_path, dtype={"symbol": str})
        if candidate_report.empty:
            st.info("후보 종목 커버리지 보고서가 비어 있습니다.")
        else:
            covered = candidate_report["snapshot_coverage_status"].eq("candidate_and_benchmarks_have_snapshot_rows")
            enough_history = candidate_report.get(
                "candidate_history_150_plus_bars", pd.Series(False, index=candidate_report.index)
            ).fillna(False).astype(bool)
            suggested_benchmark_status = candidate_report.get(
                "suggested_sector_benchmark_coverage_status",
                pd.Series("", index=candidate_report.index),
            ).fillna("").astype(str)
            suggested_benchmark_ready = suggested_benchmark_status.eq(
                "usable_for_provisional_analysis_not_approval"
            )
            suggested_benchmark_missing = suggested_benchmark_status.eq("suggestion_missing")
            report_cols = st.columns(6)
            report_cols[0].metric("검토 후보", f"{len(candidate_report):,}")
            report_cols[1].metric("후보·검토 완료 벤치마크 데이터 존재", f"{int(covered.sum()):,}")
            report_cols[2].metric("후보 이력 150개 이상", f"{int(enough_history.sum()):,}")
            report_cols[3].metric("제안 벤치마크 데이터 확보", f"{int(suggested_benchmark_ready.sum()):,}")
            report_cols[4].metric("업종 벤치마크 제안 없음", f"{int(suggested_benchmark_missing.sum()):,}")
            report_cols[5].metric("자동 활성화 승인", "없음")
            # Summarize review blockers so the next manual review can start with the most common unresolved risks.
            if "review_blockers_ko" in candidate_report.columns:
                blocker_rows = []
                for _, report_row in candidate_report.iterrows():
                    raw = str(report_row.get("review_blockers_ko", "") or "")
                    for blocker in [part.strip() for part in raw.split(" / ") if part.strip()]:
                        blocker_rows.append({"검토 항목": blocker, "심볼": str(report_row.get("symbol", ""))})
                if blocker_rows:
                    blocker_frame = pd.DataFrame(blocker_rows)
                    blocker_summary = (
                        blocker_frame.groupby("검토 항목", as_index=False)
                        .agg(후보수=("심볼", "nunique"), 후보=("심볼", lambda values: ", ".join(sorted(set(values)))))
                        .sort_values(["후보수", "검토 항목"], ascending=[False, True])
                    )
                    with st.expander("후보 검토 우선순위 요약", expanded=False):
                        st.dataframe(blocker_summary, use_container_width=True, hide_index=True)
                        st.download_button(
                            "검토 우선순위 CSV 다운로드",
                            blocker_summary.to_csv(index=False).encode("utf-8-sig"),
                            file_name="candidate_review_priorities.csv",
                            mime="text/csv",
                            key="candidate_review_priorities_download",
                        )
            st.caption(
                "스냅샷 내 데이터 존재 여부를 보여주는 보조 보고서입니다. "
                "KIS 실시간 조회 성공, 종목 식별, 시가총액, ADR 비율 또는 Stage 2 적격성을 검증하지 않습니다. "
                "모든 후보는 별도 검토 전까지 비활성 상태입니다."
            )
            display_cols = [
                ("review_priority", "검토 우선순위"), ("next_review_action", "다음 검토 작업"),
                ("evidence_fields_complete", "근거 필드 완성"), ("evidence_gaps", "누락 근거 필드"),
                ("symbol", "심볼"), ("name", "이름"), ("sector", "업종"),
                ("market", "시장"), ("exchange", "상장 거래소"), ("country", "국가"), ("currency", "통화"),
                ("instrument_type", "상품 유형"), ("identity_status", "상장 식별 상태"),
                ("depositary_ratio_status", "ADR 예탁 비율 상태"), ("market_cap_status", "시총 검증 상태"),
                ("provider_status", "KIS 지원 상태"),
                ("identity_evidence_url", "상장 식별 근거 URL"),
                ("identity_reviewed_at", "상장 식별 검토일"),
                ("market_cap_source_url", "시총 근거 URL"),
                ("market_cap_asof", "시총 기준일"),
                ("provider_observed_data_returned", "KIS 가격 조회 관측"),
                ("candidate_price_rows", "후보 일봉 수"),
                ("candidate_first_price_date", "최초 일봉"),
                ("candidate_latest_price_date", "최신 일봉"),
                ("candidate_lag_calendar_days_vs_snapshot", "기준일 차이(달력일)"),
                ("candidate_history_150_plus_bars", "이력 150개 이상"),
                ("market_benchmark", "시장 벤치마크"),
                ("market_benchmark_price_rows", "시장 벤치마크 일봉 수"),
                ("sector_benchmark", "검토 완료 업종 벤치마크"),
                ("sector_benchmark_price_rows", "검토 완료 업종 벤치마크 일봉 수"),
                ("suggested_sector_benchmark", "제안 업종 벤치마크"),
                ("suggested_sector_benchmark_active", "제안 벤치마크 활성 여부"),
                ("suggested_sector_benchmark_price_rows", "제안 벤치마크 일봉 수"),
                ("suggested_sector_benchmark_latest_date", "제안 벤치마크 최신 일봉"),
                ("suggested_sector_benchmark_lag_calendar_days", "제안 벤치마크 기준일 차이"),
                ("suggested_sector_benchmark_coverage_status", "제안 벤치마크 커버리지 상태"),
                ("snapshot_coverage_status", "스냅샷 커버리지"),
                ("review_blocker_count", "검토 차단 수"),
                ("review_blockers_ko", "남은 검토 항목"),
                ("review_blockers", "검토 코드"),
                ("activation_recommendation", "활성화 상태"),
            ]
            available = [(column, label) for column, label in display_cols if column in candidate_report.columns]
            report_view = candidate_report[[column for column, _ in available]].rename(
                columns={column: label for column, label in available}
            )
            benchmark_status_labels = {
                "suggestion_missing": "업종 벤치마크 제안 없음",
                "benchmark_inactive_or_no_snapshot_rows": "벤치마크 비활성 또는 가격 데이터 없음",
                "benchmark_snapshot_stale": "벤치마크 가격 데이터 지연",
                "usable_for_provisional_analysis_not_approval": "예비 분석 데이터 확보(매핑 승인 아님)",
            }
            if "제안 벤치마크 커버리지 상태" in report_view.columns:
                report_view["제안 벤치마크 커버리지 상태"] = (
                    report_view["제안 벤치마크 커버리지 상태"]
                    .map(benchmark_status_labels)
                    .fillna(report_view["제안 벤치마크 커버리지 상태"])
                )
            st.dataframe(report_view, use_container_width=True, hide_index=True)
            st.download_button(
                "후보 커버리지 CSV 다운로드",
                candidate_report.to_csv(index=False).encode("utf-8-sig"),
                file_name="stock_candidate_coverage_report.csv",
                mime="text/csv",
                key="candidate_coverage_report_download",
            )

            provisional_path = Path("data/provisional_candidate_stage_report.csv")
            if provisional_path.exists():
                provisional = pd.read_csv(provisional_path, dtype={"symbol": str}).fillna("")
                with st.expander("보류 후보 예비 Stage 분석 · 정식 편입과 분리", expanded=False):
                    st.caption(
                        "제안 업종·벤치마크를 이용한 참고용 계산입니다. "
                        "Stage 결과는 종목/벤치마크 검증이나 투자 신호가 아니며, "
                        "이 화면의 후보는 정식 유니버스에 편입되지 않습니다."
                    )
                    if provisional.empty:
                        st.info("예비 분석 결과가 아직 없습니다.")
                    else:
                        stage_counts = provisional["provisional_stage_label"].value_counts()
                        metrics = st.columns(4)
                        metrics[0].metric("예비 분석 후보", f"{len(provisional):,}")
                        metrics[1].metric(
                            "Stage 2 후보 표시",
                            f"{int(provisional['provisional_stage_label'].eq('Stage 2 후보').sum()):,}",
                        )
                        metrics[2].metric(
                            "데이터/벤치마크 보류",
                            f"{int(provisional['provisional_stage_label'].astype(str).str.contains('보류|부족|미완료', regex=True).sum()):,}",
                        )
                        metrics[3].metric("정식 활성화", "0 · 별도 승인 필요")
                        stage_search = st.text_input(
                            "예비 Stage 결과에서 심볼/이름 검색",
                            key="provisional_candidate_stage_search",
                            placeholder="예: ORCL, Oracle",
                        )
                        provisional_view = provisional.copy()
                        if stage_search.strip():
                            needle = stage_search.strip().casefold()
                            mask = provisional_view["symbol"].astype(str).str.casefold().str.contains(needle, regex=False, na=False)
                            if "name" in provisional_view.columns:
                                mask |= provisional_view["name"].astype(str).str.casefold().str.contains(needle, regex=False, na=False)
                            provisional_view = provisional_view[mask]
                        provisional_cols = [
                            ("symbol", "심볼"), ("name", "이름"), ("proposed_sector", "제안 업종"),
                            ("market_benchmark", "시장 벤치마크"),
                            ("suggested_sector_benchmark", "제안 업종 벤치마크"),
                            ("candidate_latest_daily_date", "최신 일봉"),
                            ("completed_weekly_date", "완료 주봉"),
                            ("weekly_bars", "완료 주봉 수"), ("close", "최근 주봉 종가"),
                            ("ma30", "30주선"), ("ma30_slope_4w_pct", "30주선 4주 기울기(%)"),
                            ("market_rs_26w_pct", "시장 대비 RS(26주, %p)"),
                            ("sector_rs_26w_pct", "업종 대비 RS(26주, %p)"),
                            ("volume_context", "거래량 참고"), ("provisional_stage_label", "예비 Stage"),
                            ("data_status", "데이터 상태"), ("review_note", "판정 보류 사유"), ("activation_status", "활성화 상태"),
                        ]
                        present = [(col, label) for col, label in provisional_cols if col in provisional_view.columns]
                        st.dataframe(
                            provisional_view[[col for col, _ in present]].rename(columns=dict(present)),
                            use_container_width=True, hide_index=True,
                        )
                        st.download_button(
                            "예비 Stage 결과 CSV 다운로드",
                            provisional.to_csv(index=False).encode("utf-8-sig"),
                            file_name="provisional_candidate_stage_report.csv",
                            mime="text/csv",
                            key="provisional_candidate_stage_download",
                        )
            else:
                st.info("보류 후보 예비 Stage 결과는 다음 커버리지 보고서 실행에서 생성됩니다.")
    else:
        st.info("커버리지 보고서는 다음 정기 가격 데이터 갱신 과정에서 생성됩니다.")

with st.expander("후보 편입 검토 작업대", expanded=False):
    queue_summary_path = Path("data/candidate_review_queue_summary.csv")
    queue_path = Path("data/candidate_review_queue.csv")
    if queue_summary_path.exists() and queue_path.exists():
        queue_summary = pd.read_csv(queue_summary_path, dtype=str).fillna("")
        review_queue = pd.read_csv(queue_path, dtype={"symbol": str}).fillna("")
        if not review_queue.empty:
            p1_identity = int(
                review_queue.get("queue_priority", pd.Series("", index=review_queue.index))
                .eq("P1_identity_classification").sum()
            )
            p1_market_cap = int(
                review_queue.get("queue_priority", pd.Series("", index=review_queue.index))
                .eq("P1_market_cap_reconciliation").sum()
            )
            p1_below_minimum = int(
                review_queue.get("queue_priority", pd.Series("", index=review_queue.index))
                .eq("P1_below_minimum_size_screen").sum()
            )
            blocked = int(
                review_queue.get("activation_gate_status", pd.Series("", index=review_queue.index))
                .eq("blocked_pending_manual_review").sum()
            )
            queue_metrics = st.columns(5)
            queue_metrics[0].metric("검토 대기 후보", f"{len(review_queue):,}")
            queue_metrics[1].metric("P1 최소 시총 미달", f"{p1_below_minimum:,}")
            queue_metrics[2].metric("P1 상장 식별", f"{p1_identity:,}")
            queue_metrics[3].metric("P1 시총 정합성", f"{p1_market_cap:,}")
            queue_metrics[4].metric("활성화 차단", f"{blocked:,}")
            st.caption(
                "우선순위는 사람이 먼저 확인할 대상을 정하는 용도입니다. "
                "최소 시총 필터는 추정치가 10억 달러 이상이면 통과 처리하며, "
                "그 자체가 공식 시총 검증이나 종목 승인이라는 뜻은 아닙니다. "
                "허들을 충분히 넘는 종목은 주식 수 역산을 반복하지 않고 상장 식별·데이터·벤치마크 검토를 우선합니다."
            )
            priority_order = {
                "P1_identity_classification": 1,
                "P1_market_cap_reconciliation": 2,
                "P2_market_cap_reconciliation": 3,
                "P2_identity_evidence": 4,
                "P3_provider_mapping": 5,
                "P3_market_cap_evidence": 6,
                "P4_final_review": 7,
            }
            if "queue_priority" in review_queue.columns:
                review_queue["_priority_order"] = review_queue["queue_priority"].map(priority_order).fillna(99)
                review_queue = review_queue.sort_values(
                    ["_priority_order", "symbol"]
                ).drop(columns="_priority_order")
            queue_filter_cols = st.columns([1, 1, 1, 2])
            with queue_filter_cols[0]:
                available_priorities = review_queue["queue_priority"].astype(str).drop_duplicates().tolist() if "queue_priority" in review_queue else []
                priority_choice = st.selectbox(
                    "우선순위 필터", ["전체"] + available_priorities,
                    key="candidate_queue_priority_filter",
                )
            with queue_filter_cols[1]:
                available_sectors = sorted(
                    value for value in review_queue.get("sector", pd.Series(dtype=str)).astype(str).str.strip().unique()
                    if value and value.lower() != "nan"
                )
                sector_choice = st.selectbox(
                    "업종 필터", ["전체"] + available_sectors,
                    key="candidate_queue_sector_filter",
                )
            with queue_filter_cols[2]:
                benchmark_choice = st.selectbox(
                    "승인 벤치마크", ["전체", "있음", "없음"],
                    key="candidate_queue_benchmark_filter",
                )
            with queue_filter_cols[3]:
                queue_search = st.text_input(
                    "후보 검색", placeholder="심볼 또는 이름", key="candidate_queue_search",
                )
            queue_view = review_queue.copy()
            if priority_choice != "전체" and "queue_priority" in queue_view:
                queue_view = queue_view[queue_view["queue_priority"].astype(str).eq(priority_choice)]
            if sector_choice != "전체" and "sector" in queue_view:
                queue_view = queue_view[queue_view["sector"].astype(str).eq(sector_choice)]
            if benchmark_choice != "전체" and "sector_benchmark" in queue_view:
                benchmark_present = queue_view["sector_benchmark"].fillna("").astype(str).str.strip().ne("")
                queue_view = queue_view[benchmark_present if benchmark_choice == "있음" else ~benchmark_present]
            if queue_search.strip():
                needle = queue_search.strip().casefold()
                search_mask = queue_view["symbol"].astype(str).str.casefold().str.contains(needle, regex=False, na=False)
                if "name" in queue_view:
                    search_mask |= queue_view["name"].astype(str).str.casefold().str.contains(needle, regex=False, na=False)
                queue_view = queue_view[search_mask]
            st.caption(f"현재 표시 {len(queue_view):,}개 / 전체 대기 {len(review_queue):,}개")
            # Compact triage counts help separate already-captured identity evidence
            # from missing benchmark proposals without treating either as approval.
            if not queue_view.empty:
                triage_metrics = st.columns(4)
                if "issuer_country_evidence_present" in queue_view:
                    evidence_present = (
                        queue_view["issuer_country_evidence_present"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        .isin({"true", "1", "yes"})
                    )
                    with triage_metrics[0]:
                        st.metric("공식 발행사 근거 확보", f"{int(evidence_present.sum()):,}개")
                    with triage_metrics[1]:
                        st.metric("신원 근거 추가 필요", f"{int((~evidence_present).sum()):,}개")
                if "sector_benchmark" in queue_view:
                    benchmark_missing = queue_view["sector_benchmark"].fillna("").astype(str).str.strip().eq("")
                    with triage_metrics[2]:
                        st.metric("승인 업종 벤치마크 공백", f"{int(benchmark_missing.sum()):,}개")
                if "suggested_sector_benchmark_coverage_status" in queue_view:
                    suggestion_usable = queue_view["suggested_sector_benchmark_coverage_status"].fillna("").astype(str).str.strip().eq("usable_for_provisional_analysis_not_approval")
                    with triage_metrics[3]:
                        st.metric("제안 ETF로 임시 RS 분석 가능", f"{int(suggestion_usable.sum()):,}개")
                st.caption(
                    "이 수치는 현재 필터의 자료 상태만 요약합니다. 근거 확보나 벤치마크 지정 여부는 "
                    "정식 편입 승인과 별개이며, 제안 ETF는 승인된 업종 매핑으로 간주하지 않습니다."
                )
            benchmark_batches_path = Path("data/sector_benchmark_review_batches.csv")
            if benchmark_batches_path.exists():
                benchmark_batches = pd.read_csv(benchmark_batches_path, dtype=str).fillna("")
                if not benchmark_batches.empty:
                    with st.expander("업종 ETF 검토 묶음 (같은 ETF는 한 번만 검토)", expanded=True):
                        st.caption(
                            "같은 제안 ETF를 사용하는 후보들을 묶어 검토 중복을 줄입니다. "
                            "이 표의 ETF는 모두 제안 단계이며, 지수 구성·업종 적합성 검토 전에는 승인 벤치마크가 아닙니다."
                        )
                        batch_columns = [
                            ("proposed_sector", "제안 업종"),
                            ("suggested_sector_benchmark", "제안 ETF"),
                            ("issuer_reference_url", "공식 운용사 자료"),
                            ("reference_scope", "근거 범위"),
                            ("official_index_methodology_url", "공식 지수 방법론"),
                            ("benchmark_scope_note", "업종 범위·주의사항"),
                            ("index_methodology_review_status", "지수 적합성 검토"),
                            ("candidate_count", "후보 수"),
                            ("candidate_symbols", "대상 종목"),
                            ("approved_sector_benchmark_count", "이미 승인된 매핑 수"),
                            ("suggested_etf_active", "ETF 가격 데이터"),
                            ("suggested_etf_latest_date", "최신 데이터일"),
                            ("review_status", "검토 상태"),
                        ]
                        batch_available = [(col, label) for col, label in batch_columns if col in benchmark_batches.columns]
                        st.dataframe(
                            benchmark_batches[[col for col, _ in batch_available]].rename(
                                columns={col: label for col, label in batch_available}
                            ),
                            use_container_width=True,
                            hide_index=True,
                        )
                        st.download_button(
                            "업종 ETF 검토 묶음 CSV 다운로드",
                            benchmark_batches.to_csv(index=False).encode("utf-8-sig"),
                            file_name="sector_benchmark_review_batches.csv",
                            mime="text/csv",
                            key="sector_benchmark_review_batches_download",
                        )
            benchmark_candidates_path = Path("data/sector_benchmark_candidate_review.csv")
            if benchmark_candidates_path.exists():
                benchmark_candidates = pd.read_csv(benchmark_candidates_path, dtype=str).fillna("")
                if not benchmark_candidates.empty:
                    with st.expander("종목별 업종 매핑 검토 체크리스트", expanded=False):
                        st.caption(
                            "후보별 발행사 근거, 제안 ETF, 공식 GICS 기준과 확인된 ETF 상위 보유종목 근거를 표시합니다. "
                            "상위 보유종목 발췌에 없다는 이유만으로 미편입이라 판단하지 않으며, 전체 보유종목 확인이 필요합니다. "
                            "사업 적합성과 최종 매핑은 미승인 상태입니다."
                        )
                        candidate_columns = [
                            ("symbol", "티커"), ("name", "종목명"),
                            ("proposed_sector", "제안 업종"),
                            ("suggested_sector_benchmark", "제안 ETF"),
                            ("identity_evidence_url", "발행사 근거"),
                            ("fund_reference_url", "ETF 자료"),
                            ("official_index_methodology_url", "공식 업종 분류 기준"),
                            ("sector_scope_note", "검토 범위"),
                            ("official_holdings_observed_date", "공식 보유종목 근거일"),
                            ("business_fit_status", "사업 적합성"),
                            ("index_membership_status", "지수 편입 검토"),
                            ("mapping_status", "매핑 상태"),
                        ]
                        candidate_available = [(col, label) for col, label in candidate_columns if col in benchmark_candidates.columns]
                        st.dataframe(
                            benchmark_candidates[[col for col, _ in candidate_available]].rename(
                                columns={col: label for col, label in candidate_available}
                            ),
                            use_container_width=True, hide_index=True,
                        )
                        st.download_button(
                            "종목별 업종 검토 CSV 다운로드",
                            benchmark_candidates.to_csv(index=False).encode("utf-8-sig"),
                            file_name="sector_benchmark_candidate_review.csv",
                            mime="text/csv", key="sector_benchmark_candidate_review_download",
                        )
            if not queue_view.empty and {"queue_priority", "next_action_ko"}.issubset(queue_view.columns):
                action_summary = (
                    queue_view.groupby(["queue_priority", "next_action_ko"], dropna=False)
                    .size()
                    .reset_index(name="후보 수")
                    .sort_values(["queue_priority", "후보 수"], ascending=[True, False])
                    .rename(columns={"queue_priority": "우선순위", "next_action_ko": "다음 작업"})
                )
                with st.expander("현재 필터의 작업량 요약", expanded=False):
                    st.dataframe(action_summary, use_container_width=True, hide_index=True)
            queue_columns = [
                ("queue_priority", "검토 우선순위"),
                ("symbol", "심볼"),
                ("name", "이름"),
                ("next_action_ko", "다음 작업"),
                ("issuer_country_evidence_present", "공식 발행사 근거 확보"),
                ("official_source_type", "공식 근거 유형"),
                ("official_source_url", "공식 발행사 근거 링크"),
                ("identity_status", "상장 식별 상태"),
                ("sector", "현재 업종"),
                ("sector_benchmark", "현재 업종 벤치마크"),
                ("proposed_sector", "제안 업종 (미승인)"),
                ("suggested_sector_benchmark", "제안 업종 ETF (미승인)"),
                ("suggested_sector_benchmark_coverage_status", "제안 ETF 데이터 상태"),
                ("depositary_ratio_status", "ADR 비율 상태"),
                ("market_cap_size_screen_result", "최소 시총 필터 ($1B)"),
                ("market_cap_status", "공식 시총 검증 상태"),
                ("provider_status", "KIS 지원 상태"),
                ("activation_gate_status", "활성화 게이트"),
                ("activation_recommendation", "권고"),
            ]
            queue_available = [(col, label) for col, label in queue_columns if col in review_queue.columns]
            st.dataframe(
                queue_view[[col for col, _ in queue_available]].rename(
                    columns={col: label for col, label in queue_available}
                ),
                use_container_width=True,
                hide_index=True,
            )
            blocker_columns = [
                ("queue_priority", "검토 우선순위"),
                ("symbol", "심볼"),
                ("name", "이름"),
                ("review_blocker_count", "차단 항목 수"),
                ("review_blockers_ko", "남은 검토 항목"),
                ("identity_status", "상장 식별 상태"),
                ("depositary_ratio_status", "ADR 비율 상태"),
                ("market_cap_size_screen_result", "최소 시총 필터 ($1B)"),
                ("market_cap_status", "공식 시총 검증 상태"),
                ("provider_status", "KIS 지원 상태"),
            ]
            blocker_available = [(col, label) for col, label in blocker_columns if col in queue_view.columns]
            if blocker_available and not queue_view.empty:
                with st.expander("종목별 편입 차단 사유 상세", expanded=False):
                    st.caption(
                        "아래 항목은 현재 보고서가 기록한 미해결 사항입니다. "
                        "차단 항목 수는 검토 우선순위를 돕는 집계값이며, 항목이 없거나 가격이 수집됐다고 해서 자동 승인되는 것은 아닙니다."
                    )
                    st.dataframe(
                        queue_view[[col for col, _ in blocker_available]].rename(
                            columns={col: label for col, label in blocker_available}
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
            st.download_button(
                "통합 후보 검토 대기열 CSV 다운로드",
                queue_view.to_csv(index=False).encode("utf-8-sig"),
                file_name="candidate_review_queue_filtered.csv",
                mime="text/csv",
                key="candidate_review_queue_download",
            )
            with st.expander("검토 대기열 집계 상세", expanded=False):
                st.dataframe(queue_summary, use_container_width=True, hide_index=True)
                st.download_button(
                    "검토 대기열 집계 CSV 다운로드",
                    queue_summary.to_csv(index=False).encode("utf-8-sig"),
                    file_name="candidate_review_queue_summary.csv",
                    mime="text/csv",
                    key="candidate_review_queue_summary_download",
                )
        else:
            st.info("검토 대기열 파일은 있지만 후보 행이 없습니다.")
    else:
        st.info("검토 대기열 보고서가 아직 생성되지 않았습니다. 다음 후보 커버리지 보고서 작업에서 생성됩니다.")

with st.expander("데이터 상태 상세 및 보류 사유", expanded=False):
    status_detail = screen[[
        c for c in [
            "symbol", "name", "asset_type_norm", "market", "last_daily_date", "last_date",
            "stage_label", "stage_analysis_status", "data_gap_calendar_days", "data_stale", "benchmark_data_stale", "benchmark_data_missing",
            "market_benchmark", "sector_benchmark", "market_cap_review_status",
        ] if c in screen.columns
    ]].copy()
    def describe_data_issues(row):
        issues = []
        if bool(row.get("data_stale", False)):
            issues.append("자산 가격 데이터 오래됨")
        if bool(row.get("benchmark_data_stale", False)):
            issues.append("벤치마크 데이터 오래됨")
        if bool(row.get("benchmark_data_missing", False)):
            issues.append("벤치마크 누락/상대강도 계산 불가")
        if str(row.get("stage_label", "")).find("판정 보류") >= 0 or str(row.get("stage_label", "")).find("데이터 부족") >= 0:
            issues.append("Stage 판정 보류")
        if pd.notna(row.get("market_cap_review_status")) and str(row.get("market_cap_review_status")).strip() not in {"", "verified", "검증 완료", "not_applicable", "해당 없음"}:
            issues.append("시가총액 별도 검토")
        return " · ".join(dict.fromkeys(issues)) if issues else "표시된 기본 가드 통과"
    status_detail["데이터 상태 / 검토 항목"] = status_detail.apply(describe_data_issues, axis=1)
    status_detail["Stage 판정 상태"] = status_detail["stage_label"].map(
        lambda value: "판정 보류" if ("판정 보류" in str(value) or "데이터 부족" in str(value)) else "Stage 분류 표시"
    )
    status_detail = status_detail.rename(columns={
        "symbol": "심볼", "name": "이름", "asset_type_norm": "자산 유형",
        "market": "시장", "last_daily_date": "최근 일봉 기준일", "last_date": "완료 주봉 기준일",
        "data_stale": "자산 데이터 오래됨", "benchmark_data_stale": "벤치마크 오래됨",
        "benchmark_data_missing": "벤치마크 누락", "stage_label": "현재 Stage 분류", "stage_analysis_status": "분석 상태", "data_gap_calendar_days": "기준일 지연(달력일)", "market_benchmark": "시장 벤치마크",
        "sector_benchmark": "업종 벤치마크", "market_cap_review_status": "시총 상태",
    })
    st.dataframe(status_detail, use_container_width=True, hide_index=True)
    st.caption(
        "‘기본 데이터 가드 통과’는 시세·종목 분류·시가총액의 정확성이 완전히 검증됐다는 뜻이 아닙니다. "
        "기준일과 보류 원인을 확인하고, 시가총액은 별도 상태 열을 함께 확인하세요."
    )

if mode == "가상 데모":
    st.info("가상 데이터입니다. 실제 시세·시장 분류·시가총액을 반영하지 않습니다.")
elif mode == "KIS API · 미국·한국":
    st.info("KIS 미국/한국 실제 시세를 사용합니다. 시가총액·업종 분류는 유니버스 메타데이터를 따르며 자동 검증되지 않습니다.")

# 목록에서 선택한 종목과 차트 화면에서 선택한 종목을 같은 세션 상태로 유지한다.
view_mode = st.radio("화면 표시", ["목록", "3×3 차트"], horizontal=True, key="global_view_mode")
st.caption(
    "차트마다 일봉·주봉을 독립적으로 선택할 수 있습니다. "
    "Stage 판정과 표의 30주선·상대강도는 화면 주기 선택과 관계없이 완료된 주봉 기준입니다."
)

def make_price_chart(symbol, compact=False, period_is_weekly=True, chart_period="주봉"):
    """Create a scroll-zoomable OHLC chart with volume beneath price."""
    if period_is_weekly:
        chart_data = weekly_by_symbol.get(symbol)
        if chart_data is None or chart_data.empty:
            return None
        chart_data = chart_data.copy()
        ma_label = "30주 이동평균"
        ma_values = chart_data["ma30"] if "ma30" in chart_data else chart_data["close"].rolling(30).mean()
    else:
        chart_data = prices.loc[prices["symbol"].astype(str).str.upper().eq(str(symbol).upper())].copy()
        if chart_data.empty:
            return None
        chart_data = chart_data.sort_values("date")
        chart_data["ma30_daily"] = chart_data["close"].rolling(30, min_periods=30).mean()
        ma_label = "30일 이동평균"
        ma_values = chart_data["ma30_daily"]

    # Show close-to-close percentage change in the candlestick hover for both daily and weekly charts.
    chart_data["change_pct"] = chart_data["close"].pct_change() * 100
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.035, row_heights=[0.76, 0.24])
    fig.add_trace(go.Candlestick(
        x=chart_data["date"], open=chart_data["open"], high=chart_data["high"],
        low=chart_data["low"], close=chart_data["close"], name=chart_period,
        customdata=chart_data["change_pct"].to_numpy(),
        increasing_line_width=1, decreasing_line_width=1,
        hovertemplate="%{x|%Y-%m-%d}<br>시가: %{open:,.2f}<br>고가: %{high:,.2f}<br>저가: %{low:,.2f}<br>종가: %{close:,.2f}<br>전일/전주 대비: %{customdata:+.2f}%<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=chart_data["date"], y=ma_values, name=ma_label, line=dict(width=1.5),
        hovertemplate=ma_label + ": %{y:,.2f}<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=chart_data["date"], y=chart_data["volume"], name="거래량", marker_line_width=0,
        hovertemplate="%{x|%Y-%m-%d}<br>거래량: %{y:,.0f}<extra></extra>",
    ), row=2, col=1)
    fig.update_layout(
        height=440 if compact else 680,
        margin=dict(l=5 if compact else 20, r=5 if compact else 20, t=28, b=5),
        title=dict(text=str(symbol), x=0.02, xanchor="left", font=dict(size=13 if compact else 18)),
        showlegend=False if compact else True, hovermode="x unified", dragmode="pan",
        xaxis_rangeslider_visible=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=8 if compact else 11)),
        yaxis=dict(showgrid=True, tickfont=dict(size=8 if compact else 11), title_text="가격"),
        yaxis2=dict(showgrid=False, tickfont=dict(size=8 if compact else 10), title_text="거래량"),
    )
    return fig

def render_pending_candidate_chart_explorer():
    """Show a review-only price chart for pending candidates without activating them."""
    report_path = Path("data/provisional_candidate_stage_report.csv")
    candidate_prices_path = Path("data/candidate_daily_prices.csv")
    if not report_path.exists() or not candidate_prices_path.exists():
        return
    try:
        report = pd.read_csv(report_path, dtype={"symbol": str}).fillna("")
        candidate_prices = read_prices(candidate_prices_path)
    except Exception as exc:
        st.warning(f"보류 후보 차트 자료를 읽지 못했습니다: {type(exc).__name__}: {str(exc)[:180]}")
        return
    if report.empty or candidate_prices.empty or "symbol" not in report.columns:
        return
    report["symbol"] = report["symbol"].astype(str).str.strip()
    candidate_prices["symbol"] = candidate_prices["symbol"].astype(str).str.strip()
    available_symbols = set(candidate_prices["symbol"])
    report = report[report["symbol"].isin(available_symbols)].copy()
    if report.empty:
        return
    with st.expander("보류 후보 차트 탐색 · 정식 활성화와 분리", expanded=False):
        st.caption(
            "검토 대기 후보의 가격 차트를 바로 확인하는 기능입니다. "
            "Stage/업종 RS는 제안된 업종 ETF를 참고할 수 있으며, 이 ETF는 아직 승인된 벤치마크가 아닙니다. "
            "차트와 예비 판정은 후보를 정식 유니버스에 편입하거나 승인하지 않습니다."
        )
        report = report.sort_values(
            ["provisional_stage_label", "symbol"] if "provisional_stage_label" in report.columns else ["symbol"]
        )
        candidate_exchange_by_symbol = {}
        registry_path = Path("data/stock_universe_candidates.csv")
        if registry_path.exists():
            try:
                registry = pd.read_csv(registry_path, dtype={"symbol": str}).fillna("")
                if {"symbol", "exchange"}.issubset(registry.columns):
                    candidate_exchange_by_symbol = dict(zip(
                        registry["symbol"].astype(str).str.strip(),
                        registry["exchange"].astype(str).str.strip().str.upper(),
                    ))
            except Exception:
                candidate_exchange_by_symbol = {}
        chart_filters = st.columns([2, 1, 1])
        with chart_filters[0]:
            chart_search = st.text_input(
                "후보 검색 (심볼/회사명)",
                key="pending_candidate_chart_search",
                placeholder="예: NVDA, 삼성전자",
            )
        with chart_filters[1]:
            stage_values = sorted(report["provisional_stage_label"].astype(str).unique()) if "provisional_stage_label" in report.columns else []
            chart_stage = st.selectbox(
                "예비 Stage 필터", ["전체"] + stage_values,
                key="pending_candidate_chart_stage_filter",
            )
        with chart_filters[2]:
            sector_values = sorted(report["proposed_sector"].astype(str).str.strip().replace("", "미분류").unique()) if "proposed_sector" in report.columns else []
            chart_sector = st.selectbox(
                "제안 업종 필터", ["전체"] + sector_values,
                key="pending_candidate_chart_sector_filter",
            )
        chart_choices = report.copy()
        if chart_sector != "전체" and "proposed_sector" in chart_choices.columns:
            sector_key = chart_choices["proposed_sector"].astype(str).str.strip().replace("", "미분류")
            chart_choices = chart_choices[sector_key.eq(chart_sector)]
        if chart_search.strip():
            needle = chart_search.strip().casefold()
            mask = chart_choices["symbol"].astype(str).str.casefold().str.contains(needle, regex=False, na=False)
            if "name" in chart_choices.columns:
                mask |= chart_choices["name"].astype(str).str.casefold().str.contains(needle, regex=False, na=False)
            chart_choices = chart_choices[mask]
        if chart_stage != "전체" and "provisional_stage_label" in chart_choices.columns:
            chart_choices = chart_choices[chart_choices["provisional_stage_label"].astype(str).eq(chart_stage)]
        if chart_choices.empty:
            st.info("검색/필터에 해당하는 후보가 없습니다.")
            return
        labels = {
            str(row["symbol"]): (
                f'{row.get("name", row["symbol"])} ({row["symbol"]}) · '
                f'{row.get("provisional_stage_label", "예비 판정 없음")}'
            )
            for _, row in chart_choices.iterrows()
        }
        selected = st.selectbox(
            "검토 후보 선택",
            options=chart_choices["symbol"].astype(str).tolist(),
            format_func=lambda symbol: labels.get(str(symbol), str(symbol)),
            key="pending_candidate_chart_symbol",
        )
        period = st.radio(
            "후보 차트 주기", ["일봉", "주봉"], horizontal=True,
            key="pending_candidate_chart_period",
        )
        daily = candidate_prices[candidate_prices["symbol"].eq(selected)].sort_values("date").copy()
        if period == "주봉":
            exchange_hint = candidate_exchange_by_symbol.get(str(selected), "")
            calendar_name = "XNYS" if exchange_hint in {"NAS", "NYS", "AMS"} else "XKRX"
            # Charts remain available for short-history candidates; the 35-week
            # minimum applies to Stage classification, not to viewing raw price history.
            chart_data = weekly_bars(daily, calendar_name=calendar_name, min_bars=1)
            if chart_data is None or chart_data.empty:
                st.warning("유효한 완료 주봉 데이터가 없어 차트를 표시할 수 없습니다.")
                return
            if len(chart_data) < 35:
                st.warning(
                    f"완료 주봉 {len(chart_data)}개만 확보되어 Stage 판정에는 이력이 부족합니다. "
                    "가격 차트는 참고용으로 표시하며, 30주선은 데이터가 충분할 때부터 나타납니다."
                )
            ma = chart_data["ma30"]
            ma_name = "30주 이동평균"
        else:
            chart_data = daily.copy()
            if chart_data.empty:
                st.warning("선택한 후보의 일봉 데이터가 없습니다.")
                return
            ma = chart_data["close"].rolling(30, min_periods=30).mean()
            ma_name = "30일 이동평균"
        chart_data["change_pct"] = chart_data["close"].pct_change() * 100
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.035, row_heights=[0.76, 0.24])
        fig.add_trace(go.Candlestick(
            x=chart_data["date"], open=chart_data["open"], high=chart_data["high"],
            low=chart_data["low"], close=chart_data["close"], name=period,
            customdata=chart_data["change_pct"].to_numpy(),
            hovertemplate="%{x|%Y-%m-%d}<br>시가: %{open:,.2f}<br>고가: %{high:,.2f}<br>저가: %{low:,.2f}<br>종가: %{close:,.2f}<br>전일/전주 대비: %{customdata:+.2f}%<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=chart_data["date"], y=ma, name=ma_name, line=dict(width=1.5),
            hovertemplate=ma_name + ": %{y:,.2f}<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            x=chart_data["date"], y=chart_data["volume"], name="거래량",
            hovertemplate="%{x|%Y-%m-%d}<br>거래량: %{y:,.0f}<extra></extra>",
        ), row=2, col=1)
        fig.update_layout(
            height=620, margin=dict(l=15, r=15, t=35, b=10),
            title=dict(text=labels.get(selected, selected), x=0.02, xanchor="left"),
            hovermode="x unified", dragmode="pan", xaxis_rangeslider_visible=False,
            yaxis=dict(title_text="가격"), yaxis2=dict(title_text="거래량"),
        )
        st.plotly_chart(
            fig, use_container_width=True, key="pending_candidate_review_chart",
            config={"scrollZoom": True, "displayModeBar": True},
        )
        selected_row = report[report["symbol"].eq(selected)]
        if not selected_row.empty:
            detail = selected_row.iloc[0]
            detail_cols = [
                ("provisional_stage_label", "예비 Stage"),
                ("proposed_sector", "제안 업종 (미승인)"),
                ("completed_weekly_date", "완료 주봉 기준일"),
                ("weekly_bars", "완료 주봉 수"),
                ("market_rs_26w_pct", "시장 대비 RS(26주, %p)"),
                ("suggested_sector_benchmark", "제안 업종 ETF (미승인)"),
                ("sector_rs_26w_pct", "제안 업종 ETF 대비 RS(26주, %p · 미승인 기준)"),
                ("volume_context", "거래량 참고"),
                ("data_status", "데이터 상태"),
                ("activation_status", "정식 편입 상태"),
                ("review_note", "검토 메모"),
            ]
            values = [
                {"항목": label, "내용": str(detail.get(column, ""))}
                for column, label in detail_cols if column in report.columns
            ]
            if values:
                st.dataframe(pd.DataFrame(values), use_container_width=True, hide_index=True)


def open_symbol_detail(area_key, symbol):
    """Switch from the chart grid to the selected symbol's full chart."""
    st.session_state["global_view_mode"] = "목록"
    st.session_state[f"{area_key}_selected_symbol"] = str(symbol)


def render_asset_area(area_key, title, subset):
    st.subheader(title)
    if subset.empty:
        st.info("이 영역에 표시할 자산이 없습니다. 유니버스 CSV에 해당 유형을 추가하면 여기에 표시됩니다.")
        return
    filters = st.columns(2)
    available_markets = sorted(subset["market"].dropna().astype(str).unique())
    with filters[0]:
        market_choice = st.selectbox(
            "국가 / 시장", ["전체"] + available_markets, key=f"{area_key}_market"
        )
    filtered = subset if market_choice == "전체" else subset[subset["market"].astype(str).eq(market_choice)]
    available_groups = sorted(filtered["sector"].dropna().astype(str).unique())
    with filters[1]:
        group_choice = st.selectbox(
            "그룹 / 업종", ["전체"] + available_groups, key=f"{area_key}_group"
        )
    filtered = filtered if group_choice == "전체" else filtered[filtered["sector"].astype(str).eq(group_choice)]

    refinement = st.columns([1, 1, 2])
    stage_options = ["전체"] + sorted(filtered["stage_label"].dropna().astype(str).unique())
    with refinement[0]:
        stage_choice = st.selectbox("Stage 필터", stage_options, key=f"{area_key}_stage_filter")
    sort_options = ["시장 대비 상대강도", "업종 대비 상대강도", "30주선 기울기"]
    if subset["asset_type_norm"].astype(str).str.lower().eq("stock").any():
        sort_options.append("시가총액")
    with refinement[1]:
        sort_choice = st.selectbox(
            "정렬 기준", sort_options, key=f"{area_key}_sort",
        )
    with refinement[2]:
        search_text = st.text_input(
            "종목명 / 심볼 검색", key=f"{area_key}_search",
            placeholder="예: NVDA, 삼성전자",
        )

    if stage_choice != "전체":
        filtered = filtered[filtered["stage_label"].astype(str).eq(stage_choice)]
    if search_text.strip():
        needle = search_text.strip().casefold()
        searchable = filtered["symbol"].astype(str).str.casefold().str.contains(needle, na=False, regex=False)
        if "name" in filtered.columns:
            searchable = searchable | filtered["name"].astype(str).str.casefold().str.contains(needle, na=False, regex=False)
        filtered = filtered[searchable]
    if filtered.empty:
        st.info("선택한 조건에 해당하는 자산이 없습니다.")
        return
    st.caption(f"{len(filtered)}개 자산 · 표의 행을 선택하면 해당 차트를 바로 엽니다.")
    sort_columns = {
        "시장 대비 상대강도": "rs_market_26w_pct",
        "업종 대비 상대강도": "rs_sector_26w_pct",
        "30주선 기울기": "slope4_pct",
        "시가총액": "market_cap_usd",
    }
    sort_column = sort_columns[sort_choice]
    sorted_view = filtered.sort_values(
        sort_column, ascending=False, na_position="last"
    ).reset_index(drop=True)
    table_cols = [
        "symbol", "name", "market", "sector", "close", "slope4_pct",
        "rs_market_26w_pct", "rs_sector_26w_pct", "stage_label", "volume_confirmation",
        "last_date", "last_daily_date", "data_gap_calendar_days", "stage_analysis_status"
    ]
    if subset["asset_type_norm"].astype(str).str.lower().eq("stock").any():
        table_cols.extend(["market_cap_usd", "market_cap_review_status"])
    table = sorted_view[[c for c in table_cols if c in sorted_view.columns]].copy()
    table = table.rename(columns={
        "symbol": "심볼", "name": "이름", "market": "국가/시장", "sector": "업종/그룹",
        "close": "최근 종가", "slope4_pct": "30주선 기울기(%)",
        "rs_market_26w_pct": "시장 대비 26주(%)",
        "rs_sector_26w_pct": "업종 대비 26주(%)",
        "stage_label": "Stage", "volume_confirmation": "거래량 참고 신호", "last_date": "주봉 기준일", "last_daily_date": "최근 일봉 데이터일", "data_gap_calendar_days": "기준일 지연(달력일)", "stage_analysis_status": "분석 상태",
        "market_cap_usd": "시가총액($B)", "market_cap_review_status": "시가총액 상태",
    })
    for col in ("30주선 기울기(%)", "시장 대비 26주(%)", "업종 대비 26주(%)"):
        if col in table.columns:
            table[col] = pd.to_numeric(table[col], errors="coerce").round(2)
    if "최근 종가" in table.columns:
        table["최근 종가"] = pd.to_numeric(table["최근 종가"], errors="coerce").round(2)
    if "시가총액($B)" in table.columns:
        # Keep sorting on the original USD value in sorted_view, but display billions.
        table["시가총액($B)"] = (
            pd.to_numeric(table["시가총액($B)"], errors="coerce") / 1_000_000_000
        ).round(2)

    st.download_button(
        f"{title} 현재 필터 결과 CSV 다운로드",
        sorted_view.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{area_key}_screen.csv",
        mime="text/csv",
        key=f"{area_key}_screen_download",
    )

    if view_mode == "목록":
        selection = st.dataframe(
            table, use_container_width=True, hide_index=True,
            on_select="rerun", selection_mode="single-row",
            key=f"{area_key}_asset_table",
        )
        selected_symbol = None
        try:
            selected_rows = selection.selection.rows
            if selected_rows:
                selected_symbol = str(sorted_view.iloc[selected_rows[0]]["symbol"])
        except Exception:
            selected_symbol = None
        if selected_symbol:
            st.session_state[f"{area_key}_selected_symbol"] = selected_symbol
        remembered = st.session_state.get(f"{area_key}_selected_symbol")
        available_symbols = set(sorted_view["symbol"].astype(str))
        if remembered not in available_symbols:
            remembered = str(sorted_view.iloc[0]["symbol"])
            st.session_state[f"{area_key}_selected_symbol"] = remembered
        chart_row = sorted_view[sorted_view["symbol"].astype(str).eq(remembered)].iloc[0]
        st.markdown(f"#### {chart_row['name']} ({remembered})")
        st.caption(
            f"Stage: {chart_row['stage_label']} · "
            f"기준일: {pd.to_datetime(chart_row['last_date']).date()}"
        )
        chart_period = st.radio(
            "차트 주기", ["일봉", "주봉"], index=1, horizontal=True,
            key=f"{area_key}_selected_period_{remembered}",
        )
        fig = make_price_chart(
            remembered, period_is_weekly=(chart_period == "주봉"), chart_period=chart_period
        )
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True, key=f"{area_key}_selected_chart", config={"scrollZoom": True, "displayModeBar": True})
        else:
            st.warning("선택한 자산의 차트 데이터를 찾을 수 없습니다.")
    else:
        default_symbols = sorted_view["symbol"].astype(str).head(9).tolist()
        chosen = st.multiselect(
            "차트에 표시할 자산 (최대 9개)", sorted_view["symbol"].astype(str).tolist(),
            default=default_symbols, max_selections=9, key=f"{area_key}_grid_symbols",
        )
        if not chosen:
            st.info("차트에 표시할 자산을 선택하세요.")
            return
        # Use the detail button above a chart to open its full-size chart in list view.
        for offset in range(0, len(chosen), 3):
            grid_cols = st.columns(3)
            for col, symbol in zip(grid_cols, chosen[offset:offset + 3]):
                with col:
                    row = sorted_view[sorted_view["symbol"].astype(str).eq(symbol)]
                    if not row.empty:
                        st.caption(f"{row.iloc[0]['name']} · {row.iloc[0]['stage_label']} · 주봉 기준일: {pd.to_datetime(row.iloc[0]['last_date']).date()}")
                    st.button(
                        f"{symbol} 상세 차트 열기",
                        key=f"{area_key}_detail_{symbol}",
                        use_container_width=True,
                        on_click=open_symbol_detail,
                        args=(area_key, symbol),
                    )
                    chart_period = st.radio(
                        "일봉 / 주봉", ["일봉", "주봉"], index=1, horizontal=True,
                        key=f"{area_key}_grid_period_{symbol}",
                        label_visibility="collapsed",
                    )
                    fig = make_price_chart(
                        symbol, compact=True, period_is_weekly=(chart_period == "주봉"),
                        chart_period=chart_period,
                    )
                    if fig is not None:
                        st.plotly_chart(fig, use_container_width=True, key=f"{area_key}_grid_{symbol}", config={"scrollZoom": True, "displayModeBar": True})

# 전체 시장의 Stage 분포를 각 탭에 들어가기 전에 한눈에 비교한다.
st.subheader("시장 레이더 요약")
stage_order = [
    "Stage 2 후보",
    "Stage 2A 관찰 후보",
    "Stage 1 바닥 형성",
    "Stage 3 천장 형성",
    "Stage 4 하락 추세",
    "판정 보류",
]
stage_counts = screen["stage_label"].astype(str).value_counts()
summary_cols = st.columns(4)
summary_cols[0].metric("분석 자산", f"{len(screen):,}")
summary_cols[1].metric("Stage 2 후보", f"{int(stage_counts.get('Stage 2 후보', 0)):,}")
summary_cols[2].metric("Stage 2A 관찰", f"{int(stage_counts.get('Stage 2A 관찰 후보', 0)):,}")
data_hold_mask = (
    screen["data_stale"].fillna(False).astype(bool)
    | screen["benchmark_data_stale"].fillna(False).astype(bool)
    | screen["benchmark_data_missing"].fillna(False).astype(bool)
    | screen["stage_label"].astype(str).str.contains("판정 보류|데이터 부족", regex=True, na=False)
)
summary_cols[3].metric(
    "데이터/벤치마크 보류",
    f"{int(data_hold_mask.sum()):,}",
)
area_label_map = {
    "stock": "종목",
    "sector_etf": "업종",
    "market_etf": "국가/시장 ETF",
    "commodity_etf": "원자재 ETF",
    "commodity": "원자재",
}
stage_summary = screen.assign(
    영역=screen["asset_type_norm"].map(area_label_map).fillna("기타"),
    Stage=screen["stage_label"].astype(str),
).pivot_table(index="영역", columns="Stage", values="symbol", aggfunc="count", fill_value=0)
for stage_name in stage_order:
    if stage_name not in stage_summary.columns:
        stage_summary[stage_name] = 0
stage_summary = stage_summary[stage_order].astype(int)
stage_summary["전체"] = stage_summary.sum(axis=1)
stage_summary.loc["전체"] = stage_summary.sum(axis=0)
st.dataframe(stage_summary, use_container_width=True)
st.caption(
    "Stage 분포는 현재 로드된 유니버스와 가격 데이터에 한정됩니다. "
    "데이터 또는 벤치마크가 부족한 자산은 정상적인 Stage 후보로 해석하지 마세요."
)

# 강한 추세 후보를 별도 비교표로 제공한다. Stage 판정 규칙은 변경하지 않는다.
with st.expander("Stage 2 후보 빠른 비교", expanded=True):
    candidate_labels = ["Stage 2 후보", "Stage 2A 관찰 후보"]
    candidates = screen[screen["stage_label"].astype(str).isin(candidate_labels)].copy()
    if candidates.empty:
        st.info("현재 데이터에서 Stage 2 또는 Stage 2A 후보가 없습니다. 데이터 부족·보류 자산은 별도로 확인하세요.")
    else:
        candidate_controls = st.columns([1, 1, 2])
        with candidate_controls[0]:
            candidate_stage = st.selectbox(
                "후보 유형", ["Stage 2 + 2A", "Stage 2만", "Stage 2A만"],
                key="candidate_quick_stage",
            )
        with candidate_controls[1]:
            candidate_area = st.selectbox(
                "자산 영역", ["전체", "종목", "업종", "국가/시장 ETF", "원자재 ETF", "원자재"],
                key="candidate_quick_area",
            )
        with candidate_controls[2]:
            candidate_search = st.text_input(
                "후보 검색", placeholder="이름 또는 심볼", key="candidate_quick_search",
            )
        if candidate_stage == "Stage 2만":
            candidates = candidates[candidates["stage_label"].astype(str).eq("Stage 2 후보")]
        elif candidate_stage == "Stage 2A만":
            candidates = candidates[candidates["stage_label"].astype(str).eq("Stage 2A 관찰 후보")]
        candidate_area_map = {
            "종목": ["stock"], "업종": ["sector_etf"], "국가/시장 ETF": ["market_etf"],
            "원자재 ETF": ["commodity_etf"], "원자재": ["commodity"],
        }
        if candidate_area != "전체":
            candidates = candidates[candidates["asset_type_norm"].isin(candidate_area_map[candidate_area])]
        if candidate_search.strip():
            needle = candidate_search.strip().casefold()
            mask = candidates["symbol"].astype(str).str.casefold().str.contains(needle, regex=False, na=False)
            if "name" in candidates:
                mask |= candidates["name"].astype(str).str.casefold().str.contains(needle, regex=False, na=False)
            candidates = candidates[mask]
        if candidates.empty:
            st.info("현재 조건에 맞는 후보가 없습니다.")
        else:
            candidate_sort = st.selectbox(
                "후보 정렬",
                ["시장 대비 상대강도", "업종 대비 상대강도", "30주선 기울기", "26주 수익률"],
                key="candidate_quick_sort",
            )
            candidate_sort_cols = {
                "시장 대비 상대강도": "rs_market_26w_pct",
                "업종 대비 상대강도": "rs_sector_26w_pct",
                "30주선 기울기": "slope4_pct",
                "26주 수익률": "ret26_pct",
            }
            candidates = candidates.sort_values(
                candidate_sort_cols[candidate_sort], ascending=False, na_position="last"
            ).reset_index(drop=True)
            candidate_total = len(candidates)
            candidate_table_cols = [
                "symbol", "name", "market", "sector", "stage_label", "close",
                "slope4_pct", "rs_market_26w_pct", "rs_sector_26w_pct", "ret26_pct",
                "volume_confirmation", "last_date",
            ]
            candidate_table = candidates.head(25)[[c for c in candidate_table_cols if c in candidates.columns]].rename(columns={
                "symbol": "심볼", "name": "이름", "market": "시장", "sector": "업종",
                "stage_label": "Stage", "close": "최근 종가", "slope4_pct": "30주선 기울기(%)",
                "rs_market_26w_pct": "시장 대비 26주(%)", "rs_sector_26w_pct": "업종 대비 26주(%)",
                "ret26_pct": "26주 수익률(%)", "volume_confirmation": "거래량 참고 신호",
                "last_date": "주봉 기준일",
            })
            st.caption(f"조건에 맞는 후보 {candidate_total:,}개 중 상위 {len(candidate_table):,}개 표시 · 정렬은 매수 신호나 성과 예측 점수가 아닙니다.")
            st.dataframe(candidate_table, use_container_width=True, hide_index=True)
            st.download_button(
                "조건에 맞는 전체 후보 CSV 다운로드",
                candidates.to_csv(index=False).encode("utf-8-sig"),
                file_name="stage_2_candidates.csv",
                mime="text/csv",
                key="candidate_quick_download",
            )
            candidate_names = {
                str(row["symbol"]): f'{row.get("name", row["symbol"])} ({row["symbol"]}) · {row["stage_label"]}'
                for _, row in candidates.iterrows()
            }
            watchlist_symbols = st.multiselect(
                "관심 후보 선택",
                options=candidates["symbol"].astype(str).tolist(),
                format_func=lambda symbol: candidate_names.get(str(symbol), str(symbol)),
                key="candidate_watchlist_symbols",
                help="선택한 후보는 현재 앱 세션에 유지됩니다. 앱을 다시 열어도 보존되는 영구 저장은 아닙니다.",
            )
            if watchlist_symbols:
                watchlist = candidates[candidates["symbol"].astype(str).isin(watchlist_symbols)].copy()
                st.caption(f"관심 후보 {len(watchlist):,}개 · 현재 세션에서 선택한 목록")
                st.dataframe(
                    watchlist[[c for c in candidate_table_cols if c in watchlist.columns]].rename(columns={
                        "symbol": "심볼", "name": "이름", "market": "시장", "sector": "업종",
                        "stage_label": "Stage", "close": "최근 종가", "slope4_pct": "30주선 기울기(%)",
                        "rs_market_26w_pct": "시장 대비 26주(%)", "rs_sector_26w_pct": "업종 대비 26주(%)",
                        "ret26_pct": "26주 수익률(%)", "volume_confirmation": "거래량 참고 신호",
                        "last_date": "주봉 기준일",
                    }),
                    use_container_width=True, hide_index=True,
                )
                st.download_button(
                    "관심 후보 CSV 다운로드",
                    watchlist.to_csv(index=False).encode("utf-8-sig"),
                    file_name="stage_2_watchlist.csv",
                    mime="text/csv",
                    key="candidate_watchlist_download",
                )

# 각 영역은 asset_type으로 분리한다. ETF는 종목 시가총액 필터를 적용받지 않는다.
area_specs = [
    ("markets_commodities", "국가 및 원자재", screen[
        screen["asset_type_norm"].isin(["market_etf", "commodity_etf", "commodity"])
    ]),
    ("sectors", "업종", screen[screen["asset_type_norm"].eq("sector_etf")]),
    ("stocks", "종목", screen[screen["asset_type_norm"].eq("stock")]),
]
st.caption(
    f"현재 분석 가능한 자산: 종목 {len(area_specs[2][2])}개 · "
    f"업종 ETF {len(area_specs[1][2])}개 · "
    f"국가/원자재 {len(area_specs[0][2])}개"
)
tabs = st.tabs([
    f"{spec[1]} ({len(spec[2])})" for spec in area_specs
])
for tab, spec in zip(tabs, area_specs):
    with tab:
        area_key, area_title, area_frame = spec
        render_asset_area(area_key, area_title, area_frame)
        if area_key == "stocks":
            st.divider()
            render_pending_candidate_chart_explorer()

# 후보 종목의 검토 현황은 활성 분석 유니버스와 분리해 표시한다.
with st.expander("종목 편입 검토 현황 · 활성 종목과 분리", expanded=False):
    st.caption(
        "아래 후보는 Stage 분석 종목으로 자동 편입되지 않습니다. "
        "식별·KIS 지원·가격 이력·벤치마크·시가총액 검토가 끝나고 명시적으로 승인된 종목만 활성 유니버스에 들어갑니다."
    )
    candidate_registry_path = Path("data/stock_universe_candidates.csv")
    if candidate_registry_path.exists():
        try:
            review_registry = pd.read_csv(candidate_registry_path, dtype={"symbol": str}).fillna("")
            if "activation_status" in review_registry.columns:
                review_status_counts = review_registry["activation_status"].astype(str).value_counts()
                review_cols = st.columns(3)
                review_cols[0].metric("검토 후보", f"{len(review_registry):,}")
                review_cols[1].metric(
                    "검토 대기",
                    f"{int(review_status_counts.get('pending_review', 0)):,}",
                )
                review_cols[2].metric(
                    "활성 상태 후보",
                    f"{int(review_status_counts.get('active', 0)):,}",
                )
            review_queue_path = Path("data/candidate_review_queue_summary.csv")
            if review_queue_path.exists():
                review_queue = pd.read_csv(review_queue_path).fillna("")
                summary_type_labels = {
                    "queue_priority": "검토 우선순위",
                    "activation_gate_status": "활성화 게이트",
                    "activation_recommendation": "활성화 권고",
                    "mapping_suggestion_status": "매핑 제안 상태",
                    "price_history_status": "가격 이력 상태",
                    "suggested_sector_benchmark_coverage": "제안 업종 벤치마크 데이터 상태",
                }
                benchmark_status_labels = {
                    "suggestion_missing": "업종 벤치마크 제안 없음",
                    "benchmark_inactive_or_no_snapshot_rows": "벤치마크 비활성 또는 가격 데이터 없음",
                    "benchmark_snapshot_stale": "벤치마크 가격 데이터 지연",
                    "usable_for_provisional_analysis_not_approval": "예비 분석 데이터 확보(매핑 승인 아님)",
                    "suggestion_missing_or_coverage_incomplete": "제안 누락 또는 데이터 커버리지 미완료",
                }
                if "summary_type" in review_queue.columns:
                    review_queue["summary_type"] = review_queue["summary_type"].map(
                        summary_type_labels
                    ).fillna(review_queue["summary_type"])
                if "category" in review_queue.columns:
                    review_queue["category"] = review_queue["category"].map(
                        benchmark_status_labels
                    ).fillna(review_queue["category"])
                st.caption("우선순위별 검토 작업량 및 벤치마크 데이터 준비 상태")
                st.dataframe(review_queue, use_container_width=True, hide_index=True)

            # Detailed queue shows sourced issuer evidence without treating it as approval.
            detailed_queue_path = Path("data/candidate_review_queue.csv")
            if detailed_queue_path.exists():
                try:
                    detailed_queue = pd.read_csv(detailed_queue_path, dtype={"symbol": str}).fillna("")
                    st.caption("후보별 상세 검토 · 공식 근거는 참고 자료이며 자동 승인 근거가 아닙니다.")
                    detail_cols = [
                        "symbol", "name", "queue_priority", "next_action_ko",
                        "market", "sector", "proposed_market", "proposed_sector",
                        "market_benchmark", "sector_benchmark",
                        "proposed_market_benchmark", "proposed_sector_benchmark",
                        "suggested_sector_benchmark_coverage_status",
                        "candidate_price_rows", "candidate_history_150_plus_bars",
                        "candidate_latest_price_date", "market_cap_size_screen",
                        "issuer_country", "listing_market", "security_type",
                        "official_source_type", "official_source_url",
                        "source_observed_date", "review_outcome", "remaining_gates",
                        "activation_recommendation",
                    ]
                    available_detail_cols = [c for c in detail_cols if c in detailed_queue.columns]
                    detail_view = detailed_queue[available_detail_cols].copy()
                    display_names = {
                        "symbol": "심볼", "name": "이름", "queue_priority": "검토 우선순위",
                        "next_action_ko": "다음 검토 작업",
                        "market": "현재 시장", "sector": "현재 업종",
                        "proposed_market": "제안 시장", "proposed_sector": "제안 업종",
                        "market_benchmark": "현재 시장 벤치마크",
                        "sector_benchmark": "현재 업종 벤치마크",
                        "proposed_market_benchmark": "제안 시장 벤치마크",
                        "proposed_sector_benchmark": "제안 업종 벤치마크",
                        "suggested_sector_benchmark_coverage_status": "제안 벤치마크 데이터 상태",
                        "candidate_price_rows": "후보 일봉 수",
                        "candidate_history_150_plus_bars": "150개 이상 일봉",
                        "candidate_latest_price_date": "후보 최근 일자",
                        "market_cap_size_screen": "시총 10억 달러 필터",
                        "issuer_country": "발행사 국가",
                        "listing_market": "상장 시장", "security_type": "증권 유형",
                        "official_source_type": "공식 자료 유형", "official_source_url": "공식 자료",
                        "source_observed_date": "근거 확인일", "review_outcome": "근거 검토 결과",
                        "remaining_gates": "남은 검토 조건",
                        "activation_recommendation": "편입 권고 상태",
                    }
                    detail_view = detail_view.rename(columns=display_names)
                    st.dataframe(
                        detail_view.head(200),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "공식 자료": st.column_config.LinkColumn(
                                "공식 자료", display_text="출처 열기"
                            )
                        },
                    )
                    st.caption(f"상세 검토 대기열 {len(detail_view):,}개 중 최대 200개 표시")
                    st.download_button(
                        "상세 검토 대기열 CSV 다운로드",
                        detailed_queue.to_csv(index=False).encode("utf-8-sig"),
                        file_name="candidate_review_queue.csv",
                        mime="text/csv",
                        key="detailed_candidate_review_queue_download",
                    )
                except Exception as exc:
                    st.warning(f"상세 검토 대기열을 표시하지 못했습니다. ({type(exc).__name__})")

            # Candidate discovery can stop early when KIS repeats a ranking page.
            # Surface this explicitly so the candidate list is not mistaken for a complete market universe.
            discovery_status_path = Path("data/candidate_collection_status.json")
            if discovery_status_path.exists():
                try:
                    discovery_status = json.loads(discovery_status_path.read_text(encoding="utf-8"))
                    stalled_pages = discovery_status.get("ranking_pagination_stalled", {})
                    fetched_pages = discovery_status.get("ranking_pages_fetched", {})
                    stalled_markets = [market for market, stalled in stalled_pages.items() if stalled]
                    if stalled_markets:
                        details = ", ".join(
                            f"{market}: {fetched_pages.get(market, 0)}페이지" for market in stalled_markets
                        )
                        st.warning(
                            "후보 수집 범위 주의: KIS 시가총액 순위가 반복 페이지를 반환해 일부 시장의 페이지 탐색이 중단됐습니다 "
                            f"({details}). 현재 후보 목록을 전체 시장 유니버스로 간주하지 말고, 미등재 종목의 시가총액은 미확인으로 유지하세요."
                        )
                except (OSError, ValueError, TypeError):
                    st.caption("후보 수집 페이지 상태를 읽지 못했습니다. 후보 목록의 시장 전체 커버리지는 별도 확인이 필요합니다.")

            reconciliation_path = Path("data/yahoo_market_cap_reconciliation.csv")
            if reconciliation_path.exists():
                cap_review = pd.read_csv(reconciliation_path).fillna("")
                st.caption("Yahoo Finance 보조 시가총액 대조 · 검증 완료 자료가 아님")
                if not cap_review.empty and "comparison_status" in cap_review.columns:
                    cap_counts = cap_review["comparison_status"].value_counts()
                    st.dataframe(
                        cap_counts.rename_axis("대조 결과").reset_index(name="종목 수"),
                        use_container_width=True,
                        hide_index=True,
                    )
                    cap_columns = [
                        "symbol", "candidate_cap_usd_b", "yahoo_cap_usd_b",
                        "difference_pct_vs_candidate", "comparison_status", "triage_note_ko",
                    ]
                    display_cap_review = cap_review[[c for c in cap_columns if c in cap_review.columns]]
                    st.dataframe(display_cap_review.head(50), use_container_width=True, hide_index=True)
                    st.download_button(
                        "시가총액 대조 CSV 다운로드",
                        cap_review.to_csv(index=False).encode("utf-8-sig"),
                        file_name="yahoo_market_cap_reconciliation.csv",
                        mime="text/csv",
                        key="candidate_cap_reconciliation_download",
                    )
                else:
                    st.info("아직 비교 가능한 시가총액 대조 행이 없습니다.")
            else:
                st.info("Yahoo Finance 시가총액 대조 보고서는 첫 후보 수집 실행이 완료된 뒤 생성됩니다.")
            coverage_path = Path("data/stock_candidate_coverage_report.csv")
            if coverage_path.exists():
                candidate_coverage = pd.read_csv(coverage_path).fillna("")
                st.caption("후보별 가격·벤치마크·검토 차단 요인")
                coverage_columns = [
                    "symbol", "name", "market", "sector",
                    "proposed_sector", "sector_benchmark", "proposed_sector_benchmark",
                    "candidate_price_rows", "candidate_latest_price_date",
                    "candidate_history_150_plus_bars", "refresh_attempt_outcome",
                    "review_priority", "review_blockers", "review_blockers_ko",
                    "suggested_sector_benchmark_coverage_status",
                    "snapshot_coverage_status",
                ]
                available_coverage_columns = [c for c in coverage_columns if c in candidate_coverage.columns]
                if available_coverage_columns:
                    st.dataframe(
                        candidate_coverage[available_coverage_columns].head(100),
                        use_container_width=True,
                        hide_index=True,
                    )
                st.download_button(
                    "후보별 데이터 커버리지 CSV 다운로드",
                    candidate_coverage.to_csv(index=False).encode("utf-8-sig"),
                    file_name="stock_candidate_coverage_report.csv",
                    mime="text/csv",
                    key="candidate_coverage_download",
                )
        except Exception as exc:
            st.warning(f"종목 편입 검토 자료를 표시하지 못했습니다. 기존 Stage 분석은 계속 이용할 수 있습니다. ({type(exc).__name__})")
    else:
        st.info("종목 후보 검토 자료가 아직 생성되지 않았습니다.")

with st.expander("시장 전체 요약"):
    a, b, c, d, e, f, g = st.columns(7)
    a.metric("표시 자산", len(screen))
    b.metric("Stage 2 후보", int(screen["stage_label"].eq("Stage 2 후보").sum()))
    c.metric("Stage 2A 관찰", int(screen["stage_label"].eq("Stage 2A 관찰 후보").sum()))
    d.metric("종목 데이터 오래됨 · 보류", int(screen["data_stale"].sum()))
    e.metric("기준 데이터 오래됨 · 보류", int(screen["benchmark_data_stale"].sum()))
    f.metric("벤치마크 부족 · 보류", int(screen["benchmark_data_missing"].sum()))
    g.metric("데이터 기준일", str(pd.to_datetime(screen["last_date"]).max().date()) if len(screen) else "N/A")

with st.expander("CSV 형식 및 판정 로직"):
    st.write("가격 CSV 열: date, symbol, open, high, low, close, volume")
    st.write("유니버스 CSV 열: symbol, name, market, sector, asset_type, market_cap_usd, market_benchmark, sector_benchmark")
    st.write("asset_type 값: stock, market_etf, sector_etf, commodity_etf, commodity")
    st.write("벤치마크 심볼도 가격 CSV에 포함해야 시장 및 업종 대비 상대강도를 계산할 수 있습니다.")
    st.write("Stage 2 후보: 종가가 30주선 위, 30주선의 4주 기울기 양수, 시장 및 업종 대비 26주 상대수익률 양수.")
    st.write("Stage 2A 관찰 후보는 초기 스크리닝을 위한 내부 분류명이며 와인스타인의 공식 단계 명칭이 아닙니다.")
    st.write("이 로직은 초기 규칙이며, 수익성 검증 또는 투자 권고가 아닙니다.")

st.download_button("현재 스크리닝 CSV 다운로드",screen.to_csv(index=False).encode("utf-8-sig"),file_name="stage_screen.csv",mime="text/csv")
