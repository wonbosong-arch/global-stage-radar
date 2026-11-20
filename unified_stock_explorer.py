"""Read-only union for the existing stock tab; never promotes research candidates.

Price-bar identity is symbol-only in the retained KIS snapshot. Do not join an
ambiguous candidate to prices or guess its exchange from availability.
"""
from __future__ import annotations

import pandas as pd

from stage_engine import weekly_bars


def research_chart_weekly(daily: pd.DataFrame, as_of):
    """Show completed weeks or, before the first close, a price-only candle."""
    completed = weekly_bars(daily, as_of_date=as_of, min_bars=1)
    if completed is not None:
        return completed, False
    # When the completed history is empty, the saved sessions belong to a
    # single week. Use the last observed session as the display date.
    daily = daily.sort_values("date")
    return pd.DataFrame([{
        "date": daily.date.iloc[-1], "open": daily.open.iloc[0],
        "high": daily.high.max(), "low": daily.low.min(),
        "close": daily.close.iloc[-1], "volume": daily.volume.sum(),
    }]), True


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
    # A validated native Nasdaq classification remains useful for browsing even
    # when no sufficiently close ETF is assigned. Keep the native taxonomy
    # visibly distinct from GICS-like research ETF sectors; do not synthesize a
    # benchmark or grant Stage eligibility from a sector label.
    proposal = pending["proposed_sector"].fillna("").astype(str).str.strip()
    native = (pending["native_sector"].fillna("").astype(str).str.strip()
              if "native_sector" in pending else pd.Series("", index=pending.index))
    industry = (pending["native_industry"].fillna("").astype(str).str.strip()
                if "native_industry" in pending else pd.Series("", index=pending.index))
    native_only = proposal.eq("") & native.ne("") & industry.ne("")
    pending["sector"] = proposal.where(~native_only, "Nasdaq · " + native)
    pending["asset_type"] = pending["asset_type_norm"] = "stock"
    eligible = pending["research_eligible"].eq(True)
    pending["stage_label"] = pending["provisional_stage_label"].where(eligible, "연구 판정 보류")
    if "price_history_short" in pending:
        pending.loc[~eligible & pending.price_history_short.eq(True), "stage_label"] = "가격 이력 부족 · Stage 보류"
    if "review_note" in pending:
        pending["review_note"] = pending["review_note"].replace({
            "mapping_incomplete_or_not_stock": "업종 ETF 미연결",
            "sector_benchmark_metadata_missing": "업종 ETF 검증 필요",
            "completed_weeks35_missing": "종목 또는 비교 ETF의 완성 주봉 35개 미만",
            "valid_daily150_missing": "종목 또는 비교 ETF의 유효 일봉 150개 미만",
            "freshness_missing": "종목 또는 비교 ETF의 최신 가격 확인 필요",
        }, regex=True)
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


def mapped_research_mask(rows: pd.DataFrame) -> pd.Series:
    """Research stocks with verified, usable saved Stage mapping and sector RS.

    This is a *presentation filter*, not a new approval or Stage calculation.
    Incomplete price charts remain available through the all-charts view.
    """
    def column(name, default=None):
        if name in rows:
            return rows[name]
        return pd.Series(default, index=rows.index)

    if rows.empty:
        return pd.Series(False, index=rows.index, dtype=bool)
    scope = column("analysis_scope", "").fillna("").astype(str)
    sector = column("proposed_sector", "").fillna("").astype(str).str.strip()
    benchmark = column("suggested_sector_benchmark", "").fillna("").astype(str).str.strip()
    rs = pd.to_numeric(column("rs_sector_26w_pct"), errors="coerce")
    rs = rs.replace([float("inf"), float("-inf")], float("nan"))
    return (scope.eq("연구")
            & column("research_eligible", False).eq(True)
            & sector.ne("") & benchmark.ne("") & rs.notna())


def mapped_stock_view(rows: pd.DataFrame) -> pd.DataFrame:
    """Keep existing operating stocks and only fully mapped research stocks."""
    if "analysis_scope" not in rows:
        return rows.copy()
    return rows.loc[rows["analysis_scope"].ne("연구") | mapped_research_mask(rows)].copy()
