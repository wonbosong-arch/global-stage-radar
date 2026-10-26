"""Discover KIS stock candidates without activating them."""
from __future__ import annotations
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import requests
from kis_provider import KISOverseasPrices
from kis_universe import (
    fetch_korea_market_cap_candidates, fetch_us_market_cap_candidates,
    fetch_us_security_master, normalize_market_cap_candidates,
)
from krx_master import download_krx_master

ROOT = Path(__file__).resolve().parent
CANDIDATES_PATH = ROOT / "data" / "stock_universe_candidates.csv"
UNIVERSE_PATH = ROOT / "data" / "monitoring_universe.csv"
STATUS_PATH = ROOT / "data" / "candidate_collection_status.json"
MIN_CAP_USD = 1_000_000_000
FX_REFERENCE_URL = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=KRW"


def resolve_usdkrw_rate(configured_rate: str = "", session=None) -> tuple[float | None, str, str | None]:
    """Use an explicit repository variable first, otherwise the latest ECB reference rate.

    FX is only used for broad USD 1B screening; if the public reference is unavailable
    or stale, leave Korean market caps unconverted and pending rather than guessing.
    """
    configured_rate = str(configured_rate or "").strip()
    if configured_rate:
        rate = float(configured_rate)
        if rate <= 0:
            raise ValueError("USD_KRW_RATE must be positive.")
        return rate, "GitHub repository variable USD_KRW_RATE", None
    requester = session or requests
    try:
        response = requester.get(FX_REFERENCE_URL, timeout=10)
        response.raise_for_status()
        payload = response.json()
        rate = float(payload["rates"]["KRW"])
        rate_date = str(payload["date"])
        parsed_date = datetime.strptime(rate_date, "%Y-%m-%d").date()
        age_days = (datetime.now(timezone.utc).date() - parsed_date).days
        if rate <= 0 or age_days < 0 or age_days > 7:
            return None, "unavailable_or_stale", rate_date
        return rate, "Frankfurter API (ECB reference rate)", rate_date
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None, "unavailable", None


def extract_adr_ratio_from_listing_name(name: str) -> tuple[str, str]:
    """Extract only an explicitly stated ordinary-share ratio from the listing label.

    This is weak provider-description evidence, never official verification. The ratio
    remains pending until checked against issuer/depositary documentation.
    """
    text = str(name or "").upper().replace(",", " ")
    patterns = (
        r"\bREP(?:RESENTS|R)?\s+(\d+(?:\.\d+)?)\s*(?:ORD(?:INARY)?\s+)?(?:SHS|SHARES)\b",
        r"\b(?:REP(?:RESENTS|R)?\s+)?(\d+(?:\.\d+)?)\s+ORD(?:INARY)?\b",
        r"\b(\d+(?:\.\d+)?)\s+(?:ORD(?:INARY)?\s+)?SHS\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                ratio = float(match.group(1))
            except ValueError:
                continue
            if ratio > 0:
                return str(ratio).rstrip("0").rstrip(".") if "." in str(ratio) else str(ratio), "ordinary_shares_per_depositary_share"
    return "", ""



def _bool_or_none(value):
    return None if value is None or pd.isna(value) else bool(value)


def build_discovered_candidate_rows(normalized: pd.DataFrame, discovered_at: str) -> pd.DataFrame:
    """Build pending-only rows. Exclude verified sub-$1B stocks and non-stock classes."""
    rows = []
    for _, item in normalized.iterrows():
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        security_class = str(item.get("master_instrument_type", "unmatched_or_unknown")).strip().lower()
        guess = str(item.get("instrument_type_guess", "")).strip().lower()
        eligibility = str(item.get("stock_eligible", "")).strip().lower()
        if security_class in {"index", "etp", "warrant"}:
            continue
        if guess in {"fund_or_etf_likely", "non_common_security_likely", "index_security_master"}:
            continue
        if eligibility == "exclude_from_stock_universe_pending_confirmation":
            continue
        cap_pass = _bool_or_none(item.get("cap_threshold_pass"))
        if cap_pass is False:
            continue
        exchange = str(item.get("exchange", "")).strip().upper()
        is_kr = exchange == "KRX"
        adr_value = item.get("is_adr_candidate", False)
        is_adr = False if pd.isna(adr_value) else bool(adr_value)
        name = str(item.get("name", "")).strip() or symbol
        adr_ratio_observed, adr_ratio_basis = extract_adr_ratio_from_listing_name(name) if is_adr else ("", "")
        cap_usd = pd.to_numeric(pd.Series([item.get("market_cap_usd")]), errors="coerce").iloc[0]
        cap_native = pd.to_numeric(pd.Series([item.get("market_cap_native")]), errors="coerce").iloc[0]
        reason = str(item.get("review_reason", "")).strip()
        cap_note = (
            f"KIS ranking implies USD market cap {cap_usd / 1_000_000_000:.2f}B"
            if pd.notna(cap_usd) else "USD market cap missing or unit unverified"
        )
        rows.append({
            "symbol": symbol, "name": name,
            "market": "South Korea" if is_kr else "United States",
            "sector": "", "asset_type": "stock",
            "market_benchmark": "EWY" if is_kr else "SPY", "sector_benchmark": "",
            "exchange": "KRX" if is_kr else exchange,
            "country": "Unknown" if not is_kr else "South Korea",
            "currency": "KRW" if is_kr else "USD",
            "instrument_type": "adr_candidate" if is_adr else (
                "common_stock_candidate_unverified" if is_kr else "equity_candidate_unverified"
            ),
            "identity_status": "issuer_proxy_review_required" if is_adr else "review_required",
            "market_cap_status": "not_verified", "provider_status": "not_checked",
            "activation_status": "pending_review",
            "review_note": (
                f"Discovered by KIS market-cap ranking on {discovered_at}. {cap_note}. "
                "Instrument identity, common-share/ADR status, sector and benchmark mapping, "
                "market-cap provenance, and current provider support require manual review. "
                f"Normalization notes: {reason or 'none'}"
            ),
            "identity_evidence_url": "", "identity_reviewed_at": "",
            "market_cap_source_url": "", "market_cap_asof": discovered_at,
            "depositary_ratio_status": "listing_description_only_pending_primary_source" if is_adr and adr_ratio_observed else ("not_verified" if is_adr else "not_applicable"),
            "depositary_ratio_observed": adr_ratio_observed,
            "depositary_ratio_basis": adr_ratio_basis,
            "depositary_ratio_evidence_text": name if is_adr and adr_ratio_observed else "",
            "market_cap_usd_b_secondary": pd.NA,
            "discovery_market_cap_usd": cap_usd,
            "discovery_market_cap_native": cap_native,
            "discovery_market_cap_currency": "KRW" if is_kr else "USD",
            "discovery_source": "KIS market-cap ranking",
            "discovered_at": discovered_at,
            "discovery_cap_threshold_pass": cap_pass,
            "discovery_security_type": security_class,
            "discovery_industry_code": str(item.get("master_industry_code", "") or "").strip(),
            "discovery_review_reason": reason,
        })
    return pd.DataFrame(rows).drop_duplicates("symbol", keep="first") if rows else pd.DataFrame()


def merge_candidate_discoveries(existing_candidates: pd.DataFrame, discovered_rows: pd.DataFrame,
                                active_universe: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Append only unseen symbols; never overwrite existing review decisions."""
    existing = existing_candidates.copy()
    discovered_evidence = discovered_rows.copy() if discovered_rows is not None else pd.DataFrame()
    # Backfill only a missing raw evidence field. Never overwrite reviewed metadata,
    # sector mappings, activation status, or other existing candidate decisions.
    if (
        not existing.empty
        and not discovered_evidence.empty
        and {"symbol"}.issubset(existing.columns)
        and {"symbol", "discovery_industry_code"}.issubset(discovered_evidence.columns)
    ):
        existing["symbol"] = existing["symbol"].astype(str).str.strip().str.upper()
        evidence = discovered_evidence[["symbol", "discovery_industry_code"]].copy()
        evidence["symbol"] = evidence["symbol"].astype(str).str.strip().str.upper()
        evidence["discovery_industry_code"] = evidence["discovery_industry_code"].fillna("").astype(str).str.strip()
        evidence = evidence.drop_duplicates("symbol", keep="first").set_index("symbol")["discovery_industry_code"]
        if "discovery_industry_code" not in existing.columns:
            existing["discovery_industry_code"] = ""
        current_code = existing["discovery_industry_code"].fillna("").astype(str).str.strip()
        missing_code = current_code.eq("")
        mapped_code = existing["symbol"].map(evidence).fillna("").astype(str).str.strip()
        existing.loc[missing_code & mapped_code.ne(""), "discovery_industry_code"] = mapped_code[missing_code & mapped_code.ne("")]
    if existing.empty:
        existing = pd.DataFrame(columns=[
            "symbol", "name", "market", "sector", "asset_type", "market_benchmark",
            "sector_benchmark", "exchange", "country", "currency", "instrument_type",
            "identity_status", "market_cap_status", "provider_status", "activation_status",
            "review_note", "identity_evidence_url", "identity_reviewed_at",
            "market_cap_source_url", "market_cap_asof", "depositary_ratio_status",
            "market_cap_usd_b_secondary",
        ])
    known = set(existing.get("symbol", pd.Series(dtype=str)).astype(str).str.strip().str.upper()) - {""}
    active = set(active_universe.get("symbol", pd.Series(dtype=str)).astype(str).str.strip().str.upper()) - {""}
    if discovered_rows is None or discovered_rows.empty:
        return existing, 0
    new = discovered_rows.copy()
    new["symbol"] = new["symbol"].astype(str).str.strip().str.upper()
    new = new[~new["symbol"].isin(known | active)].drop_duplicates("symbol", keep="first")
    if new.empty:
        return existing, 0
    columns = list(existing.columns) + [col for col in new.columns if col not in existing.columns]
    combined = pd.concat([existing.reindex(columns=columns), new.reindex(columns=columns)], ignore_index=True)
    return combined, len(new)


def _load_krx_master() -> pd.DataFrame:
    frames = []
    for market in ("KOSPI", "KOSDAQ"):
        master = download_krx_master(market)
        if master is None or master.empty:
            continue
        frame = master[["symbol", "instrument_class"]].copy()
        frame["master_security_type"] = frame["instrument_class"].map({
            "stock_candidate": "2", "etp_candidate": "3",
        }).fillna("4")
        frame["master_dr_flag"] = ""
        frame["master_dr_country_code"] = ""
        frame["master_industry_code"] = ""
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=[
            "symbol", "master_security_type", "master_dr_flag", "master_dr_country_code", "master_industry_code",
        ])
    return pd.concat(frames, ignore_index=True).drop_duplicates("symbol", keep="first")


def collect_discoveries(client, usdkrw: float | None = None) -> tuple[pd.DataFrame, dict]:
    raw_frames, page_counts = [], {}
    master = fetch_us_security_master(exchanges=("NAS", "NYS", "AMS"))
    for exchange in ("NAS", "NYS", "AMS"):
        raw = fetch_us_market_cap_candidates(client, exchange=exchange, max_pages=50)
        page_counts[f"US_{exchange}"] = int(raw.attrs.get("ranking_pages_fetched", 0))
        if raw.empty:
            continue
        raw["symb"] = raw["symb"].astype(str).str.strip().str.upper()
        current_master = master[master["listing_exchange"].astype(str).str.upper().eq(exchange)].copy()
        current_master["symbol"] = current_master["symbol"].astype(str).str.strip().str.upper()
        merged = raw.merge(
            current_master[["symbol", "master_security_type", "master_dr_flag",
                            "master_dr_country_code", "master_industry_code", "english_name"]],
            left_on="symb", right_on="symbol", how="left",
        )
        merged["ename"] = merged["ename"].where(
            merged["ename"].astype(str).str.strip().ne(""), merged["english_name"]
        )
        raw_frames.append(merged.drop(columns=["symbol", "english_name"], errors="ignore"))

    krx = fetch_korea_market_cap_candidates(client, market="0000", max_pages=10)
    page_counts["KRX_all"] = int(krx.attrs.get("ranking_pages_fetched", 0))
    if not krx.empty:
        krx["mksc_shrn_iscd"] = krx["mksc_shrn_iscd"].astype(str).str.strip().str.zfill(6)
        krx_master = _load_krx_master()
        krx_master["symbol"] = krx_master["symbol"].astype(str).str.strip().str.zfill(6)
        krx = krx.merge(
            krx_master, left_on="mksc_shrn_iscd", right_on="symbol", how="left"
        ).drop(columns=["symbol"], errors="ignore")
        raw_frames.append(krx)

    raw = pd.concat(raw_frames, ignore_index=True, sort=False) if raw_frames else pd.DataFrame()
    normalized = normalize_market_cap_candidates(raw, min_cap_usd=MIN_CAP_USD, usdkrw=usdkrw)
    return normalized, {
        "ranking_pages_fetched": page_counts,
        "raw_ranking_rows": int(len(raw)),
        "normalized_rows": int(len(normalized)),
        "usdkrw_rate_used": usdkrw,
    }


def _write_status(status: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    started = datetime.now(timezone.utc)
    discovered_at = started.astimezone(ZoneInfo("Asia/Seoul")).date().isoformat()
    rate_text = os.getenv("USD_KRW_RATE", "").strip()
    usdkrw, usdkrw_source, usdkrw_date = resolve_usdkrw_rate(rate_text)
    try:
        client = KISOverseasPrices(paper=False)
        normalized, meta = collect_discoveries(client, usdkrw=usdkrw)
        discoveries = build_discovered_candidate_rows(normalized, discovered_at)
        existing = pd.read_csv(CANDIDATES_PATH, dtype=str, keep_default_na=False) if CANDIDATES_PATH.exists() else pd.DataFrame()
        active = pd.read_csv(UNIVERSE_PATH, dtype=str, keep_default_na=False) if UNIVERSE_PATH.exists() else pd.DataFrame(columns=["symbol"])
        combined, added = merge_candidate_discoveries(existing, discoveries, active)
        combined.to_csv(CANDIDATES_PATH, index=False)
        status = {
            "status": "success", "started_at_utc": started.isoformat(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "discovered_at_kst": discovered_at, "minimum_stock_market_cap_usd": MIN_CAP_USD,
            "existing_candidate_count": int(len(existing)), "normalized_ranking_rows": int(meta["normalized_rows"]),
            "eligible_pending_rows_found": int(len(discoveries)), "new_candidates_added": int(added),
            "candidate_count_after_update": int(len(combined)), **meta,
            "usdkrw_rate_source": usdkrw_source,
            "usdkrw_rate_date": usdkrw_date,
            "note": "Discovery only. No candidate was activated. Unknown market caps and identities remain pending review. KRX USD cap screening is deferred if a fresh FX reference rate is unavailable.",
        }
        _write_status(status)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        _write_status({
            "status": "failed", "started_at_utc": started.isoformat(),
            "failed_at_utc": datetime.now(timezone.utc).isoformat(),
            "discovered_at_kst": discovered_at, "error_type": type(exc).__name__,
            "error": str(exc)[:1000],
            "usdkrw_rate_used": usdkrw,
            "usdkrw_rate_source": usdkrw_source,
            "usdkrw_rate_date": usdkrw_date,
            "note": "No candidate activation. Review this failed discovery attempt before retrying.",
        })
        raise


if __name__ == "__main__":
    raise SystemExit(main())
