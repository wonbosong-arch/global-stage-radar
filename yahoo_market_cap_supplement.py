"""Collect Yahoo Finance market-cap observations as secondary evidence only.

This module never updates the candidate universe, verifies capitalization, or
activates symbols. It handles US-listed common-stock candidates, including
unverified equity candidates that have no ADR evidence. ADRs, ETFs, and non-USD
listings remain outside this first safe implementation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

ROOT = Path(__file__).resolve().parent
CANDIDATES = ROOT / "data" / "stock_universe_candidates.csv"
OUTPUT = ROOT / "data" / "yahoo_market_cap_supplement.csv"


def yahoo_ticker_symbol(symbol: str) -> str:
    """Translate canonical slash-delimited share classes to Yahoo's hyphen format."""
    return str(symbol).strip().upper().replace("/", "-")


def collect_yahoo_market_caps(
    candidates: pd.DataFrame,
    ticker_factory: Callable[[str], object] | None = None,
    fetched_at_utc: str | None = None,
) -> pd.DataFrame:
    """Return secondary market-cap observations without mutating candidates."""
    if ticker_factory is None:
        import yfinance as yf
        ticker_factory = yf.Ticker

    required = {"symbol", "market", "exchange", "instrument_type"}
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(f"Candidate input missing columns: {', '.join(sorted(missing))}")

    fetched_at_utc = fetched_at_utc or datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, object]] = []
    frame = candidates.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    frame["market"] = frame["market"].astype(str).str.strip().str.lower()
    frame["exchange"] = frame["exchange"].astype(str).str.strip().str.upper()
    frame["instrument_type"] = frame["instrument_type"].astype(str).str.strip().str.lower()
    eligible = frame[
        frame["market"].isin({"united states", "us", "usa"})
        & frame["exchange"].isin({"NAS", "NYS", "AMS"})
        & frame["instrument_type"].isin({
            "common_stock_candidate", "common_stock_candidate_unverified",
            "common_stock", "equity_candidate_unverified",
        })
    ].copy()
    # "equity_candidate_unverified" is a normal discovery status, not an ADR
    # classification. Include it unless separate discovery/depositary evidence
    # says it may be a depositary receipt.
    if "discovery_dr_country_code" in eligible.columns:
        eligible = eligible[
            eligible["discovery_dr_country_code"].fillna("").astype(str).str.strip().eq("")
        ]
    if "depositary_ratio_status" in eligible.columns:
        ratio_status = eligible["depositary_ratio_status"].fillna("").astype(str).str.strip().str.lower()
        eligible = eligible[ratio_status.isin({"", "not_applicable", "not_required"})]
    eligible = eligible.drop_duplicates("symbol")

    for item in eligible.itertuples(index=False):
        symbol = str(item.symbol).strip().upper()
        yahoo_symbol = yahoo_ticker_symbol(symbol)
        row: dict[str, object] = {
            "symbol": symbol,
            "market_cap_usd_b_secondary": "",
            "market_cap_native": "",
            "market_cap_currency": "",
            "market_cap_asof": "",
            "source": "Yahoo Finance",
            "source_url": f"https://finance.yahoo.com/quote/{yahoo_symbol}/",
            "fetched_at_utc": fetched_at_utc,
            "quote_type": "",
            "exchange_name": "",
            "market_cap_status": "not_verified",
            "observation_status": "not_observed",
            "error": "",
        }
        try:
            info = ticker_factory(yahoo_symbol).get_info()
            if not isinstance(info, dict):
                raise ValueError("Yahoo quote response was not a dictionary")
            row["market_cap_currency"] = str(info.get("currency") or "").upper()
            row["quote_type"] = str(info.get("quoteType") or "")
            row["exchange_name"] = str(info.get("fullExchangeName") or info.get("exchange") or "")
            market_cap = info.get("marketCap")
            if market_cap is not None:
                numeric_cap = float(market_cap)
                if numeric_cap > 0:
                    row["market_cap_native"] = numeric_cap
                    if row["market_cap_currency"] == "USD":
                        row["market_cap_usd_b_secondary"] = numeric_cap / 1_000_000_000
                        row["observation_status"] = "observed_usd"
                    else:
                        row["observation_status"] = "observed_non_usd_not_converted"
                else:
                    row["observation_status"] = "invalid_market_cap"
            else:
                row["observation_status"] = "market_cap_missing"
            timestamp = info.get("regularMarketTime")
            if timestamp:
                try:
                    row["market_cap_asof"] = datetime.fromtimestamp(int(timestamp), timezone.utc).date().isoformat()
                except (ValueError, TypeError, OSError, OverflowError):
                    row["market_cap_asof"] = ""
        except Exception as exc:
            row["observation_status"] = "request_failed"
            row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        rows.append(row)

    columns = [
        "symbol", "market_cap_usd_b_secondary", "market_cap_native", "market_cap_currency",
        "market_cap_asof", "source", "source_url", "fetched_at_utc", "quote_type",
        "exchange_name", "market_cap_status", "observation_status", "error",
    ]
    return pd.DataFrame(rows, columns=columns)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=CANDIDATES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    candidates = pd.read_csv(args.input, dtype=str, keep_default_na=False)
    report = collect_yahoo_market_caps(candidates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"Yahoo market-cap observations: {len(report)}; USD values: {int(report['market_cap_usd_b_secondary'].astype(str).str.strip().ne('').sum())}; output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
