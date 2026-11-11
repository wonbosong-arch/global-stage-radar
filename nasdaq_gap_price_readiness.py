"""Offline saved-price inventory for the existing Nasdaq P1 review cohort.

No collection, candidate intake, Stage labels, approval, or output-file writes.
Saved OHLCV has no venue/provider columns: ticker presence cannot prove identity
or current KIS support. Default console output contains aggregate counts only.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from market_data import PRICE_COLUMNS, completed_bar_cutoff_date, filter_incomplete_daily_bars
from nasdaq_coverage_gap_audit import ROOT, SEC_REGISTRY, audit_gap
from us_stage_connection_plan import OfflineStageReplay

P1 = "P1_kis_name_coherent_primary_evidence_pending"


def price_inventory(gap_report: dict, prices: pd.DataFrame,
                    evaluated_at: datetime) -> dict:
    """Diagnose saved P1 history; never interpret a history pass as readiness.

    Reuse the existing replay's strict OHLCV/duplicate/date checks and completed
    weekly engine, plus the shared US market-close cutoff. Invalid rows are
    rejected before filtering so a bad date cannot disappear into a valid tail.
    """
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("Evaluation timestamp must be timezone-aware")
    if not set(PRICE_COLUMNS).issubset(prices.columns):
        raise ValueError("Saved prices require date, symbol and OHLCV columns")
    p1 = [r for r in gap_report["review_rows"]
          if r["issuer_identity_review_cohort"] == P1]
    symbols = [r["symbol"] for r in p1]
    if len(symbols) != len(set(symbols)):
        raise ValueError("Duplicate P1 symbol")
    local_clock = evaluated_at.astimezone(ZoneInfo("Asia/Seoul"))
    as_of = pd.Timestamp(local_clock.date())
    frame = prices.copy(deep=True)
    frame["symbol"] = frame.symbol.fillna("").astype(str).str.strip().str.upper()
    frame = frame[frame.symbol.isin(symbols)].copy()
    rows = []
    for gap in p1:
        symbol = gap["symbol"]
        venues = gap["kis_venues_by_ticker"]
        if len(venues) != 1 or venues[0] not in {"NAS", "NYS", "AMS"}:
            raise ValueError("P1 requires a single saved US venue")
        bars = frame[frame.symbol.eq(symbol)].copy()
        cutoff = completed_bar_cutoff_date(venues[0], local_clock)
        valid = False
        complete = bars.iloc[:0]
        replay = None
        if not bars.empty:
            # Date-only contract avoids mixed timezone/time-of-day reinterpretation.
            date_only = bars.date.astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()
            if date_only:
                raw_replay = OfflineStageReplay(bars, as_of)
                valid = (symbol in raw_replay.daily and
                         bool(pd.to_datetime(bars.date).dt.dayofweek.le(4).all()))
            if valid:
                complete = filter_incomplete_daily_bars(bars, {symbol: venues[0]}, local_clock)
                replay = OfflineStageReplay(complete, as_of)
        daily = replay.daily.get(symbol, 0) if replay else 0
        weekly = replay.weekly.get(symbol) if replay else None
        weeks = len(weekly) if weekly is not None else 0
        latest = replay.latest.get(symbol) if replay else None
        fresh = bool(latest is not None and 0 <= (as_of - latest).days <= 7)
        reasons = []
        if bars.empty:
            reasons.append("saved_prices_missing")
        elif not valid:
            reasons.append("saved_prices_invalid")
        if daily < 150:
            reasons.append("completed_daily150_missing")
        if weeks < 35:
            reasons.append("completed_weeks35_missing")
        if not fresh:
            reasons.append("freshness7_missing")
        large_move = bool(valid and not complete.empty and
                          (pd.to_numeric(complete.sort_values("date").close)
                           .pct_change().abs() > 0.5).any())
        if large_move:
            reasons.append("large_close_move_requires_review")
        status = ("missing" if bars.empty else "invalid" if not valid else
                  "insufficient_history" if daily < 150 or weeks < 35 else
                  "stale" if not fresh else "price_anomaly_review" if large_move else
                  "saved_history_thresholds_met_review_only")
        rows.append({
            "symbol": symbol, "saved_kis_venue": venues[0],
            "sec_reference_status": gap["sec_reference_status"],
            "price_inventory_status": status, "stored_rows": len(bars),
            "saved_ohlcv_quality_pass": valid,
            "excluded_unclosed_rows": len(bars) - len(complete) if valid else None,
            "completed_bar_cutoff": cutoff, "completed_daily_rows": daily,
            "completed_weeks": weeks,
            "first_completed_session": str(pd.to_datetime(complete.date).min().date()) if daily else None,
            "latest_completed_session": str(latest.date()) if latest is not None else None,
            "fresh7": fresh, "price_blockers": reasons,
            "next_price_action": ("inspect_saved_price_errors" if status == "invalid" else
                                  "review_saved_price_anomaly" if large_move else
                                  "confirm_price_provenance_and_continuity" if not reasons else
                                  "review_bounded_kis_history_request"),
            "remaining_review_gates": [
                "exact_security_and_saved_price_provenance",
                "security_level_usd_cap_basis_and_date",
                "listing_and_session_continuity",
                "sector_and_market_benchmark_rs",
                "explicit_candidate_intake_and_activation_decision",
            ],
            "live_kis_support_verified": False,
            "operational_approval_granted": False,
        })
    return {
        "mode": "offline_p1_saved_price_inventory", "evaluated_at": evaluated_at.isoformat(),
        "source_sha256": gap_report["source_sha256"], "p1_symbols": len(rows),
        "price_inventory_status_counts": dict(sorted(Counter(r["price_inventory_status"] for r in rows).items())),
        "price_blocker_counts": dict(sorted(Counter(b for r in rows for b in r["price_blockers"]).items())),
        "operational_additions": 0, "network_requests": 0,
        "collection_performed": False, "stage_labels_calculated": False,
        "notes": [
            "Saved ticker-only OHLCV cannot verify exact venue, provider, adjustment basis or KIS support.",
            "150 completed daily rows and 35 completed weekly bars are inventory thresholds, not activation approval.",
            "Weekday/close filtering reuses existing policy; exchange-holiday and missing-session continuity remain review gates.",
            "Nasdaq issuer cap, receipt approval time and SEC links do not verify security-level cap or price readiness.",
        ],
        "review_rows": rows,
    }


def build_report(raw: bytes, receipt: dict, data_dir: Path, sec_registry: dict,
                 evaluated_at: datetime) -> dict:
    names = ("stock_universe_candidates.csv", "unranked_us_stock_master.csv",
             "daily_prices.csv", "candidate_daily_prices.csv")
    payloads = {name: (data_dir / name).read_bytes() for name in names}
    from io import BytesIO
    frames = {name: pd.read_csv(BytesIO(value), dtype=str, keep_default_na=False)
              for name, value in payloads.items()}
    gaps = audit_gap(raw, receipt, frames[names[0]], frames[names[1]],
                     now=evaluated_at, sec_registry=sec_registry)
    report = price_inventory(gaps, pd.concat([frames[names[2]], frames[names[3]]],
                                            ignore_index=True), evaluated_at)
    report["input_files"] = {name: {"sha256": hashlib.sha256(value).hexdigest(), "bytes": len(value)}
                             for name, value in payloads.items()}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nasdaq-csv", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--sec-registry", type=Path, default=SEC_REGISTRY)
    parser.add_argument("--evaluated-at", required=True, help="Timezone-aware ISO timestamp")
    parser.add_argument("--preview", type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.preview <= 100:
        parser.error("--preview must be between 0 and 100")
    report = build_report(args.nasdaq_csv.read_bytes(),
                          json.loads(args.receipt.read_text(encoding="utf-8")), args.data_dir,
                          json.loads(args.sec_registry.read_text(encoding="utf-8")),
                          datetime.fromisoformat(args.evaluated_at))
    rows = report.pop("review_rows")
    if args.preview:
        report["unapproved_preview"] = rows[:args.preview]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
