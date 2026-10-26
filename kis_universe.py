"""KIS market-cap ranking discovery. Results remain candidates until units and metadata are verified."""
from __future__ import annotations
from typing import Optional

import time
from io import BytesIO
import zipfile
import pandas as pd
import requests
from kis_provider import KISError


def _request_ranking(client, path, tr_id, params, continuation=False):
    """Call KIS ranking endpoints with bounded retry and optional next-page header."""
    headers = {
        "authorization": f"Bearer {client._get_token()}",
        "appkey": client.app_key,
        "appsecret": client.app_secret,
        "tr_id": tr_id,
        "custtype": "P",
    }
    if continuation:
        headers["tr_cont"] = "N"
    last_error = None
    for attempt in range(4):
        elapsed = time.monotonic() - client._last_request_at
        if client._last_request_at and elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        try:
            response = client.session.get(
                client.base_url + path, headers=headers, params=params, timeout=client.timeout
            )
        except requests.RequestException as exc:
            client._last_request_at = time.monotonic()
            last_error = KISError(f"KIS ranking network request failed: {type(exc).__name__}")
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise last_error from exc
        client._last_request_at = time.monotonic()
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        code = str(payload.get("msg_cd", ""))
        if response.ok and str(payload.get("rt_cd", "")) == "0":
            return payload, str(getattr(response, "headers", {}).get("tr_cont", ""))
        message = str(payload.get("msg1", response.text[:250]))
        last_error = KISError(f"KIS market-cap ranking failed: {message} ({code or response.status_code})")
        # KIS can report rate limits as HTTP 500.
        # Do not retry deterministic KIS parameter/validation errors merely because
        # KIS reports them as HTTP 500. Retry known rate limits, or unclassified
        # transient HTTP failures that have no KIS application error code.
        retryable_http = response.status_code in {429, 500, 502, 503, 504}
        if code == "EGW00201" or (retryable_http and not code):
            if attempt < 3:
                time.sleep(1.5 * (2 ** attempt))
                continue
        raise last_error
    raise last_error or KISError("KIS market-cap ranking failed after retries.")


def fetch_us_market_cap_candidates(client, exchange="NAS", max_pages=50):
    """Fetch up to max_pages (50 by default) of KIS US market-cap ranking; cap units remain unverified."""
    exchange = str(exchange).strip().upper()
    if exchange not in {"NAS", "NYS", "AMS"}:
        raise ValueError("US exchange must be NAS, NYS, or AMS.")
    params = {"EXCD": exchange, "VOL_RANG": "0", "KEYB": "", "AUTH": ""}
    all_rows = []
    seen_symbols = set()
    continuation = False
    page_limit = max(1, min(int(max_pages), 50))
    pages_fetched = 0
    limit_reached = False
    pagination_stalled = False
    for page_index in range(page_limit):
        payload, next_page = _request_ranking(
            client,
            "/uapi/overseas-stock/v1/ranking/market-cap",
            "HHDFS76350100",
            params,
            continuation=continuation,
        )
        pages_fetched += 1
        page_rows = payload.get("output2") or []
        page_symbols = {
            str(row.get("symb", "")).strip().upper()
            for row in page_rows
            if str(row.get("symb", "")).strip()
        }
        new_symbols = page_symbols - seen_symbols
        all_rows.extend(page_rows)
        if page_index > 0 and not new_symbols:
            # Some KIS responses keep advertising continuation while returning the
            # same ranking page. Stop rather than spending 50 rate-limited requests.
            pagination_stalled = True
            break
        seen_symbols.update(page_symbols)
        if next_page not in {"M", "F"}:
            break
        continuation = True
        if page_index == page_limit - 1:
            limit_reached = True
    frame = pd.DataFrame(all_rows)
    frame.attrs["ranking_pages_fetched"] = pages_fetched
    frame.attrs["ranking_page_limit_reached"] = limit_reached
    frame.attrs["ranking_pagination_stalled"] = pagination_stalled
    if frame.empty:
        return frame
    if "symb" in frame.columns:
        frame = frame.drop_duplicates(subset=["symb"], keep="first")
    frame["listing_exchange"] = exchange
    frame["market_cap_units_verified"] = False
    return frame

def fetch_korea_market_cap_candidates(client, market="0000", max_pages=10):
    """Fetch up to max_pages (10 by default) of KIS KRX market-cap ranking; raw cap values are unverified."""
    market = str(market).strip()
    if market not in {"0000", "0001", "1001", "2001"}:
        raise ValueError("market must be 0000(all), 0001(exchange), 1001(KOSDAQ), or 2001(KOSPI200).")
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_cond_scr_div_code": "20174",
        "fid_div_cls_code": "1",
        "fid_input_iscd": market,
        "fid_trgt_cls_code": "0",
        "fid_trgt_exls_cls_code": "0",
        "fid_input_price_1": "",
        "fid_input_price_2": "",
        "fid_vol_cnt": "",
    }
    all_rows = []
    seen_symbols = set()
    continuation = False
    page_limit = max(1, min(int(max_pages), 10))
    pages_fetched = 0
    limit_reached = False
    pagination_stalled = False
    for page_index in range(page_limit):
        payload, next_page = _request_ranking(
            client,
            "/uapi/domestic-stock/v1/ranking/market-cap",
            "FHPST01740000",
            params,
            continuation=continuation,
        )
        pages_fetched += 1
        page_rows = payload.get("output") or []
        page_symbols = {
            str(row.get("mksc_shrn_iscd", "")).strip().zfill(6)
            for row in page_rows
            if str(row.get("mksc_shrn_iscd", "")).strip()
        }
        new_symbols = page_symbols - seen_symbols
        all_rows.extend(page_rows)
        if page_index > 0 and not new_symbols:
            pagination_stalled = True
            break
        seen_symbols.update(page_symbols)
        if next_page != "M":
            break
        continuation = True
        if page_index == page_limit - 1:
            limit_reached = True
    frame = pd.DataFrame(all_rows)
    frame.attrs["ranking_pages_fetched"] = pages_fetched
    frame.attrs["ranking_page_limit_reached"] = limit_reached
    frame.attrs["ranking_pagination_stalled"] = pagination_stalled
    if frame.empty:
        return frame
    if "mksc_shrn_iscd" in frame.columns:
        frame = frame.drop_duplicates(subset=["mksc_shrn_iscd"], keep="first")
    frame["listing_exchange"] = "KRX"
    frame["ranking_market_code"] = market
    frame["market_cap_units_verified"] = False
    return frame


_US_MASTER_COLUMNS = [
    "national_code", "exchange_id", "exchange_code", "exchange_name", "symbol",
    "realtime_symbol", "korean_name", "english_name", "security_type", "currency",
    "float_position", "data_type", "base_price", "bid_order_size", "ask_order_size",
    "market_start_time", "market_end_time", "dr_flag", "dr_country_code",
    "industry_code", "index_membership_flag", "tick_size_type", "product_type_code",
    "tick_size_detail",
]


def parse_us_security_master_zip(content: bytes, exchange: str) -> pd.DataFrame:
    """Parse an official KIS US market master ZIP into a compact symbol/type table."""
    exchange = str(exchange).strip().upper()
    codes = {"NAS": "nas", "NYS": "nys", "AMS": "ams"}
    if exchange not in codes:
        raise ValueError("US exchange must be NAS, NYS, or AMS.")
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".cod")]
            if not members:
                raise ValueError("ZIP contains no .cod master file.")
            with archive.open(members[0]) as source:
                raw = pd.read_csv(
                    source, sep="\t", header=None, dtype=str,
                    encoding="cp949", keep_default_na=False, engine="python",
                )
    except (zipfile.BadZipFile, pd.errors.ParserError, UnicodeError) as exc:
        raise KISError(f"KIS {exchange} security master could not be parsed.") from exc
    if raw.shape[1] != len(_US_MASTER_COLUMNS):
        raise KISError(
            f"KIS {exchange} security master schema changed: expected "
            f"{len(_US_MASTER_COLUMNS)} columns, received {raw.shape[1]}."
        )
    raw.columns = _US_MASTER_COLUMNS
    result = raw[[
        "symbol", "english_name", "korean_name", "security_type", "currency",
        "dr_flag", "dr_country_code", "industry_code",
    ]].copy()
    result["symbol"] = result["symbol"].astype(str).str.strip().str.upper()
    result["listing_exchange"] = exchange
    result["master_security_type"] = result["security_type"].astype(str).str.strip()
    result["master_dr_flag"] = result["dr_flag"].astype(str).str.strip()
    result["master_dr_country_code"] = result["dr_country_code"].astype(str).str.strip()
    # Preserve the source code as evidence only; no sector mapping is inferred here.
    result["master_industry_code"] = result["industry_code"].astype(str).str.strip()
    result = result[result["symbol"].ne("")]
    return result.drop_duplicates(["listing_exchange", "symbol"], keep="first").reset_index(drop=True)



def audit_us_master_ranking_coverage(
    security_master: pd.DataFrame,
    ranking_candidates: pd.DataFrame,
    exchanges=("NAS", "NYS", "AMS"),
) -> pd.DataFrame:
    """Compare KIS US symbol masters with ranking results; absence is not a cap-screen result."""
    master = security_master.copy() if security_master is not None else pd.DataFrame()
    rankings = ranking_candidates.copy() if ranking_candidates is not None else pd.DataFrame()
    rows = []
    for exchange in exchanges:
        exchange = str(exchange).strip().upper()
        if master.empty or not {"listing_exchange", "symbol"}.issubset(master.columns):
            master_symbols = set()
        else:
            selected = master.loc[
                master["listing_exchange"].astype(str).str.upper().eq(exchange), "symbol"
            ]
            master_symbols = set(selected.astype(str).str.strip().str.upper()) - {""}
        if rankings.empty or not {"listing_exchange", "symb"}.issubset(rankings.columns):
            ranking_symbols = set()
        else:
            selected = rankings.loc[
                rankings["listing_exchange"].astype(str).str.upper().eq(exchange), "symb"
            ]
            ranking_symbols = set(selected.astype(str).str.strip().str.upper()) - {""}
        rows.append({
            "exchange": exchange,
            "master_symbol_count": len(master_symbols),
            "ranking_symbol_count": len(ranking_symbols),
            "ranking_symbols_matched_to_master": len(ranking_symbols & master_symbols),
            "ranking_symbols_not_in_master": len(ranking_symbols - master_symbols),
            "master_symbols_not_in_ranking": len(master_symbols - ranking_symbols),
            "ranking_symbols_matched_to_master_pct": (
                round(100.0 * len(ranking_symbols & master_symbols) / len(ranking_symbols), 1)
                if ranking_symbols else None
            ),
            "master_symbols_returned_by_ranking_pct": (
                round(100.0 * len(ranking_symbols & master_symbols) / len(master_symbols), 1)
                if master_symbols else None
            ),
            "coverage_interpretation": (
                "master symbols absent from ranking; market cap/eligibility unknown"
            ),
        })
    return pd.DataFrame(rows)



def build_unranked_us_stock_master(security_master, ranking_candidates):
    """List stock-type master symbols absent from ranking; market cap remains unknown."""
    columns = [
        "listing_exchange", "symbol", "english_name", "korean_name",
        "master_security_type", "master_dr_flag", "master_dr_country_code",
        "market_cap_usd", "cap_threshold_pass", "review_status",
    ]
    if security_master is None or security_master.empty:
        return pd.DataFrame(columns=columns)
    master = security_master.copy()
    for column in columns[:7]:
        if column not in master.columns:
            master[column] = ""
    master["listing_exchange"] = master["listing_exchange"].astype(str).str.upper().str.strip()
    master["symbol"] = master["symbol"].astype(str).str.upper().str.strip()
    master["master_security_type"] = master["master_security_type"].astype(str).str.strip()
    master = master[master["master_security_type"].eq("2") & master["symbol"].ne("")].copy()
    ranked = set()
    if ranking_candidates is not None and not ranking_candidates.empty:
        if {"listing_exchange", "symb"}.issubset(ranking_candidates.columns):
            ranked = set(zip(
                ranking_candidates["listing_exchange"].astype(str).str.upper().str.strip(),
                ranking_candidates["symb"].astype(str).str.upper().str.strip(),
            ))
    keep = [
        (row.listing_exchange, row.symbol) not in ranked
        for row in master[["listing_exchange", "symbol"]].itertuples(index=False)
    ]
    master = master.loc[keep].copy()
    master["market_cap_usd"] = float("nan")
    master["cap_threshold_pass"] = pd.NA
    master["review_status"] = "unranked_master_symbol_cap_unknown"
    return master[columns].drop_duplicates(
        ["listing_exchange", "symbol"], keep="first"
    ).sort_values(["listing_exchange", "symbol"]).reset_index(drop=True)


def fetch_us_security_master(exchanges=("NAS", "NYS", "AMS"), timeout: float = 20.0) -> pd.DataFrame:
    """Download KIS public US symbol masters; security_type 2=stock, 3=ETP, 4=warrant."""
    frames = []
    codes = {"NAS": "nas", "NYS": "nys", "AMS": "ams"}
    for exchange in exchanges:
        exchange = str(exchange).strip().upper()
        if exchange not in codes:
            raise ValueError("US exchange must be NAS, NYS, or AMS.")
        url = f"https://new.real.download.dws.co.kr/common/master/{codes[exchange]}mst.cod.zip"
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise KISError(f"KIS {exchange} security master download failed: {type(exc).__name__}.") from exc
        frames.append(parse_us_security_master_zip(response.content, exchange))
    if not frames:
        return pd.DataFrame(columns=[
            "symbol", "english_name", "korean_name", "security_type", "currency",
            "listing_exchange", "master_security_type", "master_dr_flag",
            "master_dr_country_code", "master_industry_code",
        ])
    return pd.concat(frames, ignore_index=True).drop_duplicates(
        ["listing_exchange", "symbol"], keep="first"
    ).reset_index(drop=True)


def normalize_market_cap_candidates(raw: pd.DataFrame, min_cap_usd: float = 1_000_000_000,
                                    usdkrw: Optional[float] = None) -> pd.DataFrame:
    """Normalize raw KIS ranking rows for review; never silently approve stock type.

    US tomv is treated as USD market value based on price × shares consistency.
    KRX stck_avls is treated as 100-million-KRW units based on price × listed-share
    count consistency. USD conversion for KRX is only done when a positive USD/KRW
    rate is explicitly supplied. Instrument-name matching is a conservative flag,
    not a definitive security master.
    """
    if min_cap_usd < 0:
        raise ValueError("min_cap_usd must be non-negative.")
    if usdkrw is not None and usdkrw <= 0:
        raise ValueError("usdkrw must be positive when supplied.")
    if raw is None or raw.empty:
        return pd.DataFrame(columns=[
            "symbol", "name", "exchange", "currency", "market_cap_native",
            "market_cap_usd", "instrument_type_guess", "master_instrument_type",
            "master_security_type_code", "is_adr_candidate", "master_dr_flag",
            "master_dr_country_code", "stock_eligible", "cap_threshold_pass",
            "review_status", "review_reason"
        ])

    frame = raw.copy()
    for col in ("listing_exchange", "symb", "ename", "name", "mksc_shrn_iscd",
                "hts_kor_isnm", "tomv", "stck_avls", "lstn_stcn", "stck_prpr", "last", "shar", "master_security_type", "master_dr_flag", "master_dr_country_code", "master_industry_code"):
        if col not in frame:
            frame[col] = ""

    exchange = frame["listing_exchange"].astype(str).str.upper().str.strip()
    is_korea = exchange.eq("KRX")
    us_symbol = frame["symb"].astype(str).str.strip()
    kr_symbol = frame["mksc_shrn_iscd"].astype(str).str.strip()
    symbol = us_symbol.where(~is_korea, kr_symbol)
    us_name = frame["ename"].astype(str).str.strip()
    kr_name = frame["hts_kor_isnm"].astype(str).str.strip()
    name = us_name.where(~is_korea, kr_name)
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
    # Only use US tomv when it agrees with last × listed shares.
    us_cap = us_cap_raw.where(us_unit_verified)
    # Verify the domestic market-cap unit against price × listed shares.
    # If the implied ratio is not close to 1e8, do not use the cap for screening.
    kr_cap_raw = pd.to_numeric(frame["stck_avls"], errors="coerce")
    kr_price = pd.to_numeric(frame["stck_prpr"], errors="coerce")
    kr_shares = pd.to_numeric(frame["lstn_stcn"], errors="coerce")
    calculated_kr_cap = kr_price * kr_shares
    unit_ratio = calculated_kr_cap / kr_cap_raw.where(kr_cap_raw.ne(0))
    kr_unit_verified = (
        unit_ratio.between(80_000_000, 120_000_000)
        & calculated_kr_cap.notna()
        & kr_cap_raw.gt(0)
    )
    kr_cap_native = (kr_cap_raw * 100_000_000).where(kr_unit_verified)
    native_cap = us_cap.where(~is_korea, kr_cap_native)
    currency = pd.Series("USD", index=frame.index).where(~is_korea, "KRW")
    cap_usd = us_cap.where(~is_korea, float("nan"))
    if usdkrw is not None:
        cap_usd = cap_usd.where(~is_korea, native_cap / float(usdkrw))

    searchable_name = (
        name.fillna("").astype(str) + " " +
        frame["ename"].fillna("").astype(str) + " " +
        frame["name"].fillna("").astype(str)
    ).str.upper()
    fund_pattern = r"\b(?:ETF|ETN|TRUST|FUND|INDEX FUNDS|ISHARES|VANGUARD|SPDR|EXCHANGE TRADED|EXCHANGE-TRADED)\b"
    non_common_pattern = r"\b(?:CNV PREF|CONV(?:ERTIBLE)? PREF|PREFERRED|PREF SEC|GLOBAL NOTES|NOTES DUE|DEBENTURE|WARRANTS?|RIGHTS)\b"
    master_type = frame["master_security_type"].astype(str).str.strip()
    master_is_stock = master_type.eq("2")
    master_is_index = master_type.eq("1")
    master_is_etp = master_type.eq("3")
    master_is_warrant = master_type.eq("4")
    master_dr_flag = frame["master_dr_flag"].astype(str).str.strip().str.upper()
    master_dr_country_code = frame["master_dr_country_code"].astype(str).str.strip().str.upper()
    name_looks_adr = searchable_name.str.contains(
        r"\b(?:ADR|ADS|AMERICAN DEPOSITARY|DEPOSITARY RECEIPT|SPONSORED ADR|UNSPONSORED ADR)\b",
        regex=True, na=False,
    )
    master_marks_adr = master_dr_flag.isin({"1", "Y", "YES", "TRUE", "T"}) | (
        master_dr_country_code.ne("") & ~master_dr_country_code.isin({"US", "USA", "00", "0"})
    )
    is_adr = name_looks_adr | master_marks_adr
    # A matching price × share-count check is insufficient for an ADR unless
    # the depositary ratio is known; no ratio field is currently sourced.
    native_cap = native_cap.where(~is_adr)
    cap_usd = cap_usd.where(~is_adr)
    master_non_stock = master_type.isin({"1", "3", "4"})
    likely_fund = searchable_name.str.contains(fund_pattern, regex=True, na=False) | master_is_etp
    likely_non_common = searchable_name.str.contains(non_common_pattern, regex=True, na=False) | master_is_warrant
    # The KIS master type is authoritative for stock-vs-ETP/index/warrant; common-equity status still needs review.
    type_guess = pd.Series("equity_candidate_unverified", index=frame.index)
    type_guess = type_guess.where(~likely_fund & ~likely_non_common, "fund_or_etf_likely")
    type_guess = type_guess.where(~(likely_non_common & ~likely_fund), "non_common_security_likely")
    type_guess = type_guess.where(~master_is_index, "index_security_master")
    type_guess = type_guess.where(~is_adr, "adr_candidate_unverified")
    eligible = pd.Series("review_required", index=frame.index)
    eligible = eligible.where(
        ~likely_fund & ~likely_non_common & ~master_is_index,
        "exclude_from_stock_universe_pending_confirmation",
    )

    master_instrument_type = master_type.map({
        "1": "index", "2": "stock", "3": "etp", "4": "warrant"
    }).fillna("unmatched_or_unknown")
    # Market-cap screening is only for stock candidates, never ETFs, indices, or warrants.
    cap_pass = cap_usd.ge(float(min_cap_usd)).where(
        cap_usd.notna() & master_is_stock & ~likely_fund & ~likely_non_common & ~master_is_index, pd.NA
    )
    reasons = []
    statuses = []
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
        if is_korea.loc[idx] and pd.isna(native_cap.loc[idx]):
            why.append("krx_market_cap_unit_not_verified_against_price_times_shares")
        if not is_korea.loc[idx] and pd.isna(native_cap.loc[idx]):
            why.append(
                "adr_market_cap_requires_depositary_ratio_verification"
                if is_adr.loc[idx] else "us_market_cap_not_verified_against_price_times_shares"
            )
        if pd.isna(cap_usd.loc[idx]):
            why.append("usd_market_cap_unavailable")
        elif cap_usd.loc[idx] < min_cap_usd:
            why.append("below_minimum_market_cap")
        if is_korea.loc[idx] and usdkrw is None and not likely_fund.loc[idx] and not likely_non_common.loc[idx]:
            why.append("fx_rate_required_for_usd_threshold")
        reasons.append(";".join(why))
        statuses.append("exclude_candidate" if (likely_fund.loc[idx] or likely_non_common.loc[idx] or master_is_index.loc[idx]) else "manual_review")

    result = pd.DataFrame({
        "symbol": symbol,
        "name": name,
        "exchange": exchange,
        "currency": currency,
        "market_cap_native": native_cap,
        "market_cap_usd": cap_usd,
        "instrument_type_guess": type_guess,
        "master_instrument_type": master_instrument_type,
        "master_security_type_code": master_type,
        "is_adr_candidate": is_adr,
        "master_dr_flag": master_dr_flag,
        "master_dr_country_code": master_dr_country_code,
        "master_industry_code": frame["master_industry_code"].astype(str).str.strip(),
        "stock_eligible": eligible,
        "cap_threshold_pass": cap_pass,
        "review_status": statuses,
        "review_reason": reasons,
    })
    result["market_cap_native"] = pd.to_numeric(result["market_cap_native"], errors="coerce")
    result["market_cap_usd"] = pd.to_numeric(result["market_cap_usd"], errors="coerce")
    return result.reset_index(drop=True)
