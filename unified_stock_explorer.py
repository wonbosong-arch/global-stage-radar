"""Read-only union for the existing stock tab; never promotes research candidates.

Price-bar identity is symbol-only in the retained KIS snapshot. Do not join an
ambiguous candidate to prices or guess its exchange from availability.
"""
from __future__ import annotations

import pandas as pd


def unified_stock_rows(operating: pd.DataFrame, report: pd.DataFrame,
                       research_prices: pd.DataFrame):
    """Return UI rows and *research-only* symbols with safe saved price history.

    The operational frame is not mutated. Exact symbol overlap keeps the
    operational row and chart; a symbol conflict cannot create a second chart
    selection with the same key. Candidate identity holds have no price bars
    after the existing research_identities guard and are never resurrected here.
    """
    active = operating.copy()
    active["analysis_scope"] = "운영"
    if report.empty or research_prices.empty:
        return active, set()

    safe_prices = set(research_prices["symbol"].dropna().astype(str).str.strip().str.upper())
    pending = report.copy()
    pending["symbol"] = pending["symbol"].astype(str).str.strip().str.upper()
    duplicated = set(pending.loc[pending.symbol.duplicated(keep=False), "symbol"])
    # Fail closed if an upstream snapshot inadvertently contains nonunique
    # identities, even when the normal quarantine has already run.
    pending = pending.loc[pending.symbol.isin(safe_prices) & ~pending.symbol.isin(duplicated)].copy()
    active_symbols = set(active["symbol"].dropna().astype(str).str.strip().str.upper())
    pending = pending.loc[~pending.symbol.isin(active_symbols)].copy()
    if pending.empty:
        return active, set()

    pending["market"] = "United States"
    pending["sector"] = pending["proposed_sector"].fillna("").astype(str)
    pending["asset_type"] = pending["asset_type_norm"] = "stock"
    eligible = pending["research_eligible"].eq(True)
    pending["stage_label"] = pending["provisional_stage_label"].where(eligible, "연구 판정 보류")
    pending["slope4_pct"] = pd.to_numeric(pending.get("ma30_slope_4w_pct"), errors="coerce")
    pending["rs_market_26w_pct"] = pd.to_numeric(pending.get("market_rs_26w_pct"), errors="coerce")
    pending["rs_sector_26w_pct"] = pd.to_numeric(pending.get("sector_rs_26w_pct"), errors="coerce")
    pending["last_date"] = pending.get("completed_weekly_date")
    pending["last_daily_date"] = pending.get("candidate_latest_daily_date")
    pending["volume_confirmation"] = pending.get("volume_context", "")
    pending["price_available"] = True
    pending["stage2_new_entry"] = False
    pending["previous_stage_label"] = "이전 주 데이터 부족"
    pending["analysis_scope"] = "연구"
    # Never alter pending_review_not_activated or copy research Stage to the
    # operational universe; this DataFrame is only for on-screen exploration.
    symbols = set(pending["symbol"])
    return pd.concat([active, pending], ignore_index=True, sort=False), symbols
