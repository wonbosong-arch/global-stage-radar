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
ADR_RATIO_EVIDENCE = ROOT / "data" / "yahoo_market_cap_supplement.csv"

# Shares in millions, transcribed from the cited issuer filings; effective dates
# are retained because a dated filing share count is not the same as current shares.
OFFICIAL_SHARE_COUNTS = {
    "NVDA": {
        "shares_m": 24100.0,
        "shares_asof": "2026-08-21",
        "source": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm",
        "note": "Latest Q2 FY2027 Form 10-Q states 24.1 billion common shares outstanding as of August 21, 2026; rounded as reported.",
    },
    "AAPL": {
        "shares_m": 14594.180,
        "shares_asof": "2026-07-17",
        "source": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm",
        "note": "Q3 FY2026 Form 10-Q reports 14,594,180,000 common shares outstanding as of July 17, 2026.",
    },
    "MSFT": {
        "shares_m": 7425.545491,
        "shares_asof": "2026-07-23",
        "source": "https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm",
        "note": "FY2026 Form 10-K reports 7,425,545,491 common shares outstanding as of July 23, 2026.",
    },
    "AMZN": {
        "shares_m": 10786.313572,
        "shares_asof": "2026-07-22",
        "source": "https://www.sec.gov/Archives/edgar/data/1018724/000101872426000026/amzn-20260630.htm",
        "note": "Q2 2026 Form 10-Q reports 10,786,313,572 common shares outstanding as of July 22, 2026.",
    },
    "META": {
        "shares_m": 2547.506225,
        "shares_asof": "2026-07-24",
        "source": "https://www.sec.gov/Archives/edgar/data/1326801/000162828026050705/meta-20260630.htm",
        "note": "Combined Class A (2,205,128,509) and Class B (342,377,716) shares outstanding as of July 24, 2026; total company shares for a multi-class issuer.",
    },
    "AVGO": {
        "shares_m": 4773.629865,
        "shares_asof": "2026-08-28",
        "source": "https://www.sec.gov/Archives/edgar/data/1730168/000173016826000080/avgo-20260802.htm",
        "note": "Q3 FY2026 Form 10-Q reports 4,773,629,865 common shares outstanding as of August 28, 2026.",
    },
    "TSLA": {
        "shares_m": 3952.757946,
        "shares_asof": "2026-10-15",
        "source": "https://www.sec.gov/Archives/edgar/data/1318605/000162828026066775/tsla-20260930.htm",
        "note": "Q3 2026 Form 10-Q reports 3,952,757,946 common shares outstanding as of October 15, 2026.",
    },
    "LLY": {
        "shares_m": 941.357065,
        "shares_asof": "2026-08-03",
        "source": "https://www.sec.gov/Archives/edgar/data/59478/000005947826000081/lly-20260630.htm",
        "note": "Q2 2026 Form 10-Q reports 941,357,065 common shares outstanding as of August 3, 2026.",
    },
    "MU": {
        "shares_m": 1131.423212,
        "shares_asof": "2026-10-02",
        "source": "https://www.sec.gov/Archives/edgar/data/723125/000072312526000023/mu-20260903.htm",
        "note": "FY2026 Form 10-K reports 1,131,423,212 common shares outstanding as of October 2, 2026.",
    },
    "ORCL": {
        "shares_m": 2880.471,
        "shares_asof": "2026-06-12",
        "source": "https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm",
    },
    "CRM": {
        "shares_m": 823.0,
        "shares_asof": "2026-08-20",
        "source": "https://www.sec.gov/Archives/edgar/data/1108524/000110852426000190/crm-20260731.htm",
        "note": "Latest 10-Q reports approximately 823 million common shares outstanding as of August 20, 2026; this replaces the older February 2026 count.",
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
        "shares_m": 997.689626,
        "shares_asof": "2026-08-18",
        "source": "https://www.sec.gov/Archives/edgar/data/354950/000162828026058715/hd-20260802.htm",
        "note": "Latest Q2 FY2026 10-Q reports 997,689,626 shares outstanding as of August 18, 2026; replaces the March share count.",
    },
    "BAC": {
        "shares_m": 6992.748365,
        "shares_asof": "2026-07-30",
        "source": "https://www.sec.gov/Archives/edgar/data/70858/000007085826000394/bac-20260630.htm",
        "note": "Latest Q2 2026 10-Q reports 6,992,748,365 common shares outstanding as of July 30, 2026; replaces the February share count.",
    },
    "AMGN": {
        "shares_m": 540.632005,
        "shares_asof": "2026-07-30",
        "source": "https://www.sec.gov/Archives/edgar/data/318154/000031815426000126/amgn-20260630.htm",
        "note": "Latest 10-Q reports 540,632,005 common shares outstanding as of July 30, 2026; replaces the February 2026 share count.",
    },
    "SBUX": {
        "shares_m": 1140.0,
        "shares_asof": "2026-07-23",
        "source": "https://www.sec.gov/Archives/edgar/data/829224/000082922426000130/sbux-20260628.htm",
    },
    "NFLX": {
        "shares_m": 4106.325903,
        "shares_asof": "2026-09-30",
        "source": "https://www.sec.gov/Archives/edgar/data/1065280/000106528026000291/nflx-20260930.htm",
        "note": "Latest Q3 2026 10-Q reports 4,106,325,903 common shares outstanding as of September 30, 2026; replaces the year-end 2025 count.",
    },
    "WELL": {
        "shares_m": 720.744951,
        "shares_asof": "2026-07-24",
        "source": "https://www.sec.gov/Archives/edgar/data/766704/000076670426000030/well-20260630.htm",
        "note": "Latest Q2 2026 10-Q reports 720,744,951 common shares outstanding as of July 24, 2026; replaces the February share count.",
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


def build_report(
    candidates: pd.DataFrame,
    prices: pd.DataFrame,
    ratio_evidence: pd.DataFrame | None = None,
) -> pd.DataFrame:
    c = candidates.copy()
    p = prices.copy()
    for col in ("symbol", "market_cap_usd_b_secondary", "market_cap_asof", "market_cap_status", "market_cap_source_url", "instrument_type"):
        if col not in c:
            c[col] = ""
    for col in ("symbol", "date", "close"):
        if col not in p:
            p[col] = ""
    p["date"] = pd.to_datetime(p["date"], errors="coerce")
    p["close"] = pd.to_numeric(p["close"], errors="coerce")
    p = p.dropna(subset=["date", "close"])
    p["symbol"] = p["symbol"].astype(str).str.strip().str.upper()
    price_groups = {symbol: group.sort_values("date") for symbol, group in p.groupby("symbol")}
    ratio_by_symbol = {}
    if ratio_evidence is not None and not ratio_evidence.empty:
        evidence = ratio_evidence.copy()
        for col in ("symbol", "depositary_ratio_status", "depositary_ratio_observed", "depositary_ratio_source_url", "market_cap_usd_b_secondary", "market_cap_currency", "source_url", "market_cap_asof"):
            if col not in evidence:
                evidence[col] = ""
        evidence["symbol"] = evidence["symbol"].astype(str).str.strip().str.upper()
        for _, evidence_row in evidence.iterrows():
            ev_status = str(evidence_row.get("depositary_ratio_status", "")).strip().lower()
            ev_url = str(evidence_row.get("depositary_ratio_source_url", "")).strip()
            ev_ratio = pd.to_numeric(evidence_row.get("depositary_ratio_observed", ""), errors="coerce")
            if ev_status in {"verified", "official_source_confirmed", "verified_primary_source"} and ev_url and pd.notna(ev_ratio) and ev_ratio > 0:
                ratio_by_symbol[str(evidence_row["symbol"])] = evidence_row

    rows = []
    for _, candidate in c.iterrows():
        symbol = str(candidate["symbol"]).strip().upper()
        cap = pd.to_numeric(candidate["market_cap_usd_b_secondary"], errors="coerce")
        cap_asof = pd.to_datetime(candidate["market_cap_asof"], errors="coerce")
        cap_source_url = str(candidate.get("market_cap_source_url", "") or "").strip()
        # Yahoo's USD cap supplement is a fallback observation for triage only.
        # Never apply it to local-currency prices or treat it as verified cap data.
        supplemental_rows = (
            ratio_evidence[ratio_evidence["symbol"].astype(str).str.strip().str.upper() == symbol]
            if ratio_evidence is not None and not ratio_evidence.empty and "symbol" in ratio_evidence
            else pd.DataFrame()
        )
        if pd.isna(cap) and not supplemental_rows.empty and str(candidate.get("currency", "")).upper() == "USD":
            for _, cap_row in supplemental_rows.iterrows():
                supplement_currency = str(cap_row.get("market_cap_currency", "")).strip().upper()
                supplement_cap = pd.to_numeric(cap_row.get("market_cap_usd_b_secondary", ""), errors="coerce")
                if supplement_currency == "USD" and pd.notna(supplement_cap) and supplement_cap > 0:
                    cap = supplement_cap
                    if not cap_source_url:
                        cap_source_url = str(cap_row.get("source_url", "") or "").strip()
                    supplement_asof = pd.to_datetime(cap_row.get("market_cap_asof", ""), errors="coerce")
                    if pd.isna(cap_asof) and pd.notna(supplement_asof):
                        cap_asof = supplement_asof
                    break
        symbol_prices = price_groups.get(symbol)
        px = None
        if symbol_prices is not None and not symbol_prices.empty:
            if pd.notna(cap_asof):
                # Compare a dated market-cap observation with a price from the
                # same effective date where possible, otherwise the nearest
                # available prior close. This avoids using a later price move
                # to explain a cap snapshot from an earlier date.
                prior_prices = symbol_prices[symbol_prices["date"] <= cap_asof]
                if not prior_prices.empty:
                    px = prior_prices.iloc[-1]
                else:
                    px = symbol_prices.iloc[0]
            else:
                px = symbol_prices.iloc[-1]
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
        ratio_status = str(candidate.get("depositary_ratio_status", "") or "").strip()
        ratio_observed = pd.to_numeric(candidate.get("depositary_ratio_observed", ""), errors="coerce")
        ratio_source_url = str(candidate.get("depositary_ratio_source_url", "") or "").strip()
        # Candidate rows can predate the ratio-source registry. Use the separate
        # supplement only as evidence for the ratio, never as cap verification.
        supplemental_ratio = ratio_by_symbol.get(symbol)
        if supplemental_ratio is not None and (not ratio_source_url or pd.isna(ratio_observed) or ratio_observed <= 0):
            ratio_status = str(supplemental_ratio.get("depositary_ratio_status", "")).strip()
            ratio_observed = pd.to_numeric(supplemental_ratio.get("depositary_ratio_observed", ""), errors="coerce")
            ratio_source_url = str(supplemental_ratio.get("depositary_ratio_source_url", "")).strip()
        ratio_evidence_confirmed = (
            ratio_status in {"official_source_confirmed", "verified", "verified_primary_source"}
            and pd.notna(ratio_observed)
            and ratio_observed > 0
            and bool(ratio_source_url)
        )
        if candidate["instrument_type"] == "adr_candidate":
            outcome = (
                "adr_ratio_evidence_captured_share_count_review_required"
                if ratio_evidence_confirmed
                else "adr_share_class_review_required"
            )
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
        elif price_share_gap_days is not None and price_share_gap_days > 180:
            date_review_priority = "P1_stale_share_count"
            date_review_reason = "share_count_date_more_than_180_days_before_price"
        elif price_share_gap_days is not None and price_share_gap_days > 90:
            date_review_priority = "P2_date_alignment"
            date_review_reason = "share_count_date_more_than_90_days_before_price"
        elif shares is None and candidate["instrument_type"] != "adr_candidate":
            # Missing issuer share-count evidence is the main bottleneck for most
            # candidates; prioritize collecting it rather than labeling it routine.
            date_review_priority = "P2_share_count_evidence"
            date_review_reason = "official_share_count_not_captured"
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
            "secondary_market_cap_asof": cap_asof.date().isoformat() if pd.notna(cap_asof) else candidate["market_cap_asof"],
            "secondary_market_cap_source_url": cap_source_url,
            "price_to_cap_asof_gap_days": price_cap_gap_days,
            "price_to_share_count_asof_gap_days": price_share_gap_days,
            "secondary_market_cap_usd_b": float(cap) if pd.notna(cap) else None,
            "implied_shares_m_from_cap_and_close": round(implied_shares, 3) if implied_shares is not None else None,
            "reported_shares_m": reported_shares,
            "reported_shares_asof": shares["shares_asof"] if shares else "",
            "reported_shares_source_url": shares["source"] if shares else "",
            "reported_shares_note": shares.get("note", "") if shares else "",
            "depositary_ratio_status": ratio_status if candidate["instrument_type"] == "adr_candidate" else "not_applicable",
            "depositary_ratio_observed": float(ratio_observed) if pd.notna(ratio_observed) else None,
            "depositary_ratio_source_url": ratio_source_url,
            "depositary_ratio_evidence_confirmed": ratio_evidence_confirmed if candidate["instrument_type"] == "adr_candidate" else False,
            "implied_vs_reported_shares_pct": round(difference_pct, 2) if difference_pct is not None else None,
            "triage_outcome": outcome,
            "market_cap_status_remains": candidate["market_cap_status"],
            "verification_note": "Triage only; dated share count and secondary cap are not independently reconciled to an identical effective date. Never auto-verify or activate.",
        })
        report = pd.DataFrame(rows)
    # Within each review tier, surface the largest reported companies first.
    # This only prioritizes manual evidence collection; it never verifies or filters.
    report["_cap_sort"] = pd.to_numeric(report["secondary_market_cap_usd_b"], errors="coerce")
    return (
        report.sort_values(
            ["date_review_priority", "_cap_sort", "symbol"],
            ascending=[True, False, True],
            na_position="last",
            kind="stable",
        )
        .drop(columns=["_cap_sort"])
        .reset_index(drop=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--prices", type=Path, default=PRICES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--ratio-evidence", type=Path, default=ADR_RATIO_EVIDENCE)
    args = parser.parse_args()
    candidates = pd.read_csv(args.candidates, dtype=str, keep_default_na=False)
    prices = pd.read_csv(args.prices, dtype={"symbol": str})
    ratio_evidence = (
        pd.read_csv(args.ratio_evidence, dtype=str, keep_default_na=False)
        if args.ratio_evidence.exists()
        else pd.DataFrame()
    )
    report = build_report(candidates, prices, ratio_evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"rows={len(report)}")
    print("triage_outcomes=" + str(report["triage_outcome"].value_counts().to_dict()))
    print("market_cap_status_changed=0")
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
