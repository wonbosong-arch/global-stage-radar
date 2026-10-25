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
    "CAT": {
        "shares_m": 459.674889,
        "shares_asof": "2026-06-30",
        "source": "https://www.sec.gov/Archives/edgar/data/18230/000001823026000046/cat-20260630.htm",
    },
    "PG": {
        "shares_m": 2324.433060,
        "shares_asof": "2026-07-31",
        "source": "https://www.sec.gov/Archives/edgar/data/80424/000008042426000103/pg-20260630.htm",
    },
    "HD": {
        "shares_m": 996.011466,
        "shares_asof": "2026-03-04",
        "source": "https://www.sec.gov/Archives/edgar/data/354950/000162828026019436/hd-20260201.htm",
    },
    "BAC": {
        "shares_m": 7176.682170,
        "shares_asof": "2026-02-24",
        "source": "https://www.sec.gov/Archives/edgar/data/70858/000007085826000157/bac-20251231.htm",
    },
    "AMGN": {
        "shares_m": 539.067675,
        "shares_asof": "2026-02-10",
        "source": "https://www.sec.gov/Archives/edgar/data/318154/000031815426000010/amgn-20251231.htm",
    },
    "SBUX": {
        "shares_m": 1140.0,
        "shares_asof": "2026-07-23",
        "source": "https://www.sec.gov/Archives/edgar/data/829224/000082922426000130/sbux-20260628.htm",
    },
    "NFLX": {
        "shares_m": 4222.162150,
        "shares_asof": "2025-12-31",
        "source": "https://www.sec.gov/Archives/edgar/data/1065280/000106528026000034/nflx-20251231.htm",
    },
    "WELL": {
        "shares_m": 697.752530,
        "shares_asof": "2026-02-06",
        "source": "https://www.sec.gov/Archives/edgar/data/766704/000076670426000010/well-20251231.htm",
    },
    "CSCO": {
        "shares_m": 3942.586873,
        "shares_asof": "2026-08-27",
        "source": "https://www.sec.gov/Archives/edgar/data/858877/000085887726000132/csco-20260725.htm",
    },
    "CEG": {
        "shares_m": 354.307379,
        "shares_asof": "2026-07-31",
        "source": "https://www.sec.gov/Archives/edgar/data/1868275/000186827526000104/ceg-20260630.htm",
    },
    "CVX": {
        "shares_m": 1975.771274,
        "shares_asof": "2026-06-30",
        "source": "https://www.sec.gov/Archives/edgar/data/93410/000009341026000167/cvx-20260630.htm",
    },
    "TMUS": {
        "shares_m": 1072.671613,
        "shares_asof": "2026-07-17",
        "source": "https://www.sec.gov/Archives/edgar/data/1283699/000128369926000101/tmus-20260630.htm",
    },
    "AEP": {
        "shares_m": 544.397352,
        "shares_asof": "2026-07-30",
        "source": "https://www.sec.gov/Archives/edgar/data/92487/000000490426000059/aep-20260630.htm",
    },
    "KO": {
        "shares_m": 4302.549243,
        "shares_asof": "2026-07-27",
        "source": "https://www.sec.gov/Archives/edgar/data/21344/000162828026050503/ko-20260703.htm",
    },
    "ANET": {
        "shares_m": 1261.224648,
        "shares_asof": "2026-07-30",
        "source": "https://www.sec.gov/Archives/edgar/data/1596532/000159653226000175/anet-20260630.htm",
    },
    "ADBE": {
        "shares_m": 389.2,
        "shares_asof": "2026-09-18",
        "source": "https://www.sec.gov/Archives/edgar/data/796343/000079634326000156/adbe-20260828.htm",
    },
    "MCD": {
        "shares_m": 707.641531,
        "shares_asof": "2026-06-30",
        "source": "https://www.sec.gov/Archives/edgar/data/63908/000006390826000073/mcd-20260630.htm",
    },
    "ETN": {
        "shares_m": 388.4,
        "shares_asof": "2026-06-30",
        "source": "https://www.sec.gov/Archives/edgar/data/1551182/000155118226000030/etn-20260630.htm",
    },
    "IBM": {
        "shares_m": 942.134390,
        "shares_asof": "2026-06-30",
        "source": "https://www.sec.gov/Archives/edgar/data/51143/000005114326000078/ibm-20260630.htm",
    },
    "NOW": {
        "shares_m": 1034.0,
        "shares_asof": "2026-06-30",
        "source": "https://www.sec.gov/Archives/edgar/data/1373715/000137371526000076/now-20260630.htm",
    },
    "PLTR": {
        "shares_m": 2402.058480,
        "shares_asof": "2026-07-27",
        "source": "https://www.sec.gov/Archives/edgar/data/1321655/000132165526000041/pltr-20260630.htm",
        "note": "Total of Class A, Class B, and Class F shares disclosed in the 10-Q; class mix matters for instrument/capitalization interpretation.",
    },
    "COP": {
        "shares_m": 1201.337479,
        "shares_asof": "2026-06-30",
        "source": "https://www.sec.gov/Archives/edgar/data/1163165/000116316526000032/cop-20260630.htm",
    },
    "TJX": {
        "shares_m": 1099.974061,
        "shares_asof": "2026-08-21",
        "source": "https://www.sec.gov/Archives/edgar/data/109198/000010919826000048/tjx-20260801.htm",
    },
    "DIS": {
        "shares_m": 1726.686902,
        "shares_asof": "2026-07-29",
        "source": "https://www.sec.gov/Archives/edgar/data/1744489/000174448926000057/dis-20260627.htm",
    },
    "DE": {
        "shares_m": 269.937425,
        "shares_asof": "2026-05-03",
        "source": "https://www.sec.gov/Archives/edgar/data/315189/000110465926067311/de-20260503x10q.htm",
    },
    "LIN": {
        "shares_m": 460.980163,
        "shares_asof": "2026-06-30",
        "source": "https://www.sec.gov/Archives/edgar/data/1707925/000162828026051289/lin-20260630.htm",
        "note": "Ordinary shares outstanding, net of treasury shares; issuer is incorporated in Ireland and listed in the US.",
    },
    "TSM": {
        "shares_m": 5186.474,
        "shares_asof": "2026-06-30",
        "source": "https://www.sec.gov/Archives/edgar/data/1046179/000104617926000541/a2026q2consolidatedreport-.htm",
        "note": "ADS-equivalent shares: 25,932.370 million ordinary shares divided by 5 ordinary shares per ADS. ADS-equivalent count is used for US ADS price/cap arithmetic; verify source convention and exact share basis.",
    },
    "BABA": {
        "shares_m": 2486.561,
        "shares_asof": "2026-09-22",
        "source": "https://www.stocktitan.net/sec-filings/BABA/6-k-alibaba-group-holding-ltd-current-report-foreign-issuer-c260c31c0da9.html",
        "note": "ADS-equivalent shares: 19,892.488918 million ordinary shares divided by 8 ordinary shares per ADS. AGM filing reports ordinary shares in issue; verify cap vendor convention and exact date basis.",
    },
}


def _normalize_symbols(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    normalized = frame.copy()
    if "symbol" not in normalized.columns:
        raise ValueError(f"{label} input must contain a symbol column.")
    normalized["symbol"] = normalized["symbol"].fillna("").astype(str).str.strip().str.upper()
    if normalized["symbol"].eq("").any():
        raise ValueError(f"{label} input cannot contain blank symbols.")
    duplicates = sorted(normalized.loc[normalized["symbol"].duplicated(keep=False), "symbol"].unique())
    if duplicates:
        raise ValueError(f"{label} input contains duplicate symbols: {duplicates}")
    return normalized


def build_report(candidates: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    c = _normalize_symbols(candidates, "Candidate")
    p = prices.copy()
    for col in ("market_cap_usd_b_secondary", "market_cap_asof", "market_cap_status", "market_cap_source_url", "instrument_type"):
        if col not in c:
            c[col] = ""
    for col in ("date", "close"):
        if col not in p:
            p[col] = ""
    if "symbol" not in p.columns:
        raise ValueError("Price input must contain a symbol column.")
    p["symbol"] = p["symbol"].fillna("").astype(str).str.strip().str.upper()
    p = p.loc[p["symbol"].ne("")].copy()
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
        cap_asof = pd.to_datetime(candidate["market_cap_asof"], errors="coerce")
        share_asof = pd.to_datetime(shares["shares_asof"], errors="coerce") if shares else pd.NaT
        price_cap_gap_days = (
            abs((px["date"] - cap_asof).days)
            if px is not None and pd.notna(cap_asof)
            else None
        )
        price_share_gap_days = (
            abs((px["date"] - share_asof).days)
            if px is not None and pd.notna(share_asof)
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
        if outcome == "material_arithmetic_mismatch_review" or (
            difference_pct is not None and abs(difference_pct) > 10
        ):
            date_review_priority = "P1_material_mismatch"
            date_review_reason = "absolute_share_count_variance_over_10_percent"
        elif outcome in {"official_share_count_not_captured", "price_or_secondary_cap_missing"}:
            date_review_priority = "P2_missing_reconciliation_input"
            date_review_reason = "required_price_cap_or_dated_share_count_input_missing"
        elif price_share_gap_days is not None and price_share_gap_days > 180:
            date_review_priority = "P1_stale_share_count"
            date_review_reason = "share_count_date_more_than_180_days_before_price"
        elif price_share_gap_days is not None and price_share_gap_days > 90:
            date_review_priority = "P2_date_alignment"
            date_review_reason = "share_count_date_more_than_90_days_before_price"
        elif outcome in {"investigate_share_count_or_date_basis", "adr_share_class_review_required"}:
            date_review_priority = "P2_manual_reconciliation"
            date_review_reason = "manual_share_class_or_arithmetic_review"
        else:
            date_review_priority = "P3_routine_evidence"
            date_review_reason = "arithmetic_consistent_but_market_cap_not_verified"

        rows.append({
            "symbol": symbol,
            "date_review_priority": date_review_priority,
            "date_review_reason": date_review_reason,
            "price_date": price_date,
            "close_usd": close,
            "secondary_market_cap_asof": candidate["market_cap_asof"],
            "secondary_market_cap_source_url": candidate["market_cap_source_url"],
            "price_to_cap_asof_gap_days": price_cap_gap_days,
            "price_to_share_count_asof_gap_days": price_share_gap_days,
            "secondary_market_cap_usd_b": float(cap) if pd.notna(cap) else None,
            "implied_shares_m_from_cap_and_close": round(implied_shares, 3) if implied_shares is not None else None,
            "reported_shares_m": reported_shares,
            "reported_shares_asof": shares["shares_asof"] if shares else "",
            "reported_shares_source_url": shares["source"] if shares else "",
            "reported_shares_note": shares.get("note", "") if shares else "",
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
