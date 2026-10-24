"""Conservative market-cap reconciliation triage for pending candidates.

This is a plausibility check, not an official market-cap verification. It compares
secondary market-cap snapshots with a close price and a dated reported share count
for a small, explicitly sourced subset. A mismatch can reflect dates, buybacks,
issuance, class/ADS conventions, or bad source data; never auto-verify or activate.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
CANDIDATES = ROOT / "data" / "stock_universe_candidates.csv"
PRICES = ROOT / "data" / "candidate_daily_prices.csv"
OUTPUT = ROOT / "data" / "candidate_market_cap_reconciliation.csv"

# Shares in millions, transcribed from the cited issuer filings; effective dates
# are retained because a dated filing share count is not the same as current shares.
OFFICIAL_SHARE_COUNTS = {
    "ORCL": {
        "shares_m": 2880.471,
        "shares_asof": "2026-06-12",
        "source": "https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm",
    },
    "CRM": {
        "shares_m": 923.0,
        "shares_asof": "2026-02-25",
        "source": "https://www.sec.gov/Archives/edgar/data/1108524/000110852426000060/crm-20260131.htm",
    },
    "COST": {
        "shares_m": 443.129349,
        "shares_asof": "2026-09-29",
        "source": "https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/cost-20260830.htm",
    },
    "WELL": {
        "shares_m": 697.752530,
        "shares_asof": "2026-02-06",
        "source": "https://www.sec.gov/Archives/edgar/data/766704/000076670426000010/well-20251231.htm",
    },
    "ANET": {
        "shares_m": 1261.224648,
        "shares_asof": "2026-07-30",
        "source": "https://www.sec.gov/Archives/edgar/data/1596532/000159653226000175/anet-20260630.htm",
    },
    "CSCO": {
        "shares_m": 3942.586873,
        "shares_asof": "2026-08-27",
        "source": "https://www.sec.gov/Archives/edgar/data/858877/000085887726000132/csco-20260725.htm",
    },
    "CVX": {
        "shares_m": 1995.385539,
        "shares_asof": "2026-02-06",
        "source": "https://www.sec.gov/Archives/edgar/data/93410/000009341026000078/cvx-20251231.htm",
    },
}


def build_report(candidates: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    c = candidates.copy()
    p = prices.copy()
    for col in ("symbol", "market_cap_usd_b_secondary", "market_cap_asof", "market_cap_status", "instrument_type"):
        if col not in c:
            c[col] = ""
    for col in ("symbol", "date", "close"):
        if col not in p:
            p[col] = ""
    p["date"] = pd.to_datetime(p["date"], errors="coerce")
    p["close"] = pd.to_numeric(p["close"], errors="coerce")
    p = p.dropna(subset=["date", "close"])
    p = p.sort_values("date").groupby("symbol", as_index=False).tail(1)
    latest = {r["symbol"]: r for _, r in p.iterrows()}

    rows = []
    for _, candidate in c.iterrows():
        symbol = str(candidate["symbol"]).strip()
        cap = pd.to_numeric(candidate["market_cap_usd_b_secondary"], errors="coerce")
        px = latest.get(symbol)
        close = float(px["close"]) if px is not None else None
        price_date = px["date"].date().isoformat() if px is not None else ""
        shares = OFFICIAL_SHARE_COUNTS.get(symbol)
        implied_shares = (float(cap) * 1000 / close) if pd.notna(cap) and close and close > 0 else None
        reported_shares = shares["shares_m"] if shares else None
        difference_pct = (
            (implied_shares / reported_shares - 1) * 100
            if implied_shares is not None and reported_shares
            else None
        )
        if candidate["instrument_type"] == "adr_candidate":
            outcome = "adr_share_class_review_required"
        elif shares is None:
            outcome = "official_share_count_not_captured"
        elif close is None or pd.isna(cap):
            outcome = "price_or_secondary_cap_missing"
        elif abs(difference_pct) <= 3:
            outcome = "arithmetic_consistent_date_basis_still_unverified"
        elif abs(difference_pct) <= 10:
            outcome = "investigate_share_count_or_date_basis"
        else:
            outcome = "material_arithmetic_mismatch_review"
        rows.append({
            "symbol": symbol,
            "price_date": price_date,
            "close_usd": close,
            "secondary_market_cap_asof": candidate["market_cap_asof"],
            "secondary_market_cap_usd_b": float(cap) if pd.notna(cap) else None,
            "implied_shares_m_from_cap_and_close": round(implied_shares, 3) if implied_shares is not None else None,
            "reported_shares_m": reported_shares,
            "reported_shares_asof": shares["shares_asof"] if shares else "",
            "reported_shares_source_url": shares["source"] if shares else "",
            "implied_vs_reported_shares_pct": round(difference_pct, 2) if difference_pct is not None else None,
            "triage_outcome": outcome,
            "market_cap_status_remains": candidate["market_cap_status"],
            "verification_note": "Triage only; dated share count and secondary cap are not independently reconciled to an identical effective date. Never auto-verify or activate.",
        })
    return pd.DataFrame(rows).sort_values(["triage_outcome", "symbol"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--prices", type=Path, default=PRICES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    candidates = pd.read_csv(args.candidates, dtype=str, keep_default_na=False)
    prices = pd.read_csv(args.prices, dtype={"symbol": str})
    report = build_report(candidates, prices)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"rows={len(report)}")
    print("triage_outcomes=" + str(report["triage_outcome"].value_counts().to_dict()))
    print("market_cap_status_changed=0")
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
