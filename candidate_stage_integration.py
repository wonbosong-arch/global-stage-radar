"""Load only candidates that pass the final Stage activation gates."""
from __future__ import annotations

import pandas as pd

from approved_stock_universe import approved_candidates_for_stage


def extend_universe_with_approved_candidates(
    base_universe: pd.DataFrame,
    candidates: pd.DataFrame,
    prices: pd.DataFrame,
    latest_snapshot_date=None,
) -> tuple[pd.DataFrame, list[dict]]:
    """Extend a base universe candidate-by-candidate; isolate failures per symbol."""
    if candidates.empty:
        return base_universe.copy(), []
    if "activation_status" not in candidates.columns:
        return base_universe.copy(), [{"symbol": "", "error": "activation_status column is missing"}]

    active = candidates[
        candidates["activation_status"].fillna("").astype(str).str.strip().str.lower().eq("active")
    ].copy()
    if active.empty:
        return base_universe.copy(), []

    base = base_universe.copy()
    existing = set(base["symbol"].fillna("").astype(str).str.strip().str.upper())
    additions = []
    errors = []
    for _, row in active.iterrows():
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            errors.append({"symbol": "", "error": "Active candidate has empty symbol"})
            continue
        if symbol in existing:
            errors.append({"symbol": symbol, "error": "Symbol already exists in base universe"})
            continue
        try:
            needed = {symbol}
            market_benchmark = str(row.get("market_benchmark", "")).strip().upper()
            sector_benchmark = str(row.get("sector_benchmark", "")).strip().upper()
            if market_benchmark:
                needed.add(market_benchmark)
            if sector_benchmark:
                needed.add(sector_benchmark)
            candidate_prices = prices[
                prices["symbol"].fillna("").astype(str).str.strip().str.upper().isin(needed)
            ].copy()
            one = approved_candidates_for_stage(
                pd.DataFrame([row.to_dict()]),
                candidate_prices,
                latest_snapshot_date=latest_snapshot_date,
            )
            if len(one) != 1:
                errors.append({"symbol": symbol, "error": "Candidate did not produce exactly one approved row"})
                continue
            additions.append(one)
            existing.add(symbol)
        except Exception as exc:
            errors.append({"symbol": symbol, "error": f"{type(exc).__name__}: {str(exc)[:250]}"})

    if not additions:
        return base, errors
    return pd.concat([base, *additions], ignore_index=True, sort=False), errors
