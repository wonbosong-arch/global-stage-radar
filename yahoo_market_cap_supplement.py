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
ADR_RATIO_REGISTRY = ROOT / "data" / "adr_ratio_primary_source_registry.csv"


def yahoo_ticker_symbol(symbol: str) -> str:
    """Translate canonical slash-delimited share classes to Yahoo's hyphen format."""
    return str(symbol).strip().upper().replace("/", "-")


def collect_yahoo_market_caps(
    candidates: pd.DataFrame,
    ticker_factory: Callable[[str], object] | None = None,
    fetched_at_utc: str | None = None,
    adr_ratio_registry: pd.DataFrame | None = None,
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
    us_listing = (
        frame["market"].isin({"united states", "us", "usa"})
        & frame["exchange"].isin({"NAS", "NYS", "AMS"})
    )
    common_types = {
        "common_stock_candidate", "common_stock_candidate_unverified",
        "common_stock", "equity_candidate_unverified",
    }
    common = frame[us_listing & frame["instrument_type"].isin(common_types)].copy()
    # "equity_candidate_unverified" is not itself an ADR classification, but
    # separate depositary evidence must keep likely ADRs out of the common-stock path.
    if "discovery_dr_country_code" in common.columns:
        common = common[
            common["discovery_dr_country_code"].fillna("").astype(str).str.strip().eq("")
        ]
    if "depositary_ratio_status" in common.columns:
        ratio_status = common["depositary_ratio_status"].fillna("").astype(str).str.strip().str.lower()
        common = common[ratio_status.isin({"", "not_applicable", "not_required"})]

    adr_registry_by_symbol = {}
    if adr_ratio_registry is not None and {"symbol", "status", "depositary_ratio_observed", "depositary_ratio_basis", "depositary_ratio_source_url"}.issubset(adr_ratio_registry.columns):
        confirmed = adr_ratio_registry[adr_ratio_registry["status"].astype(str).str.strip().str.lower().eq("official_source_confirmed")]
        adr_registry_by_symbol = {str(row["symbol"]).strip().upper(): row for _, row in confirmed.iterrows()}
    adr = frame[us_listing & frame["instrument_type"].isin({"adr_candidate", "adr", "american_depositary_receipt"})].copy()
    if "discovery_dr_country_code" in adr.columns:
        adr = adr[adr["discovery_dr_country_code"].fillna("").astype(str).str.strip().ne("")]
    adr = adr[adr["symbol"].isin(adr_registry_by_symbol)]
    eligible = pd.concat([common, adr], ignore_index=True).drop_duplicates("symbol")

    for item in eligible.itertuples(index=False):
        symbol = str(item.symbol).strip().upper()
        yahoo_symbol = yahoo_ticker_symbol(symbol)
        row: dict[str, object] = {
            "symbol": symbol,
            "market_cap_usd_b_secondary": "",
            "market_cap_native": "",
            "market_cap_currency": "",
            "market_cap_asof": "",
            "market_cap_asof_basis": "not_provided_by_yahoo",
            "source": "Yahoo Finance",
            "source_url": f"https://finance.yahoo.com/quote/{yahoo_symbol}/",
            "fetched_at_utc": fetched_at_utc,
            "quote_type": "",
            "exchange_name": "",
            "market_cap_status": "not_verified",
            "depositary_ratio_status": "verified" if symbol in adr_registry_by_symbol else "not_applicable",
            "depositary_ratio_observed": str(adr_registry_by_symbol[symbol]["depositary_ratio_observed"]) if symbol in adr_registry_by_symbol else "",
            "depositary_ratio_basis": str(adr_registry_by_symbol[symbol]["depositary_ratio_basis"]) if symbol in adr_registry_by_symbol else "",
            "depositary_ratio_source_url": str(adr_registry_by_symbol[symbol]["depositary_ratio_source_url"]) if symbol in adr_registry_by_symbol else "",
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
            # Yahoo's regularMarketTime is a quote timestamp, not an explicit
            # effective date for its market-cap field. Do not infer cap dates from it.
        except Exception as exc:
            row["observation_status"] = "request_failed"
            row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        rows.append(row)

    columns = [
        "symbol", "market_cap_usd_b_secondary", "market_cap_native", "market_cap_currency",
        "market_cap_asof", "market_cap_asof_basis", "source", "source_url", "fetched_at_utc", "quote_type",
        "exchange_name", "market_cap_status", "depositary_ratio_status", "depositary_ratio_observed",
        "depositary_ratio_basis", "depositary_ratio_source_url", "observation_status", "error",
    ]
    return pd.DataFrame(rows, columns=columns)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=CANDIDATES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    candidates = pd.read_csv(args.input, dtype=str, keep_default_na=False)
    adr_registry = pd.read_csv(ADR_RATIO_REGISTRY, dtype={"symbol": str}) if ADR_RATIO_REGISTRY.exists() else pd.DataFrame()
    report = collect_yahoo_market_caps(candidates, adr_ratio_registry=adr_registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"Yahoo market-cap observations: {len(report)}; USD values: {int(report['market_cap_usd_b_secondary'].astype(str).str.strip().ne('').sum())}; output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
