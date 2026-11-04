"""Offline queue/freshness warnings for an explicit Stage-plan review cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from candidate_refresh_state import collection_plan, read_collection_status


def audit_queue(candidates, universe, prices, status, symbols, as_of, batch_sizes=()):
    """Replay existing selection only; a batch estimate is never a refresh promise."""
    now = pd.Timestamp(as_of)
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    candidates = candidates.copy()
    candidates["symbol"] = candidates.symbol.str.strip().str.upper()
    eligible = candidates[candidates.activation_status.eq("pending_review") &
                          ~candidates.symbol.isin(universe.symbol.str.strip().str.upper())].drop_duplicates("symbol")
    plan, state, skipped = collection_plan(eligible, prices, status, now)
    positions = {s: i + 1 for i, s in enumerate(plan.symbol)}
    latest = prices.groupby("symbol").date.max().to_dict()
    rows = []
    sizes = sorted(set(batch_sizes))
    if any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in sizes):
        raise ValueError("Observed batch sizes must be positive integers")
    for symbol in sorted(set(symbols)):
        session = latest.get(symbol)
        deadline = (pd.Timestamp(session) + pd.Timedelta(days=7)).date().isoformat() if session else None
        position = positions.get(symbol)
        rows.append({"symbol": symbol, "queue_position": position,
                     "queue_status": "cooldown" if symbol in skipped else "eligible" if position else "excluded",
                     "last_attempt_at_utc": state.get(symbol, {}).get("last_attempt_at_utc"),
                     "latest_stored_session": session, "fresh_through": deadline,
                     "freshness_warning": "missing" if not deadline else "expired" if now.date().isoformat() > deadline else "expires_within_1_day" if (pd.Timestamp(deadline).date() - now.date()).days <= 1 else "within_7_days",
                     "deferred_in_last_run": symbol in status.get("deferred_symbols", []),
                     "response_in_last_run": symbol in status.get("fresh_data_symbols", []),
                     "estimated_successful_runs": {str(n): math.ceil(position / n) for n in sizes} if position else {}})
    return {"policy": "offline review only; unchanged queue; estimates assume unchanged order and observed throughput, not successful fresh bars",
            "as_of": now.isoformat(), "eligible_count": len(eligible), "queue_count": len(plan),
            "cohort_count": len(rows), "last_run_finished_at_utc": status.get("finished_at_utc"),
            "last_run_attempted_count": status.get("attempted_symbol_count"),
            "warning": "Run success and response presence do not prove latest-session freshness; deferred cohorts have no daily refresh guarantee.",
            "candidates": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    parser.add_argument("--cohort", type=Path, required=True, help="JSON output/packet from us_stage_connection_plan.py")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--observed-batch-size", type=int, action="append", default=[])
    args = parser.parse_args()
    data = args.data_dir
    names = ["stock_universe_candidates.csv", "monitoring_universe.csv", "candidate_daily_prices.csv", "candidate_daily_prices_status.json"]
    inputs = {name: hashlib.sha256((data / name).read_bytes()).hexdigest() for name in names}
    status = read_collection_status(data / names[3], data / names[2])
    if not status:
        raise ValueError("Scheduling status invalid or snapshot digest mismatch; use exact repository LF bytes")
    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    read = lambda name: pd.read_csv(data / name, dtype=str, keep_default_na=False)
    result = audit_queue(read(names[0]), read(names[1]), read(names[2]), status,
                         [r["symbol"] for r in cohort["candidates"]], args.as_of, args.observed_batch_size)
    result["input_sha256"] = inputs
    result["cohort_sha256"] = hashlib.sha256(args.cohort.read_bytes()).hexdigest()
    result["cohort_as_of"] = cohort.get("as_of")
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
