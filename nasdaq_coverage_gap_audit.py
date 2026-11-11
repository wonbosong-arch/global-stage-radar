"""Read-only Nasdaq/KIS coverage gap audit for the manual public snapshot.

Run against a local copy of the approved snapshot and its hash-bound receipt.
Ticker matches are *not* evidence of common-share identity, cap basis, or approval.
This module performs no network calls, candidate intake, or data writes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

import pandas as pd

from nasdaq_github_store import verified_dates
from nasdaq_local_csv_review import clean, missing, read_table
from nasdaq_monthly_refresh import quality
from nasdaq_single_source import native_security_conflict

ROOT = Path(__file__).resolve().parent
US_VENUES = frozenset({"NAS", "NYS", "AMS"})
MIN_USD_CAP = Decimal("1000000000")

# Independent *review signals*, not a common-stock eligibility classifier.
# The source is an issuer-level Nasdaq screener and can list preferred shares,
# debt, fund units and ADRs with the same issuer market cap as a common share.
NAME_SIGNALS = (
    ("debt_or_structured_security", re.compile(
        r"\b(?:NOTES?|DEBENTURES?|BONDS?|SUBORDINATED|ZONES|"
        r"CORPORATE UNITS?|TANGIBLE EQUITY UNITS?|"
        r"FIXED[\s-]+TO[\s-]+FLOATING)\b", re.I)),
    ("preferred_security", re.compile(r"\b(?:PREFERRED|PREFERENCE|PFD)\b", re.I)),
    ("warrant_or_right", re.compile(
        r"\b(?:WARRANTS?|CONTINGENT VALUE RIGHTS?|SUBSCRIPTION RIGHTS?)\b", re.I)),
    ("fund_or_trust", re.compile(
        r"\b(?:FUNDS?|ETF|ETN|CLOSED[\s-]+END|INVESTMENT TRUST)\b", re.I)),
    ("depositary_receipt", re.compile(
        r"\b(?:ADRS?|ADS|AMERICAN DEPOSITA(?:RY|RY)|"
        r"AMERICAN DEPOSITORY|DEPOSITARY RECEIPTS?|DEPOSITORY RECEIPTS?|"
        r"(?:NEW YORK|NY) REGISTRY SHARES)\b", re.I)),
    ("unit_or_partnership", re.compile(r"\b(?:UNITS?|PARTNERSHIP INTERESTS?)\b", re.I)),
)


def security_name_signal(symbol: str, name: str) -> str:
    """Conservative risk signal; lack of a match is never a common-share pass."""
    for label, pattern in NAME_SIGNALS:
        if pattern.search(name):
            return label
    if re.search(r"\bCLASS\s+[A-Z]\b", name, re.I) or re.search(r"\.[A-Z]$", symbol, re.I):
        return "share_class_requires_identity_review"
    return "no_explicit_security_type_signal_unverified"



def _us_symbols(frame: pd.DataFrame, venue_column: str) -> set[str]:
    if not {"symbol", venue_column}.issubset(frame.columns):
        raise ValueError("US reference requires symbol and venue columns")
    venues = frame[venue_column].fillna("").astype(str).str.strip().str.upper()
    symbols = frame["symbol"].fillna("").astype(str).str.strip().str.upper()
    return set(symbols.loc[venues.isin(US_VENUES)]).difference({""})


def audit_gap(raw: bytes, receipt: dict, candidates: pd.DataFrame,
              kis_master: pd.DataFrame, *, now: datetime | None = None,
              min_rows: int = 5000) -> dict:
    """Compare a verified Nasdaq CSV with saved US ticker inventories only.

    No input is changed. The returned potential-gap records are always marked
    review-only: Nasdaq market cap may refer to the issuer, not the security.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Evaluation time must be timezone-aware")
    downloaded, approved = verified_dates(raw, receipt, now)
    measured = quality(raw, {"symbol_aliases": []}, min_rows=min_rows)
    _, _, rows = read_table(raw)
    candidate_symbols = _us_symbols(candidates, "exchange")
    master_symbols = _us_symbols(kis_master, "listing_exchange")
    master_venues: dict[str, set[str]] = defaultdict(set)
    master_records: dict[str, list[dict]] = defaultdict(list)
    for item in kis_master.to_dict("records"):
        symbol = clean(item.get("symbol")).upper()
        venue = clean(item.get("listing_exchange")).upper()
        if symbol and venue in US_VENUES:
            master_venues[symbol].add(venue)
            master_records[symbol].append(item)

    gaps = []
    seen_cap = 0
    already_in_candidates = 0
    for source in rows:
        symbol = clean(source["Symbol"]).upper()
        value = clean(source["Market Cap"]).replace(",", "").removeprefix("$")
        if missing(value, "Market Cap"):
            continue
        try:
            cap = Decimal(value)
        except InvalidOperation:
            raise ValueError("Invalid Nasdaq market-cap number") from None
        if not cap.is_finite() or cap < MIN_USD_CAP:
            continue
        seen_cap += 1
        if symbol in candidate_symbols:
            already_in_candidates += 1
            continue
        signal = native_security_conflict(
            source, symbol, {"name": "", "depositary_ratio_status": ""})
        name_type = security_name_signal(symbol, source["Name"])
        master_hits = master_records.get(symbol, [])
        master_dr_flags = sorted({clean(item.get("master_dr_flag")).upper()
                                  for item in master_hits if clean(item.get("master_dr_flag"))})
        master_type_codes = sorted({clean(item.get("master_security_type"))
                                    for item in master_hits if clean(item.get("master_security_type"))})
        identity_flags = []
        if not master_hits:
            identity_flags.append("no_kis_master_ticker")
        elif len(master_hits) != 1:
            identity_flags.append("kis_master_ticker_collision")
        if "Y" in master_dr_flags:
            identity_flags.append("kis_dr_flag_requires_ratio_and_identity_review")
        if name_type != "no_explicit_security_type_signal_unverified":
            identity_flags.append("source_security_type_requires_review")
        gaps.append({
            "symbol": symbol,
            "source_name": source["Name"],
            "nasdaq_sector": source["Sector"],
            "nasdaq_industry": source["Industry"],
            "nasdaq_reported_cap_usd": str(cap),
            "kis_ticker_present": symbol in master_symbols,
            "kis_venues_by_ticker": sorted(master_venues.get(symbol, ())),
            "name_warning": signal or "no_obvious_name_warning_unverified",
            "security_name_signal": name_type,
            "kis_master_dr_flags": master_dr_flags,
            "kis_master_security_type_codes_unverified": master_type_codes,
            "identity_review_flags": sorted(identity_flags),
            "review_status": "research_only_not_approved",
        })
    gaps.sort(key=lambda row: (-Decimal(row["nasdaq_reported_cap_usd"]), row["symbol"]))
    sectors = Counter(row["nasdaq_sector"] or "missing" for row in gaps)
    warnings = Counter(row["name_warning"] for row in gaps)
    security_signals = Counter(row["security_name_signal"] for row in gaps)
    identity_flags = Counter(flag for row in gaps for flag in row["identity_review_flags"])
    known_kis = sum(row["kis_ticker_present"] for row in gaps)
    result = {
        "mode": "offline_research_only",
        "source_sha256": measured["csv_sha256"],
        "source_rows": measured["rows"],
        "source_downloaded_on_utc": downloaded.isoformat(),
        "source_approved_at_utc": approved.isoformat(),
        "minimum_issuer_cap_usd_unverified": str(MIN_USD_CAP),
        "source_ge_cap": seen_cap,
        "source_ge_cap_existing_candidate_ticker": already_in_candidates,
        "missing_from_candidate_ticker_inventory": len(gaps),
        "missing_candidate_with_kis_master_ticker": known_kis,
        "missing_candidate_without_kis_master_ticker": len(gaps) - known_kis,
        "gap_name_warnings": dict(sorted(warnings.items())),
        "gap_security_name_signals": dict(sorted(security_signals.items())),
        "gap_identity_review_flags": dict(sorted(identity_flags.items())),
        "gap_by_nasdaq_sector": dict(sorted(sectors.items())),
        "operational_additions": 0,
        "network_requests": 0,
        "notes": [
            "Source CSV lacks listing exchange; ticker overlaps do not establish exact security identity.",
            "Nasdaq reported market cap may describe the issuer, not a preferred or ADR share class.",
            "Name warnings are only review signals. No unflagged row is cleared for activation.",
            "A KIS master code or DR flag alone does not prove common-share status or ADS ratio.",
        ],
        "review_rows": gaps,
    }
    assert result["source_ge_cap"] == (
        result["source_ge_cap_existing_candidate_ticker"]
        + result["missing_from_candidate_ticker_inventory"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nasdaq-csv", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--candidates", type=Path,
                        default=ROOT / "data" / "stock_universe_candidates.csv")
    parser.add_argument("--kis-master", type=Path,
                        default=ROOT / "data" / "unranked_us_stock_master.csv")
    parser.add_argument("--preview", type=int, default=0,
                        help="Show at most N unapproved gap rows in stdout; default 0")
    args = parser.parse_args()
    if not 0 <= args.preview <= 100:
        parser.error("--preview must be between 0 and 100")
    report = audit_gap(
        args.nasdaq_csv.read_bytes(),
        json.loads(args.receipt.read_text(encoding="utf-8")),
        pd.read_csv(args.candidates, dtype=str, keep_default_na=False),
        pd.read_csv(args.kis_master, dtype=str, keep_default_na=False),
    )
    rows = report.pop("review_rows")
    if args.preview:
        report["unapproved_preview"] = rows[:args.preview]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
