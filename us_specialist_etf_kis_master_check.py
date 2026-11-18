"""Read-only KIS master identity evidence for five price-proven US ETF candidates.

The approved one-time AMS price probe returned 400 daily bars and 83 completed
weeks for each symbol on 2026-11-18, but prices alone cannot identify a fund.
Reuse the existing public KIS master parser; never export full master data,
OHLCV, operating CSV, or automatically approve a benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import re

import pandas as pd

from kis_universe import fetch_us_security_master

# Exact symbols whose AMS quote histories were observed, and issuer/fund
# descriptors expected in public KIS master English security names.
# A miss remains review-only rather than being guessed.
EXPECTED = {
    "XBI": ("SPDR", "BIOTECH"),
    "IYR": ("ISHARES", "REAL", "ESTATE"),
    "KBE": ("SPDR", "BANK"),
    "KIE": ("SPDR", "INSURANCE"),
    "JETS": ("US", "GLOBAL", "JETS"),
}


def _tokens(value):
    return set(re.findall(r"[A-Z0-9]+", str(value or "").upper()))


def assess_master(master: pd.DataFrame) -> dict:
    """Check venue/type/name without changing KIS records or research Stage."""
    needed = {"symbol", "listing_exchange", "master_security_type", "english_name"}
    if not needed.issubset(master.columns):
        raise ValueError("KIS US master has missing required identity columns")
    rows = master.copy()
    for col in needed:
        rows[col] = rows[col].fillna("").astype(str).str.strip()
    details = []
    for symbol, words in EXPECTED.items():
        matches = rows.loc[
            rows.symbol.str.upper().eq(symbol)
            & rows.listing_exchange.str.upper().eq("AMS")
        ]
        status = "kis_master_missing"
        if len(matches) > 1:
            status = "kis_master_ambiguous"
        elif len(matches) == 1:
            record = matches.iloc[0]
            if record.master_security_type != "3":
                status = "kis_master_not_etp"
            elif not set(words).issubset(_tokens(record.english_name)):
                status = "kis_master_name_review"
            else:
                status = "kis_master_etp_name_match"
        details.append({
            "symbol": symbol, "master_venue": "AMS", "status": status,
            "kis_master_evidence_supported": status == "kis_master_etp_name_match",
            "etf_approved": False, "analysis_activated": False,
        })
    return {
        "source": "KIS public AMS security master; instrument-name evidence only",
        "counts": dict(Counter(item["status"] for item in details)),
        "details": details,
        "requested": len(EXPECTED), "price_data_saved": False,
        "universe_updated": False, "stage_definition_changed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="Fetch the public KIS AMS master once")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"mode": "offline_plan_no_network",
                          "symbols": list(EXPECTED), "master_venue": "AMS",
                          "universe_updated": False}))
        return
    # The KIS master URL and parser already exist in kis_universe.py.
    report = assess_master(fetch_us_security_master(exchanges=("AMS",)))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
