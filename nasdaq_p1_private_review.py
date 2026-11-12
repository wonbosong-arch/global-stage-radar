"""Read-only local P1 charts and in-memory candidate intake proposals."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path

import pandas as pd

from collect_stock_candidates import merge_candidate_discoveries
from market_data import PRICE_COLUMNS, filter_incomplete_daily_bars
from nasdaq_gap_price_readiness import P1, price_inventory
from nasdaq_p1_private_bundle import digest, unseal
from nasdaq_p1_kis_history_probe import MATCHED_SEC_VENUE, US_VENUES
from nasdaq_single_source import private_path, proxy_for
from stage_engine import weekly_bars

PASS = "saved_history_thresholds_met_review_only"
AUTH = "p1_private_auth"


def load_bundle(path, key_path, expected_code_sha):
    if len(expected_code_sha) != 40:
        raise ValueError("Require the trusted workflow run's full code SHA")
    payload = unseal(private_path(Path(path)).read_bytes(),
                     private_path(Path(key_path)).read_bytes())
    if (payload["schema_version"] != 1 or payload["code_sha"] != expected_code_sha
            or payload["observations_sha256"] != digest(payload["observations"])):
        raise ValueError("Bundle provenance mismatch")
    return payload


def prepare_review(payload, candidates, active, now):
    """Recheck retained histories, preserve identity holds, propose pending rows only.

    Returned candidate registry is a copy. No file writes or provider calls.
    Saved observations remain historical facts; current freshness is recomputed.
    """
    observations = payload["observations"]
    if not 1 <= len(observations) <= 16:
        raise ValueError("Unexpected capture cohort")
    if payload["observations_sha256"] != digest(observations):
        raise ValueError("Capture hash mismatch")
    seen, price_frames, rows, proposed = set(), [], [], []
    captured_at = datetime.fromisoformat(payload["evaluated_at"])
    if captured_at.utcoffset() is None or captured_at > now:
        raise ValueError("Invalid capture timestamp")
    for observation in observations:
        symbol, venue = observation["symbol"], observation["venue"]
        identity, sec = observation["identity"], observation["sec_reference"]
        if (symbol in seen or venue not in US_VENUES
                or observation["activation_approved"] is not False
                or identity["symbol"] != symbol or sec["symbol"] != symbol
                or identity["issuer_identity_review_cohort"] != P1
                or identity["kis_venues_by_ticker"] != [venue]
                or identity["sec_reference_status"] != MATCHED_SEC_VENUE
                or sec["kis_venue"] != venue
                or sec["activation_status"] != "pending_review"
                or sec["evidence_status"] != "sec_filing_security_and_symbol_checked"
                or not any(word in sec["security_class"].lower() for word in ("common", "ordinary"))
                or observation["prices_sha256"] != digest(observation["prices"])):
            raise ValueError("Capture identity or price linkage mismatch")
        seen.add(symbol)
        bars = pd.DataFrame(observation["prices"], columns=PRICE_COLUMNS)
        if not bars.empty and set(bars.symbol) != {symbol}:
            raise ValueError("Capture symbol mismatch")
        gap = {"source_sha256": payload["summary"]["source_sha256"], "review_rows": [identity]}
        historical = price_inventory(gap, bars, captured_at)["review_rows"][0]
        current = price_inventory(gap, bars, now)["review_rows"][0]
        # Empty/error responses carry no price-based status to reconcile.
        if not bars.empty and historical["price_inventory_status"] != observation["status"]:
            raise ValueError("Historical status does not match retained prices")
        proxy, proxy_status = proxy_for({"Sector": identity["nasdaq_sector"],
                                         "Industry": identity["nasdaq_industry"]})
        note = sec["review_note"]
        ready = current["price_inventory_status"] == PASS and not note
        rows.append({"symbol": symbol, "exchange": venue, "name": identity["source_name"],
                     "captured_status": observation["status"],
                     "current_status": current["price_inventory_status"],
                     "daily_rows": current["completed_daily_rows"],
                     "completed_weeks": current["completed_weeks"],
                     "security_class": sec["security_class"], "identity_hold": note,
                     "sector_proxy_status": proxy_status,
                     "intake_proposable": ready, "activation_approved": False})
        if not bars.empty and current["saved_ohlcv_quality_pass"]:
            bars["date"] = pd.to_datetime(bars.date)
            for column in ("open", "high", "low", "close", "volume"):
                bars[column] = pd.to_numeric(bars[column])
            price_frames.append(filter_incomplete_daily_bars(bars, {symbol: venue}, now))
        if ready:
            proposed.append({"symbol": symbol, "name": identity["source_name"],
                "exchange": venue, "market": "United States", "country": "United States",
                "currency": "USD", "asset_type": "stock", "market_benchmark": "SPY",
                "sector": "", "sector_benchmark": "",
                "instrument_type": "common_stock_candidate_unverified",
                "identity_status": "review_required", "market_cap_status": "not_verified",
                "provider_status": "kis_history_captured_review_only",
                "activation_status": "pending_review", "identity_evidence_url": sec["source_url"],
                "discovery_source": "approved_nasdaq_csv",
                "discovery_market_cap_usd": identity["nasdaq_reported_cap_usd"],
                "discovery_cap_threshold_pass": "nasdaq_csv_size_screen",
                "proposed_sector": proxy[0] if proxy else "",
                "proposed_sector_benchmark": proxy[1] if proxy else "",
                "review_note": "Approved Nasdaq size screen; retained KIS history; pending intake approval. "
                               "Sector proxy is a suggestion, not an approved benchmark."})
    registry, added = merge_candidate_discoveries(candidates.copy(deep=True),
                                                 pd.DataFrame(proposed), active.copy(deep=True))
    prices = pd.concat(price_frames, ignore_index=True) if price_frames else pd.DataFrame(columns=PRICE_COLUMNS)
    return {"rows": pd.DataFrame(rows), "prices": prices,
            "candidate_proposal": registry, "proposed_additions": added}


def render_private_charts(st, env, get_secret, make_chart):
    """Disabled unless local opt-in, private paths and existing app password exist."""
    if env.get("NASDAQ_P1_PRIVATE_CONTEXT") != "local_private":
        st.session_state.pop(AUTH, None)
        return
    context = tuple(env.get(k, "") for k in (
        "NASDAQ_P1_BUNDLE", "NASDAQ_P1_PRIVATE_KEY", "NASDAQ_P1_CODE_SHA"))
    password = str(get_secret("APP_PASSWORD") or "")
    tag = hashlib.sha256(json.dumps((password, context)).encode()).hexdigest()
    with st.expander("미국 P1 · 비공개 가격 이력 검토"):
        if not password or not all(context):
            st.session_state.pop(AUTH, None)
            st.info("비공개 자료와 기존 앱 비밀번호를 설정해야 합니다.")
            return
        if st.session_state.get(AUTH) != tag:
            with st.form("p1_private_login"):
                entered = st.text_input("검토 비밀번호", type="password")
                submitted = st.form_submit_button("가격 이력 열기")
            if submitted and hmac.compare_digest(entered.encode(), password.encode()):
                st.session_state[AUTH] = tag
                st.rerun()
            return
        if st.button("가격 이력 잠그기", key="p1_private_lock"):
            st.session_state.pop(AUTH, None)
            st.rerun()
        try:
            payload = load_bundle(*context)
            root = Path(__file__).resolve().parent / "data"
            prepared = prepare_review(payload,
                pd.read_csv(root / "stock_universe_candidates.csv", dtype=str).fillna(""),
                pd.read_csv(root / "monitoring_universe.csv", dtype=str).fillna(""),
                datetime.now(timezone.utc))
        except Exception:
            st.warning("비공개 자료의 무결성 또는 기준시점 확인에 실패했습니다.")
            return
        st.caption(f"후보 등록 제안 {prepared['proposed_additions']}개 · 운영 편입 0개")
        st.dataframe(prepared["rows"], hide_index=True)
        available = sorted(prepared["prices"].symbol.unique())
        if not available:
            return
        selected = st.selectbox("P1 검토 종목", available, key="p1_private_symbol")
        period = st.radio("P1 차트 주기", ["일봉", "주봉"], horizontal=True, key="p1_private_period")
        detail = prepared["rows"].set_index("symbol").loc[selected]
        if detail.current_status != PASS or detail.identity_hold:
            st.warning(f"검토 보류: {detail.current_status} {detail.identity_hold}")
        daily = prepared["prices"].loc[prepared["prices"].symbol.eq(selected)].copy()
        weekly = weekly_bars(daily, calendar_name="XNYS", min_bars=1)
        figure = make_chart(selected, period_is_weekly=period == "주봉", chart_period=period,
                            daily_data=daily, weekly_data={selected: weekly})
        if figure is not None:
            st.plotly_chart(figure, key="p1_private_chart", use_container_width=True)
