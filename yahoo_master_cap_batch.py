"""Resumable, bounded Yahoo market-cap observations for unranked KIS US master symbols.

Yahoo Finance is used only as a secondary market-cap source. This script does not
supply price history, verify market cap, or activate candidates. It processes a
small batch per run and checkpoints observations so failures can be retried.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from yahoo_market_cap_supplement import ADR_RATIO_REGISTRY, collect_yahoo_market_caps

ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "data" / "unranked_us_stock_master.csv"
OUTPUT = ROOT / "data" / "yahoo_unranked_master_market_caps.csv"
EXCHANGE_MAP = {"NAS": "NAS", "NYS": "NYS", "AMS": "AMS"}


def master_to_yahoo_input(master: pd.DataFrame) -> pd.DataFrame:
    required = {"listing_exchange", "symbol", "master_security_type", "master_dr_flag", "master_dr_country_code"}
    missing = required - set(master.columns)
    if missing:
        raise ValueError(f"Master input missing columns: {', '.join(sorted(missing))}")
    frame = master.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    frame["exchange"] = frame["listing_exchange"].astype(str).str.strip().str.upper()
    frame["market"] = "United States"
    frame["instrument_type"] = "unsupported_master_security"
    common = frame["master_security_type"].astype(str).str.strip().eq("2") & frame["master_dr_flag"].astype(str).str.strip().str.upper().ne("Y")
    adr = frame["master_dr_flag"].astype(str).str.strip().str.upper().eq("Y")
    frame.loc[common, "instrument_type"] = "equity_candidate_unverified"
    frame.loc[adr, "instrument_type"] = "adr_candidate"
    frame["discovery_dr_country_code"] = frame["master_dr_country_code"].fillna("").astype(str).str.strip()
    return frame[["symbol", "market", "exchange", "instrument_type", "discovery_dr_country_code"]].drop_duplicates("symbol")


def collect_bounded_batch(
    master: pd.DataFrame,
    previous: pd.DataFrame | None = None,
    batch_size: int = 100,
    ticker_factory=None,
    adr_ratio_registry: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    inputs = master_to_yahoo_input(master)
    if previous is None:
        previous = pd.DataFrame()
    completed = set()
    if not previous.empty and {"symbol", "observation_status"}.issubset(previous.columns):
        # Retry only explicit failures; successful observations and confirmed no-cap
        # responses remain checkpointed to limit repeated provider calls.
        completed = set(previous.loc[~previous["observation_status"].isin(["request_failed", "not_observed"]), "symbol"].astype(str).str.upper())
    eligible = inputs[
        inputs["instrument_type"].eq("equity_candidate_unverified")
        & inputs["exchange"].isin(EXCHANGE_MAP)
        & ~inputs["symbol"].isin(completed)
    ].copy()
    # ADRs are queried only when an issuer/official-source ratio is confirmed.
    # Keep other ADR master rows pending rather than repeatedly selecting rows
    # that the downstream safe collector intentionally rejects.
    if adr_ratio_registry is not None and {"symbol", "status"}.issubset(adr_ratio_registry.columns):
        confirmed_adrs = set(
            adr_ratio_registry.loc[
                adr_ratio_registry["status"].astype(str).str.strip().str.lower().eq("official_source_confirmed"),
                "symbol",
            ].astype(str).str.strip().str.upper()
        )
        eligible_adrs = inputs[
            inputs["instrument_type"].eq("adr_candidate")
            & inputs["exchange"].isin(EXCHANGE_MAP)
            & inputs["symbol"].isin(confirmed_adrs)
            & ~inputs["symbol"].isin(completed)
        ]
        eligible = pd.concat([eligible, eligible_adrs], ignore_index=True).drop_duplicates("symbol")
    # Interleave exchange queues so a large alphabetical exchange segment does
    # not monopolize every run. Previously completed symbols are removed first.
    if not eligible.empty:
        eligible["_exchange_order"] = eligible["exchange"].map({"NAS": 0, "NYS": 1, "AMS": 2}).fillna(9)
        eligible["_within_exchange"] = eligible.groupby("exchange").cumcount()
        eligible = eligible.sort_values(["_within_exchange", "_exchange_order", "symbol"])
        eligible = eligible.drop(columns=["_exchange_order", "_within_exchange"])
    batch = eligible.head(batch_size)
    if batch.empty:
        return previous.copy(), {"eligible_remaining": 0, "processed_this_run": 0, "observations_total": len(previous)}
    fresh = collect_yahoo_market_caps(
        batch,
        ticker_factory=ticker_factory,
        adr_ratio_registry=adr_ratio_registry,
    )
    combined = pd.concat([previous, fresh], ignore_index=True) if not previous.empty else fresh
    combined["symbol"] = combined["symbol"].astype(str).str.upper()
    combined = combined.drop_duplicates("symbol", keep="last")
    remaining = max(0, len(eligible) - len(batch))
    return combined, {"eligible_remaining": remaining, "processed_this_run": len(batch), "observations_total": len(combined)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=MASTER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    master = pd.read_csv(args.master, dtype=str, keep_default_na=False)
    previous = pd.read_csv(args.output, dtype=str, keep_default_na=False) if args.output.exists() else pd.DataFrame()
    registry = pd.read_csv(ADR_RATIO_REGISTRY, dtype=str, keep_default_na=False) if ADR_RATIO_REGISTRY.exists() else pd.DataFrame()
    report, stats = collect_bounded_batch(master, previous, args.batch_size, adr_ratio_registry=registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"Yahoo secondary cap batch: {stats['processed_this_run']} processed; {stats['eligible_remaining']} eligible remain; {stats['observations_total']} observations stored; output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
