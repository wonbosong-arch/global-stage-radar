"""Resumable, bounded Yahoo market-cap observations for unranked KIS US master symbols.

Yahoo Finance is used only as a secondary market-cap source. This script does not
supply price history, verify market cap, or activate candidates. It processes a
small batch per run and checkpoints observations so failures can be retried.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from yahoo_market_cap_supplement import ADR_RATIO_REGISTRY, collect_yahoo_market_caps
from stock_mapping import proposed_stock_mapping

ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "data" / "unranked_us_stock_master.csv"
OUTPUT = ROOT / "data" / "yahoo_unranked_master_market_caps.csv"
REVIEW_OUTPUT = ROOT / "data" / "yahoo_master_cap_triage.csv"
STATUS_OUTPUT = ROOT / "data" / "yahoo_master_cap_batch_status.json"
CANDIDATE_REVIEW_OUTPUT = ROOT / "data" / "yahoo_large_cap_candidate_review.csv"
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


def build_coverage_status(
    master: pd.DataFrame,
    observations: pd.DataFrame,
    batch_size: int,
    processed_this_run: int = 0,
) -> dict[str, object]:
    """Summarize broad-inventory progress without treating estimates as verification."""
    inputs = master_to_yahoo_input(master)
    ordinary = inputs[
        inputs["instrument_type"].eq("equity_candidate_unverified")
        & inputs["exchange"].isin(EXCHANGE_MAP)
    ]
    registry = pd.DataFrame()
    if ADR_RATIO_REGISTRY.exists():
        try:
            registry = pd.read_csv(ADR_RATIO_REGISTRY, dtype=str, keep_default_na=False)
        except (OSError, pd.errors.ParserError):
            registry = pd.DataFrame()
    all_adr_inputs = inputs[
        inputs["instrument_type"].eq("adr_candidate")
        & inputs["exchange"].isin(EXCHANGE_MAP)
    ]
    if {"symbol", "status"}.issubset(registry.columns):
        confirmed_adrs = set(
            registry.loc[
                registry["status"].astype(str).str.strip().str.lower().eq("official_source_confirmed"),
                "symbol",
            ].astype(str).str.strip().str.upper()
        )
        adr_inputs = all_adr_inputs[all_adr_inputs["symbol"].isin(confirmed_adrs)]
    else:
        confirmed_adrs = set()
        adr_inputs = inputs.iloc[0:0]
    unconfirmed_adr_inputs = all_adr_inputs[~all_adr_inputs["symbol"].isin(confirmed_adrs)]
    eligible_symbols = set(pd.concat([ordinary, adr_inputs])["symbol"].astype(str).str.upper())
    if observations.empty or "symbol" not in observations:
        observed = pd.DataFrame(columns=["symbol", "observation_status", "market_cap_usd_b_secondary"])
    else:
        observed = observations.copy()
        observed["symbol"] = observed["symbol"].astype(str).str.upper()
        observed = observed.drop_duplicates("symbol", keep="last")
    observed_statuses = observed.get("observation_status", pd.Series("", index=observed.index)).astype(str)
    completed_symbols = set(observed.loc[~observed_statuses.isin(["request_failed", "not_observed"]), "symbol"])
    covered_symbols = eligible_symbols & completed_symbols
    remaining = max(0, len(eligible_symbols - covered_symbols))
    eligible_observed = observed[observed["symbol"].isin(eligible_symbols)].copy()
    eligible_statuses = eligible_observed.get("observation_status", pd.Series("", index=eligible_observed.index)).astype(str)
    observed_usd = eligible_statuses.eq("observed_usd")
    caps = pd.to_numeric(eligible_observed.get("market_cap_usd_b_secondary", pd.Series(float("nan"), index=eligible_observed.index)), errors="coerce")
    valid_caps = observed_usd & caps.notna()
    remaining_batches = (remaining + batch_size - 1) // batch_size if batch_size > 0 else None
    return {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if remaining == 0 else "in_progress",
        "eligible_common_stock_symbols": len(ordinary),
        "eligible_confirmed_adr_symbols": len(adr_inputs),
        "adr_master_symbols_total": len(all_adr_inputs),
        "unconfirmed_adr_symbols_pending": len(unconfirmed_adr_inputs),
        "unconfirmed_adr_symbol_sample": sorted(unconfirmed_adr_inputs["symbol"].astype(str).str.upper().unique().tolist())[:20],
        "eligible_inventory_total": len(eligible_symbols),
        "observations_total": int(len(observed)),
        "eligible_symbols_with_observation": len(covered_symbols),
        "eligible_symbols_pending": remaining,
        "coverage_pct": round(100 * len(covered_symbols) / len(eligible_symbols), 2) if eligible_symbols else 100.0,
        "observed_usd_market_caps": int(valid_caps.sum()),
        "observed_cap_ge_1b": int((valid_caps & caps.ge(1)).sum()),
        "observed_cap_lt_1b": int((valid_caps & caps.lt(1)).sum()),
        "request_failures": int(eligible_statuses.isin(["request_failed", "not_observed"]).sum()),
        "processed_this_run": int(processed_this_run),
        "batch_size": int(batch_size),
        "estimated_batches_remaining": remaining_batches,
        "market_cap_status": "secondary_estimates_only_not_verified",
        "activation_status": "no_candidates_activated",
    }


def build_cap_triage(observations: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """Create a review queue; observations never become verified or activated here."""
    if observations.empty:
        return pd.DataFrame(columns=["symbol", "market_cap_usd_b_secondary", "quote_type", "exchange_name", "observation_status", "market_cap_status", "triage_status", "triage_reason"])
    frame = observations.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    master_frame = master.copy()
    master_frame["symbol"] = master_frame["symbol"].astype(str).str.strip().str.upper()
    master_frame["master_security_type"] = master_frame["master_security_type"].astype(str).str.strip()
    master_frame["master_dr_flag"] = master_frame["master_dr_flag"].astype(str).str.strip().str.upper()
    meta = master_frame.drop_duplicates("symbol").set_index("symbol")
    # Enrich the review queue with the official KIS master identity fields so
    # reviewers can triage the long tail without joining another CSV manually.
    # These fields are evidence only and never change activation or cap status.
    master_review_fields = {
        "english_name": "kis_english_name",
        "master_security_type": "kis_security_type",
        "master_dr_flag": "kis_dr_flag",
        "master_dr_country_code": "kis_dr_country_code",
        "master_industry_code": "kis_industry_code",
        "listing_exchange": "kis_listing_exchange",
    }
    for source_field, review_field in master_review_fields.items():
        if source_field in meta.columns:
            frame[review_field] = frame["symbol"].map(meta[source_field]).fillna("").astype(str)
        else:
            frame[review_field] = ""
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
    columns = [
        "symbol", "kis_english_name", "kis_listing_exchange", "kis_security_type",
        "kis_dr_flag", "kis_dr_country_code", "kis_industry_code",
        "market_cap_usd_b_secondary", "quote_type", "exchange_name",
        "observation_status", "market_cap_status", "market_cap_asof",
        "market_cap_asof_basis", "source_url", "fetched_at_utc",
        "triage_status", "triage_reason", "cap_threshold_review",
    ]
    return frame[[c for c in columns if c in frame.columns]].sort_values(["triage_status", "symbol"]).reset_index(drop=True)




def build_large_cap_candidate_review_queue(triage: pd.DataFrame) -> pd.DataFrame:
    """Return large-cap ordinary-equity rows for manual review only."""
    columns = ["symbol", "name", "exchange", "instrument_type", "proposed_market", "market_benchmark",
               "sector", "sector_benchmark", "mapping_status", "mapping_note",
               "identity_status", "market_cap_status", "provider_status", "activation_status",
               "discovery_market_cap_usd_b_secondary", "market_cap_source_url",
               "market_cap_asof", "market_cap_asof_basis", "fetched_at_utc", "review_reason"]
    if triage.empty:
        return pd.DataFrame(columns=columns)
    d = triage.copy()
    for col in ["symbol", "kis_security_type", "kis_dr_flag", "quote_type", "triage_status", "kis_listing_exchange"]:
        if col not in d:
            d[col] = ""
        d[col] = d[col].fillna("").astype(str).str.strip()
    cap = pd.to_numeric(d.get("market_cap_usd_b_secondary", pd.Series(index=d.index, dtype=float)), errors="coerce")
    d = d.loc[d["triage_status"].eq("priority_review_cap_ge_1b") & d["kis_security_type"].eq("2")
              & ~d["kis_dr_flag"].str.upper().eq("Y") & d["quote_type"].str.upper().eq("EQUITY") & cap.ge(1)].copy()
    if d.empty:
        return pd.DataFrame(columns=columns)
    cap = pd.to_numeric(d["market_cap_usd_b_secondary"], errors="coerce")
    names = d.get("kis_english_name", pd.Series("", index=d.index)).fillna("").astype(str)
    adr_name_pattern = r"\b(ADR|ADS|DEPOSITARY|DEPOSITORY|SPONSORED ADR|SPON ADS|EACH REP)\b"
    possible_adr = names.str.upper().str.contains(adr_name_pattern, regex=True, na=False)
    mappings = [
        proposed_stock_mapping(s, e, country)
        for s, e, country in zip(
            d["symbol"], d["kis_listing_exchange"],
            d.get("kis_dr_country_code", pd.Series("", index=d.index)).fillna("").astype(str),
        )
    ]
    out = pd.DataFrame({
        "symbol": d["symbol"].str.upper(),
        "name": d.get("kis_english_name", pd.Series("", index=d.index)).fillna("").astype(str),
        "exchange": d["kis_listing_exchange"],
        "instrument_type": ["possible_adr_or_equity_review" if flag else "equity_candidate_unverified" for flag in possible_adr],
        "proposed_market": [m.get("proposed_market", "") for m in mappings],
        "market_benchmark": [m.get("proposed_market_benchmark", "") for m in mappings],
        "sector": [m.get("proposed_sector", "") for m in mappings],
        "sector_benchmark": [m.get("proposed_sector_benchmark", "") for m in mappings],
        "mapping_status": [m.get("mapping_status", "") for m in mappings],
        "mapping_note": [m.get("mapping_note", "") for m in mappings],
        "identity_status": ["possible_adr_review_required" if flag else "review_required" for flag in possible_adr], "market_cap_status": "not_verified",
        "provider_status": "not_checked", "activation_status": "pending_review",
        "discovery_market_cap_usd_b_secondary": cap,
        "market_cap_source_url": d.get("source_url", pd.Series("", index=d.index)).fillna("").astype(str),
        "market_cap_asof": d.get("market_cap_asof", pd.Series("", index=d.index)).fillna("").astype(str),
        "market_cap_asof_basis": d.get("market_cap_asof_basis", pd.Series("", index=d.index)).fillna("").astype(str),
        "fetched_at_utc": d.get("fetched_at_utc", pd.Series("", index=d.index)).fillna("").astype(str),
        "review_reason": ["Issuer master name contains ADR/ADS/depositary wording; verify security type and issuer before classification" if flag else "First-pass screen only; identity, market-cap date, provider, and mapping require review" for flag in possible_adr],
    })
    return out[columns].sort_values(["discovery_market_cap_usd_b_secondary", "symbol"], ascending=[False, True]).reset_index(drop=True)


def collect_multiple_batches(
    master: pd.DataFrame,
    previous: pd.DataFrame | None = None,
    batch_size: int = 200,
    batches_per_run: int = 1,
    adr_ratio_registry: pd.DataFrame | None = None,
    collector=collect_bounded_batch,
) -> tuple[pd.DataFrame, dict[str, int], int]:
    """Run a small bounded number of sequential batches, preserving each checkpoint."""
    if batches_per_run < 1 or batches_per_run > 4:
        raise ValueError("batches_per_run must be between 1 and 4")
    report = previous.copy() if previous is not None else pd.DataFrame()
    processed_total = 0
    batches_completed = 0
    stats: dict[str, int] = {}
    for _ in range(batches_per_run):
        report, stats = collector(
            master, report, batch_size, adr_ratio_registry=adr_ratio_registry
        )
        processed = int(stats.get("processed_this_run", 0))
        processed_total += processed
        if processed == 0:
            break
        batches_completed += 1
    stats = dict(stats)
    stats["processed_this_run"] = processed_total
    return report, stats, batches_completed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=MASTER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--batches-per-run", type=int, default=1, help="Number of sequential checkpointed batches to process")
    args = parser.parse_args()
    if args.batches_per_run < 1 or args.batches_per_run > 4:
        parser.error("--batches-per-run must be between 1 and 4")
    master = pd.read_csv(args.master, dtype=str, keep_default_na=False)
    previous = pd.read_csv(args.output, dtype=str, keep_default_na=False) if args.output.exists() else pd.DataFrame()
    registry = pd.read_csv(ADR_RATIO_REGISTRY, dtype=str, keep_default_na=False) if ADR_RATIO_REGISTRY.exists() else pd.DataFrame()
    report, stats, batches_completed = collect_multiple_batches(
        master, previous, args.batch_size, args.batches_per_run, registry
    )
    processed_total = int(stats["processed_this_run"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    triage = build_cap_triage(report, master)
    REVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    triage.to_csv(REVIEW_OUTPUT, index=False)
    candidate_review = build_large_cap_candidate_review_queue(triage)
    CANDIDATE_REVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    candidate_review.to_csv(CANDIDATE_REVIEW_OUTPUT, index=False)
    status = build_coverage_status(master, report, args.batch_size, processed_total)
    status["large_cap_candidate_review_queue_rows"] = int(len(candidate_review))
    status["large_cap_candidate_review_queue_path"] = str(CANDIDATE_REVIEW_OUTPUT.relative_to(ROOT))
    status["batches_completed_this_run"] = batches_completed
    status["batches_requested_this_run"] = args.batches_per_run
    STATUS_OUTPUT.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Yahoo secondary cap batch: {processed_total} processed across {batches_completed} batches; "
        f"{status['eligible_symbols_pending']} eligible symbols pending; "
        f"{status['coverage_pct']}% inventory coverage; "
        f"estimated batches remaining={status['estimated_batches_remaining']}; "
        f"{stats['observations_total']} observations stored; output={args.output}; "
        f"triage={REVIEW_OUTPUT}; status={STATUS_OUTPUT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
