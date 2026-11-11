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
from nasdaq_single_source import name_basis, native_security_conflict

ROOT = Path(__file__).resolve().parent
US_VENUES = frozenset({"NAS", "NYS", "AMS"})
MIN_USD_CAP = Decimal("1000000000")
SEC_REGISTRY = ROOT / "docs" / "evidence" / "us-nasdaq-issuer-listing-sec-20261111.json"

# Independent *review signals*, not a common-stock eligibility classifier.
# The source is an issuer-level Nasdaq screener and can list preferred shares,
# debt, fund units and ADRs with the same issuer market cap as a common share.
NAME_SIGNALS = (
    ("debt_or_structured_security", re.compile(
        r"\b(?:NOTES?|DEBENTURES?|BONDS?|SUBORDINATED|ZONES|STRATS|"
        r"CORPORATE UNITS?|TANGIBLE EQUITY UNITS?|"
        r"FIXED[\s-]+TO[\s-]+FLOATING)\b", re.I)),
    ("preferred_security", re.compile(r"\b(?:PREFERRED|PREFERENCE|PFD|PRF)\b", re.I)),
    ("warrant_or_right", re.compile(
        r"\b(?:WARRANTS?|CONTINGENT VALUE RIGHTS?|SUBSCRIPTION RIGHTS?)\b", re.I)),
    ("fund_or_trust", re.compile(
        r"\b(?:FUNDS?|ETF|ETN|CLOSED[\s-]+END|INVESTMENT TRUST|TRUST)\b", re.I)),
    ("depositary_receipt", re.compile(
        r"\b(?:ADRS?|ADS|AMERICAN DEPOSITA(?:RY|RY)|"
        r"AMERICAN DEPOSITORY|DEPOSITARY RECEIPTS?|DEPOSITORY RECEIPTS?|"
        r"(?:NEW YORK|NY) REGISTRY SHARES|DEPOSITARY SHARES?|DEPOSITORY SHARES?|DEP SHS)\b", re.I)),
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




def issuer_identity_triage(source: dict, symbol: str, master_hits: list[dict]) -> dict:
    """Prioritize manual identity work; never certify eligibility or market cap.

    Corroborate issuer against stored KIS name and venue; do not treat a KIS
    DR=N flag, security type 2, or issuer-level Nasdaq cap as a pass.
    """
    source_signal = security_name_signal(symbol, clean(source.get("Name")))
    basis = None
    master_signal = "missing_kis_master_name"
    if not master_hits:
        status = "P4_kis_master_missing"
    elif len(master_hits) != 1:
        status = "P4_kis_ticker_or_venue_ambiguous"
    else:
        m = master_hits[0]
        master_name = clean(m.get("english_name"))
        master_signal = security_name_signal(symbol, master_name) if master_name else "missing_kis_master_name"
        source_country = clean(source.get("Country"))
        basis = name_basis([master_name], clean(source.get("Name"))) if master_name else None
        non_common = {"debt_or_structured_security", "preferred_security",
                      "warrant_or_right", "fund_or_trust", "unit_or_partnership"}
        if source_signal in non_common or master_signal in non_common:
            status = "P3_noncommon_instrument_review"
        elif (source_signal == "depositary_receipt"
              or master_signal == "depositary_receipt"
              or clean(m.get("master_dr_flag")).upper() == "Y"):
            status = "P3_depositary_or_ratio_review"
        elif clean(m.get("master_security_type")) != "2":
            status = "P4_kis_security_type_unresolved"
        elif source_country != "United States":
            status = "P3_foreign_issuer_listing_review"
        elif not basis:
            status = "P2_issuer_name_mismatch_or_missing"
        elif not re.search(r"\b(?:COMMON STOCK|COMMON SHARES?|ORDINARY SHARES?)\b",
                           clean(source.get("Name")), re.I):
            status = "P2_common_share_label_missing"
        elif source_signal != "no_explicit_security_type_signal_unverified":
            status = "P2_share_class_requires_review"
        else:
            status = "P1_kis_name_coherent_primary_evidence_pending"
    return {
        "issuer_name_basis": basis,
        "kis_master_name_signal": master_signal,
        "issuer_identity_review_cohort": status,
        "operational_approval_granted": False,
    }

def _us_symbols(frame: pd.DataFrame, venue_column: str) -> set[str]:
    if not {"symbol", venue_column}.issubset(frame.columns):
        raise ValueError("US reference requires symbol and venue columns")
    venues = frame[venue_column].fillna("").astype(str).str.strip().str.upper()
    symbols = frame["symbol"].fillna("").astype(str).str.strip().str.upper()
    return set(symbols.loc[venues.isin(US_VENUES)]).difference({""})




def _sec_reference_index(registry: dict | None) -> dict[str, dict] | None:
    """Validate research-only references without checking or accepting filings.

    A stored SEC URL is a navigation aid, not independent identity, price,
    market-cap, exchange support, or activation evidence.
    """
    if registry is None:
        return None
    if not isinstance(registry, dict) or registry.get("operational_additions") != 0:
        raise ValueError("Invalid read-only SEC evidence registry")
    records = registry.get("records")
    if (not isinstance(records, list) or
            registry.get("record_count") != len(records)):
        raise ValueError("Invalid SEC evidence record count")
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid SEC evidence record")
        symbol = record.get("symbol")
        venue = record.get("kis_venue")
        url = record.get("source_url")
        if (not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9./-]+", symbol)
                or symbol in indexed or venue not in US_VENUES
                or not isinstance(url, str)
                or not url.startswith("https://www.sec.gov/Archives/edgar/data/")
                or record.get("activation_status") != "pending_review"
                or record.get("evidence_status") != "sec_filing_security_and_symbol_checked"):
            raise ValueError("Invalid or duplicated SEC reference")
        indexed[symbol] = record
    return indexed


def _sec_reference_status(symbol: str, venues: set[str],
                          references: dict[str, dict] | None) -> str:
    if references is None:
        return "sec_registry_not_loaded"
    record = references.get(symbol)
    if record is None:
        return "sec_reference_not_registered"
    if len(venues) != 1:
        return "sec_reference_kis_venue_absent_or_ambiguous"
    return ("sec_reference_same_saved_kis_venue_review_only"
            if record["kis_venue"] in venues
            else "sec_reference_saved_kis_venue_disagreement")


def audit_gap(raw: bytes, receipt: dict, candidates: pd.DataFrame,
              kis_master: pd.DataFrame, *, now: datetime | None = None,
              min_rows: int = 5000,
              sec_registry: dict | None = None) -> dict:
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
    sec_references = _sec_reference_index(sec_registry)
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
        triage = issuer_identity_triage(source, symbol, master_hits)
        sec_status = _sec_reference_status(symbol, master_venues.get(symbol, set()),
                                           sec_references)
        gaps.append({
            **triage,
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
            "sec_reference_status": sec_status,
            "sec_reference_url": (sec_references[symbol]["source_url"]
                                  if sec_references is not None and symbol in sec_references else None),
            "review_status": "research_only_not_approved",
        })
    gaps.sort(key=lambda row: (-Decimal(row["nasdaq_reported_cap_usd"]), row["symbol"]))
    sectors = Counter(row["nasdaq_sector"] or "missing" for row in gaps)
    warnings = Counter(row["name_warning"] for row in gaps)
    security_signals = Counter(row["security_name_signal"] for row in gaps)
    identity_flags = Counter(flag for row in gaps for flag in row["identity_review_flags"])
    issuer_cohorts = Counter(row["issuer_identity_review_cohort"] for row in gaps)
    sec_statuses = Counter(row["sec_reference_status"] for row in gaps)
    p1_statuses = Counter(row["sec_reference_status"] for row in gaps
                          if row["issuer_identity_review_cohort"].startswith("P1_"))
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
        "gap_issuer_identity_review_cohorts": dict(sorted(issuer_cohorts.items())),
        "gap_sec_reference_statuses": dict(sorted(sec_statuses.items())),
        "p1_sec_reference_statuses": dict(sorted(p1_statuses.items())),
        "gap_by_nasdaq_sector": dict(sorted(sectors.items())),
        "operational_additions": 0,
        "network_requests": 0,
        "notes": [
            "Source CSV lacks listing exchange; ticker overlaps do not establish exact security identity.",
            "Nasdaq reported market cap may describe the issuer, not a preferred or ADR share class.",
            "Name warnings are only review signals. No unflagged row is cleared for activation.",
            "A KIS master code or DR flag alone does not prove common-share status or ADS ratio.",
            "Issuer name coherence prioritizes review only; primary security evidence and KIS price coverage still require confirmation.",
            "Stored SEC filing URLs are unverified here; matching a venue cannot authorize candidate intake or activation.",
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
    parser.add_argument("--sec-registry", type=Path, default=SEC_REGISTRY,
                        help="Existing research-only SEC link registry (read-only)")
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
        sec_registry=json.loads(args.sec_registry.read_text(encoding="utf-8")),
    )
    rows = report.pop("review_rows")
    if args.preview:
        report["unapproved_preview"] = rows[:args.preview]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
