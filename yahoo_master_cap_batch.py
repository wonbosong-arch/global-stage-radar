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
REVIEW_OUTPUT = ROOT / "data" / "yahoo_master_cap_triage.csv"
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
    # Fresh symbols take priority over retries so persistent Yahoo failures do
    # not occupy a slot on every run and delay coverage of the remaining master.
    failed_symbols = set()
    if not previous.empty and {"symbol", "observation_status"}.issubset(previous.columns):
        failed_symbols = set(
            previous.loc[
                previous["observation_status"].isin(["request_failed", "not_observed"]),
                "symbol",
            ].astype(str).str.upper()
        )
    if not eligible.empty:
        eligible["_retry_priority"] = eligible["symbol"].isin(failed_symbols).astype(int)
        eligible["_exchange_order"] = eligible["exchange"].map({"NAS": 0, "NYS": 1, "AMS": 2}).fillna(9)
        eligible["_within_exchange"] = eligible.groupby("exchange").cumcount()
        eligible = eligible.sort_values(
            ["_retry_priority", "_within_exchange", "_exchange_order", "symbol"]
        )
        eligible = eligible.drop(columns=["_retry_priority", "_exchange_order", "_within_exchange"])
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


def build_cap_triage(observations: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """Create a review queue; observations never become verified or activated here."""
    if observations.empty:
        return pd.DataFrame(columns=["symbol", "market_cap_usd_b_secondary", "quote_type", "exchange_name", "observation_status", "triage_status", "triage_reason"])
    frame = observations.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    master_frame = master.copy()
    master_frame["symbol"] = master_frame["symbol"].astype(str).str.strip().str.upper()
    master_frame["master_security_type"] = master_frame["master_security_type"].astype(str).str.strip()
    master_frame["master_dr_flag"] = master_frame["master_dr_flag"].astype(str).str.strip().str.upper()
    meta = master_frame.drop_duplicates("symbol").set_index("symbol")
    statuses, reasons, cap_threshold_reviews = [], [], []
    for row in frame.itertuples(index=False):
        symbol = str(getattr(row, "symbol", "")).upper()
        quote_type = str(getattr(row, "quote_type", "")).strip().upper()
        exchange_name = str(getattr(row, "exchange_name", "")).strip().lower()
        observation_status = str(getattr(row, "observation_status", "")).strip().lower()
        try:
            cap = float(getattr(row, "market_cap_usd_b_secondary", ""))
        except (TypeError, ValueError):
            cap = float("nan")
        master_row = meta.loc[symbol] if symbol in meta.index else None

        # Keep the size screen independent from identity/type review. A large
        # observed cap should remain visible for follow-up even when listing
        # venue or instrument identity is not yet reconciled.
        if observation_status != "observed_usd" or not pd.notna(cap):
            cap_review = "cap_unverified"
        elif cap >= 1:
            cap_review = "observed_ge_1b_review_only"
        else:
            cap_review = "observed_lt_1b_review_only"
        cap_threshold_reviews.append(cap_review)

        if master_row is None:
            status, reason = "identity_review_required", "Symbol missing from KIS master inventory"
        elif master_row["master_dr_flag"] == "Y":
            status, reason = "adr_review_required", "ADR requires official ratio and issuer identity confirmation"
        elif master_row["master_security_type"] != "2" or quote_type != "EQUITY":
            status, reason = "instrument_type_review_required", "KIS master type or Yahoo quote type is not ordinary equity"
        elif not any(x in exchange_name for x in ("nasdaq", "new york stock exchange", "nyse", "american")):
            status, reason = "listing_identity_review_required", "Yahoo listing venue does not clearly match expected US primary listing"
        elif observation_status != "observed_usd" or not pd.notna(cap):
            status, reason = "market_cap_unknown", "No usable USD market-cap observation"
        elif cap >= 1:
            status, reason = "priority_review_cap_ge_1b", "Observed cap is at least USD 1B; source date and identity still require confirmation"
        else:
            status, reason = "priority_review_cap_lt_1b", "Observed cap is below USD 1B; exclude only after independent verification"
        statuses.append(status)
        reasons.append(reason)
    frame["triage_status"] = statuses
    frame["triage_reason"] = reasons
    frame["cap_threshold_review"] = cap_threshold_reviews
    columns = ["symbol", "market_cap_usd_b_secondary", "quote_type", "exchange_name", "observation_status", "market_cap_asof", "market_cap_asof_basis", "source_url", "fetched_at_utc", "triage_status", "triage_reason", "cap_threshold_review"]
    return frame[[c for c in columns if c in frame.columns]].sort_values(["triage_status", "symbol"]).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=MASTER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()
    master = pd.read_csv(args.master, dtype=str, keep_default_na=False)
    previous = pd.read_csv(args.output, dtype=str, keep_default_na=False) if args.output.exists() else pd.DataFrame()
    registry = pd.read_csv(ADR_RATIO_REGISTRY, dtype=str, keep_default_na=False) if ADR_RATIO_REGISTRY.exists() else pd.DataFrame()
    report, stats = collect_bounded_batch(master, previous, args.batch_size, adr_ratio_registry=registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    triage = build_cap_triage(report, master)
    REVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    triage.to_csv(REVIEW_OUTPUT, index=False)
    print(f"Yahoo secondary cap batch: {stats['processed_this_run']} processed; {stats['eligible_remaining']} eligible remain; {stats['observations_total']} observations stored; output={args.output}; triage={REVIEW_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
