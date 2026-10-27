"""Bounded, review-only intake from the secondary large-cap discovery queue.

This expands the candidate-review list without changing the approved monitoring universe.
Secondary market-cap observations remain unverified and possible ADRs are excluded.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from stock_mapping import proposed_stock_mapping

ROOT = Path(__file__).resolve().parent
CANDIDATES_PATH = ROOT / "data" / "stock_universe_candidates.csv"
UNIVERSE_PATH = ROOT / "data" / "monitoring_universe.csv"
QUEUE_PATH = ROOT / "data" / "yahoo_large_cap_candidate_review.csv"
CAP_STATUS_PATH = ROOT / "data" / "yahoo_master_cap_batch_status.json"
STATUS_PATH = ROOT / "data" / "candidate_collection_status.json"
MAX_ADD_PER_RUN = 25
MAX_TOTAL_CANDIDATES = 500
MAX_QUEUE_AGE_HOURS = 72


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _queue_is_fresh(path: Path, max_age_hours: int = MAX_QUEUE_AGE_HOURS) -> tuple[bool, str]:
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
        updated = datetime.fromisoformat(str(status["updated_at_utc"]).replace("Z", "+00:00"))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - updated.astimezone(timezone.utc)).total_seconds() / 3600
        if age_hours < -1 or age_hours > max_age_hours:
            return False, f"secondary cap queue status is stale or future-dated ({age_hours:.1f} hours)"
        if status.get("market_cap_status") != "secondary_estimates_only_not_verified":
            return False, "secondary cap queue status is not explicitly review-only"
        return True, "fresh review-only cap queue"
    except (OSError, ValueError, KeyError, TypeError):
        return False, "secondary cap queue status is missing or malformed"


def build_review_only_candidates(
    candidates: pd.DataFrame,
    active: pd.DataFrame,
    queue: pd.DataFrame,
    discovered_at: str,
    max_add: int = MAX_ADD_PER_RUN,
    max_total: int = MAX_TOTAL_CANDIDATES,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Append up to max_add large-cap ordinary-equity suggestions, never activating them."""
    if max_add < 0 or max_total < 0:
        raise ValueError("candidate limits must be non-negative")
    existing = candidates.copy()
    if existing.empty and len(existing.columns) == 0:
        existing = pd.DataFrame(columns=[
            "symbol", "name", "market", "sector", "asset_type", "market_benchmark",
            "sector_benchmark", "exchange", "country", "currency", "instrument_type",
            "identity_status", "market_cap_status", "provider_status", "activation_status",
        ])
    for frame in (existing, active):
        if "symbol" not in frame.columns:
            frame["symbol"] = ""
    existing_symbols = set(existing["symbol"].astype(str).str.strip().str.upper()) - {""}
    active_symbols = set(active["symbol"].astype(str).str.strip().str.upper()) - {""}
    queue_symbols = set(queue.get("symbol", pd.Series(dtype=str)).astype(str).str.strip().str.upper()) - {""}

    status: dict[str, object] = {
        "large_cap_review_candidates_added": 0,
        "large_cap_review_candidates_available": int(len(queue)),
        "large_cap_review_candidate_limit_per_run": int(max_add),
        "large_cap_review_candidate_total_limit": int(max_total),
        "large_cap_review_candidates_status": "pending_review_only",
        "large_cap_review_candidates_note": "No candidate is verified or activated by this intake.",
    }
    room = max(0, max_total - len(existing))
    if max_add == 0 or room == 0 or queue.empty:
        status["large_cap_review_candidates_skip_reason"] = (
            "candidate list reached configured cap" if room == 0 else "no queue rows or intake disabled"
        )
        return existing, status

    q = queue.copy()
    for col in ("symbol", "name", "exchange", "instrument_type", "identity_status",
                "market_cap_status", "activation_status", "market_cap_source_url",
                "market_cap_asof", "market_cap_asof_basis", "fetched_at_utc",
                "review_reason", "sector", "sector_benchmark", "proposed_market",
                "market_benchmark", "mapping_status", "mapping_note"):
        if col not in q:
            q[col] = ""
        q[col] = q[col].fillna("").astype(str).str.strip()
    caps = pd.to_numeric(q.get("discovery_market_cap_usd_b_secondary", pd.Series(index=q.index, dtype=float)), errors="coerce")
    eligible = (
        q["instrument_type"].eq("equity_candidate_unverified")
        & q["identity_status"].eq("review_required")
        & q["market_cap_status"].eq("not_verified")
        & q["activation_status"].eq("pending_review")
        & caps.ge(1.0)
        & ~q["symbol"].str.upper().str.contains(r"[/=]", regex=True, na=False)
    )
    q = q.loc[eligible].copy()
    q_caps = caps.loc[q.index]
    q = q.loc[~q["symbol"].str.upper().isin(existing_symbols | active_symbols)].copy()
    q_caps = q_caps.loc[q.index]
    q = q.assign(_cap=q_caps).sort_values(["_cap", "symbol"], ascending=[False, True])
    slots = min(max_add, room)
    chosen = q.head(slots)

    new_rows: list[dict[str, str]] = []
    for row in chosen.to_dict("records"):
        symbol = str(row["symbol"]).upper()
        exchange = str(row["exchange"]).upper()
        mapping = proposed_stock_mapping(symbol, exchange)
        record = {column: "" for column in existing.columns}
        values = {
            "symbol": symbol,
            "name": row.get("name", ""),
            "market": "United States",
            "sector": mapping.get("proposed_sector", row.get("sector", "")),
            "asset_type": "stock",
            "market_benchmark": mapping.get("proposed_market_benchmark", "SPY"),
            "sector_benchmark": mapping.get("proposed_sector_benchmark", row.get("sector_benchmark", "")),
            "exchange": exchange,
            "country": "United States",
            "currency": "USD",
            "instrument_type": "common_stock_candidate_unverified",
            "identity_status": "review_required",
            "market_cap_status": "not_verified",
            "provider_status": "not_checked",
            "activation_status": "pending_review",
            "review_note": "Secondary Yahoo market-cap estimate only; identity, cap date, listing, provider history and sector mapping require review. Not activated.",
            "market_cap_source_url": row.get("market_cap_source_url", ""),
            "market_cap_asof": "",
            "depositary_ratio_status": "review_required",
            "market_cap_usd_b_secondary": str(row.get("discovery_market_cap_usd_b_secondary", "")),
            "discovery_market_cap_usd": str(float(row.get("discovery_market_cap_usd_b_secondary") or 0) * 1_000_000_000),
            "discovery_market_cap_native": "",
            "discovery_market_cap_currency": "USD",
            "discovery_source": "yahoo_large_cap_review_queue",
            "discovered_at": discovered_at,
            "discovery_cap_threshold_pass": "secondary_estimate_ge_1b_review_only",
            "discovery_security_type": "2",
            "discovery_review_reason": row.get("review_reason", ""),
            "discovery_industry_code": "",
            "discovery_dr_country_code": "",
            "proposed_market": mapping.get("proposed_market", "United States (US-listed instrument)"),
            "proposed_sector": mapping.get("proposed_sector", ""),
            "proposed_asset_type": "stock",
            "proposed_market_benchmark": mapping.get("proposed_market_benchmark", "SPY"),
            "proposed_sector_benchmark": mapping.get("proposed_sector_benchmark", ""),
            "mapping_status": mapping.get("mapping_status", "sector_mapping_missing"),
            "mapping_note": mapping.get("mapping_note", "First-pass suggestion only; manual review required."),
        }
        for key, value in values.items():
            if key in record:
                record[key] = str(value if value is not None else "")
        new_rows.append(record)

    if new_rows:
        new_frame = pd.DataFrame(new_rows, columns=existing.columns)
        existing = pd.concat([existing, new_frame], ignore_index=True)
        existing["symbol"] = existing["symbol"].astype(str).str.strip().str.upper()
        existing = existing.drop_duplicates("symbol", keep="first").reset_index(drop=True)
    status["large_cap_review_candidates_added"] = len(new_rows)
    status["large_cap_review_candidates_remaining_after_batch"] = max(0, len(q) - len(new_rows))
    status["large_cap_review_candidates_status"] = "added_pending_review" if new_rows else "no_eligible_new_candidates"
    return existing, status


def main() -> int:
    candidates = _read_csv(CANDIDATES_PATH)
    active = _read_csv(UNIVERSE_PATH)
    queue = _read_csv(QUEUE_PATH)
    fresh, freshness_note = _queue_is_fresh(CAP_STATUS_PATH)
    discovered_at = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Seoul")).date().isoformat()
    try:
        previous_status = json.loads(STATUS_PATH.read_text(encoding="utf-8")) if STATUS_PATH.exists() else {}
    except (OSError, ValueError):
        previous_status = {}

    if not fresh:
        status = {
            "large_cap_review_candidates_added": 0,
            "large_cap_review_candidates_available": int(len(queue)),
            "large_cap_review_candidates_status": "skipped_stale_or_unverified_queue",
            "large_cap_review_candidates_skip_reason": freshness_note,
            "large_cap_review_candidates_note": "No candidate is verified or activated by this intake.",
        }
    elif previous_status.get("large_cap_review_candidates_last_intake_date") == discovered_at:
        status = {
            "large_cap_review_candidates_added": 0,
            "large_cap_review_candidates_available": int(len(queue)),
            "large_cap_review_candidates_status": "daily_intake_already_completed",
            "large_cap_review_candidates_skip_reason": "bounded intake already ran on this KST date",
            "large_cap_review_candidates_note": "No candidate is verified or activated by this intake.",
        }
    else:
        candidates, status = build_review_only_candidates(candidates, active, queue, discovered_at)
        candidates.to_csv(CANDIDATES_PATH, index=False)
        status["large_cap_review_candidates_last_intake_date"] = discovered_at
        status["candidate_count_after_update"] = int(len(candidates))

    previous_status.update(status)
    previous_status["large_cap_review_candidates_queue_freshness"] = freshness_note
    previous_status["candidate_count_after_update"] = int(len(candidates))
    STATUS_PATH.write_text(json.dumps(previous_status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
