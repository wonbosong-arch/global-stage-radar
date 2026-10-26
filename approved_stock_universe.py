"""Build a conservative Stage-analysis universe from explicitly approved candidates.

This bridge is intentionally opt-in: pending candidates are never added to the
active monitoring universe merely because they have prices or market-cap data.
"""
from __future__ import annotations

import pandas as pd

REQUIRED_CANDIDATE_COLUMNS = {
    "symbol", "name", "market", "sector", "asset_type",
    "market_benchmark", "sector_benchmark", "exchange", "activation_status",
}


def approved_candidates_for_stage(candidates: pd.DataFrame) -> pd.DataFrame:
    """Return only explicitly approved, fully mapped candidates in universe schema."""
    missing = REQUIRED_CANDIDATE_COLUMNS - set(candidates.columns)
    if missing:
        raise ValueError("Missing candidate columns: " + ", ".join(sorted(missing)))

    frame = candidates.copy()
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.strip().str.upper()
    status = frame["activation_status"].fillna("").astype(str).str.strip().str.lower()
    # Be deliberately strict: no aliases, recommendations, or inferred approvals.
    approved = frame.loc[status.eq("approved")].copy()
    if approved.empty:
        return pd.DataFrame(columns=[
            "symbol", "name", "market", "sector", "asset_type", "market_cap_usd",
            "market_benchmark", "sector_benchmark", "exchange",
        ])

    if approved["symbol"].eq("").any() or approved["symbol"].duplicated().any():
        raise ValueError("Approved candidates must have unique, non-empty symbols.")

    for column in ("name", "market", "sector", "asset_type", "market_benchmark", "sector_benchmark", "exchange"):
        approved[column] = approved[column].fillna("").astype(str).str.strip()

    required_text = ["name", "market", "sector", "asset_type", "market_benchmark", "exchange"]
    invalid = approved[required_text].eq("").any(axis=1)
    invalid |= approved["asset_type"].eq("stock") & approved["sector_benchmark"].eq("")
    if invalid.any():
        symbols = ", ".join(approved.loc[invalid, "symbol"].astype(str).tolist()[:10])
        raise ValueError("Approved candidates lack required Stage mapping: " + symbols)

    if "market_cap_usd" in approved.columns:
        cap = pd.to_numeric(approved["market_cap_usd"], errors="coerce")
    elif "market_cap_usd_b_secondary" in approved.columns:
        # Secondary Yahoo observations are evidence only and must not silently
        # become the verified market-cap field used by the activation gate.
        cap = pd.Series(float("nan"), index=approved.index)
    else:
        cap = pd.Series(float("nan"), index=approved.index)

    result = approved[[
        "symbol", "name", "market", "sector", "asset_type",
        "market_benchmark", "sector_benchmark", "exchange",
    ]].copy()
    result["market_cap_usd"] = cap
    return result.reset_index(drop=True)
