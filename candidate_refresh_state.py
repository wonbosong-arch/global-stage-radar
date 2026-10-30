"""Review-only collection scheduling and validated snapshot publication."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from market_data import MarketDataError, normalize_ohlcv


def read_collection_status(path: Path, prices_path: Path) -> dict:
    """Bad/stale metadata must never invalidate an independently readable CSV."""
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(status, dict):
            return {}
        for field in ("pending_symbols", "deferred_symbols", "fresh_data_symbols", "skipped_symbols"):
            values = status.get(field, [])
            if not isinstance(values, list) or any(not isinstance(s, str) for s in values):
                return {}
        if not isinstance(status.get("errors", []), list):
            return {}
        if any(not isinstance(e, dict) or not isinstance(e.get("symbol", ""), str)
               for e in status.get("errors", [])):
            return {}
        entries = status.get("collection_state", {})
        if not isinstance(entries, dict) or any(not isinstance(e, dict) for e in entries.values()):
            return {}
        if any(not isinstance(e.get(field, ""), str) for e in entries.values()
               for field in ("last_attempt_at_utc", "last_success_at_utc", "retry_after_utc")):
            return {}
        digest = status.get("snapshot_sha256")
        if digest and (not prices_path.exists() or digest != hashlib.sha256(prices_path.read_bytes()).hexdigest()):
            return {}
        return status
    except (OSError, ValueError, TypeError):
        return {}


def route_key(row) -> str:
    return f"{str(row.exchange).strip().upper()}:{str(row.asset_type).strip().lower()}"


def collection_plan(candidates, previous, status, now):
    """Finish the unattempted tail before retrying failures or recent successes.

    First-time missing histories can enter at the front once. Failed missing
    symbols then join the normal rotation, so they cannot monopolize every run.
    """
    raw_state = status.get("collection_state", {})
    state = {s: dict(v) for s, v in raw_state.items() if isinstance(v, dict)} if isinstance(raw_state, dict) else {}
    legacy_attempts = set(status.get("fresh_data_symbols", []))
    legacy_attempts.update(e.get("symbol") for e in status.get("errors", [])
                           if isinstance(e, dict) and e.get("error") != "refresh_deferred_time_budget")
    for symbol in legacy_attempts:
        state.setdefault(symbol, {"last_attempt_at_utc": status.get("updated_at_utc", "")})
    pending = list(dict.fromkeys(status.get("pending_symbols", []) + status.get("deferred_symbols", []) + [
        e.get("symbol") for e in status.get("errors", [])
        if isinstance(e, dict) and e.get("error") == "refresh_deferred_time_budget"
    ]))
    pending_order = {s: i for i, s in enumerate(pending)}
    available = set(previous["symbol"])
    latest = previous.groupby("symbol")["date"].max().astype(str).to_dict()
    keys, skipped = {}, []
    for row in candidates.itertuples(index=False):
        entry = state.get(row.symbol, {})
        if entry.get("route") != route_key(row):
            entry.pop("retry_after_utc", None)
        retry_after = pd.to_datetime(entry.get("retry_after_utc"), utc=True, errors="coerce")
        if pd.notna(retry_after) and retry_after > now:
            skipped.append(row.symbol)
        never_attempted = not entry.get("last_attempt_at_utc")
        keys[row.symbol] = (
            0 if row.symbol not in available and never_attempted else 1 if row.symbol in pending_order else 2,
            pending_order.get(row.symbol, len(pending_order)),
            entry.get("last_attempt_at_utc", ""),
            entry.get("last_success_at_utc", latest.get(row.symbol, "")),
        )
    ordered = sorted(candidates["symbol"], key=keys.__getitem__)
    plan = candidates.set_index("symbol", drop=False).loc[[s for s in ordered if s not in skipped]].reset_index(drop=True)
    return plan, {s: state.get(s, {}) for s in candidates["symbol"]}, skipped


def classify_failure(exc: Exception) -> str:
    """Only explicit unsupported-route failures get a long retry cooldown."""
    text = str(exc).lower()
    http_codes = set(re.findall(r"http\s+(\d{3})\b", text))
    if "429" in http_codes or any(code in text for code in ("egw00201", "egw00133", "rate limit", "too many requests")):
        return "rate_limited"
    if http_codes & {"401", "403"} or any(code in text for code in ("unauthorized", "authentication", "access_token", "token request failed")):
        return "authentication_failed"
    if isinstance(exc, NotImplementedError) or (isinstance(exc, ValueError) and any(
        word in text for word in ("unsupported", "does not support", "supported kis", "require exchange", "reserved for")
    )):
        return "unsupported_symbol"
    if isinstance(exc, (TimeoutError, ConnectionError)) or http_codes & {"500", "502", "503", "504"} or any(
        word in text for word in ("timeout", "network", "connection", "server")
    ):
        return "temporary_server_error"
    return "validation_error"


def update_symbol_state(state, row, outcome, now):
    entry = state.setdefault(row.symbol, {})
    entry.update(last_attempt_at_utc=now.isoformat(), outcome=outcome, route=route_key(row))
    entry.pop("retry_after_utc", None)
    if outcome == "succeeded":
        entry["last_success_at_utc"] = now.isoformat()
    elif outcome == "unsupported_symbol":
        entry["retry_after_utc"] = (now + timedelta(days=30)).isoformat()


def validate_prices(frame, symbol=None):
    result = normalize_ohlcv(frame)
    if not result.empty and not np.isfinite(result[["open", "high", "low", "close", "volume"]].to_numpy()).all():
        raise MarketDataError("Non-finite OHLCV value")
    if symbol and not result["symbol"].eq(symbol).all():
        raise MarketDataError("Response symbol differs from requested symbol")
    if not result.empty:
        result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    return result


def publish_snapshot(prices, status, prices_path, status_path):
    """Stage both complete files before replacement; roll back publication errors.

    The digest lets scheduling reject stale metadata after a hard process kill
    between renames. The CSV remains independently readable in that window.
    """
    prices = validate_prices(prices)
    if status["symbols_with_data"] != prices["symbol"].nunique():
        raise ValueError("Snapshot/status symbol count mismatch")
    coverage = {item["symbol"]: item["rows"] for item in status["per_symbol_coverage"]}
    if coverage != prices.groupby("symbol")["date"].nunique().to_dict():
        raise ValueError("Snapshot/status coverage mismatch")
    staged, backups, replaced = {}, {}, []
    try:
        for path in (prices_path, status_path):
            fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
            os.close(fd)
            staged[path] = Path(name)
            if path.exists():
                fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".bak", dir=path.parent)
                os.close(fd)
                backup = Path(name)
                backups[path] = backup
                backup.write_bytes(path.read_bytes())
        prices.to_csv(staged[prices_path], index=False)
        status["snapshot_sha256"] = hashlib.sha256(staged[prices_path].read_bytes()).hexdigest()
        staged[status_path].write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for path in (prices_path, status_path):
            with staged[path].open("rb") as handle:
                os.fsync(handle.fileno())
        for path in (prices_path, status_path):
            os.replace(staged[path], path)
            replaced.append(path)
    except BaseException:
        for path in reversed(replaced):
            if path in backups:
                backup = backups[path]
                try:
                    os.replace(backup, path)
                except OSError as exc:
                    # Keep the recovery copy even if the filesystem also rejects rollback.
                    backups.pop(path)
                    raise RuntimeError(f"Snapshot rollback failed; original retained at {backup}") from exc
            else:
                path.unlink(missing_ok=True)
        raise
    finally:
        for path in [*staged.values(), *backups.values()]:
            path.unlink(missing_ok=True)


def record_refresh_failure(prices_path, status_path):
    """Actions fallback preserves scheduling state and the saved CSV's coverage."""
    status = read_collection_status(status_path, prices_path)
    now = datetime.now(timezone.utc)
    # These checkpoint metrics describe saved history, never a fresh success.
    checkpoint_at = status.get("updated_at_utc")
    status.update(
        status_schema_version=2, collection_phase="failed", finished_at_utc=None,
        last_checkpoint_at_utc=checkpoint_at,
        updated_at_utc=now.isoformat(), updated_at_kst=now.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
        refresh_complete=False, refresh_attempt_run_level_failed=True,
        fresh_data_symbols=[], fresh_data_symbol_count=0, attempted_symbol_count=None,
        failed_symbols=["*"], failed_symbol_count=1, error_count=1,
        errors=[{"symbol": "*", "error": "refresh_failed_before_status_write; inspect GitHub Actions logs"}],
        data_note="Refresh failed; retained CSV and scheduling state are from the last checkpoint, not a successful run.",
    )
    temporary = status_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, status_path)
