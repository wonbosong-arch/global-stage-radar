"""Build a review-only Stage/relative-strength screen for inactive Japan ETF candidates."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
CANDIDATE_PATH = ROOT / "data" / "japan_candidate_prices.csv"
ACTIVE_PATH = ROOT / "data" / "daily_prices.csv"
METADATA_PATH = ROOT / "data" / "country_sector_proxy_candidates.csv"
OUTPUT_PATH = ROOT / "data" / "japan_candidate_screening_review.csv"
BENCHMARK = "EWJ"


def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "symbol", "close", "volume"])
    d = frame.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]
    if not {"date", "symbol", "close"}.issubset(d.columns):
        raise ValueError("Price file must include date, symbol, and close columns.")
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d["symbol"] = d["symbol"].fillna("").astype(str).str.strip().str.upper()
    d["close"] = pd.to_numeric(d["close"], errors="coerce")
    d["volume"] = pd.to_numeric(d["volume"], errors="coerce") if "volume" in d else float("nan")
    return d.dropna(subset=["date", "close"]).loc[lambda x: x["symbol"].ne("") & x["close"].gt(0)]


def _weekly_close(frame: pd.DataFrame) -> pd.Series:
    return frame.sort_values("date").set_index("date")["close"].resample("W-FRI").last().dropna()


def _return(series: pd.Series, weeks: int) -> float | None:
    if len(series) <= weeks:
        return None
    start, end = float(series.iloc[-weeks - 1]), float(series.iloc[-1])
    return (end / start - 1.0) * 100.0 if start > 0 else None


def _sma30(series: pd.Series) -> tuple[float | None, bool | None]:
    if len(series) < 34:
        return None, None
    ma = series.rolling(30).mean()
    latest, prior = float(ma.iloc[-1]), float(ma.iloc[-5])
    return latest, latest > prior


def build_review(candidate_prices: pd.DataFrame, active_prices: pd.DataFrame,
                 metadata: pd.DataFrame) -> pd.DataFrame:
    candidates, active = _normalize(candidate_prices), _normalize(active_prices)
    meta = metadata.copy() if metadata is not None else pd.DataFrame()
    meta.columns = [str(c).strip().lower() for c in meta.columns]
    for col in ("symbol", "country", "sector_or_theme", "instrument_scope", "dashboard_status", "decision_note"):
        if col not in meta:
            meta[col] = ""
    meta["symbol"] = meta["symbol"].astype(str).str.strip().str.upper()
    meta = meta[meta["country"].astype(str).str.strip().eq("Japan")].drop_duplicates("symbol").set_index("symbol", drop=False)
    benchmark_frame = active[active["symbol"].eq(BENCHMARK)]
    benchmark_week = _weekly_close(benchmark_frame) if not benchmark_frame.empty else pd.Series(dtype=float)
    benchmark_date = str(benchmark_frame["date"].max().date()) if not benchmark_frame.empty else ""
    rows = []
    for symbol, frame in candidates.groupby("symbol"):
        frame = frame.sort_values("date")
        latest = frame.iloc[-1]
        week = _weekly_close(frame)
        sma, rising = _sma30(week)
        above = (float(week.iloc[-1]) / sma - 1.0) * 100.0 if sma else None
        r13, r26, r52 = _return(week, 13), _return(week, 26), _return(week, 52)
        rs13 = rs26 = None
        if not benchmark_week.empty:
            common = pd.concat([week.rename("candidate"), benchmark_week.rename("benchmark")], axis=1).dropna()
            if len(common) > 13:
                rs13 = _return(common["candidate"], 13) - _return(common["benchmark"], 13)
            if len(common) > 26:
                rs26 = _return(common["candidate"], 26) - _return(common["benchmark"], 26)
        stage_proxy = above is not None and above > 0 and rising is True
        rs_positive = rs13 is not None and rs26 is not None and rs13 > 0 and rs26 > 0
        if stage_proxy and rs_positive:
            priority = "priority_for_manual_review"
        elif stage_proxy:
            priority = "trend_candidate_RS_unconfirmed_or_weak"
        elif above is not None and above > -5 and rising is True:
            priority = "watch_near_30w_MA"
        else:
            priority = "not_current_Stage2_proxy"
        m = meta.loc[symbol] if symbol in meta.index else {}
        rows.append({
            "symbol": symbol,
            "country": "Japan",
            "sector_or_theme": m.get("sector_or_theme", "") if hasattr(m, "get") else "",
            "instrument_scope": m.get("instrument_scope", "") if hasattr(m, "get") else "",
            "bars": int(len(frame)),
            "first_date": str(frame["date"].min().date()),
            "latest_date": str(latest["date"].date()),
            "latest_close": float(latest["close"]),
            "pct_vs_30w_sma": round(above, 2) if above is not None else "",
            "30w_sma_rising_over_4w": rising if rising is not None else "",
            "return_13w_pct": round(r13, 2) if r13 is not None else "",
            "return_26w_pct": round(r26, 2) if r26 is not None else "",
            "return_52w_pct": round(r52, 2) if r52 is not None else "",
            "relative_strength_13w_vs_EWJ_pct_points": round(rs13, 2) if rs13 is not None else "",
            "relative_strength_26w_vs_EWJ_pct_points": round(rs26, 2) if rs26 is not None else "",
            "EWJ_latest_date": benchmark_date,
            "avg_daily_volume_60d": round(float(frame["volume"].tail(60).mean()), 0) if frame["volume"].notna().any() else "",
            "screen_priority": priority,
            "dashboard_status": m.get("dashboard_status", "") if hasattr(m, "get") else "",
            "activation_status": "inactive_research_only",
            "limitations": "Screening proxy only; thematic funds are not automatically broad sectors. Verify official index scope, adjusted-price quality, liquidity, Korean broker access, and data-use rights before activation.",
        })
    result = pd.DataFrame(rows)
    if not result.empty:
        order = {"priority_for_manual_review": 0, "trend_candidate_RS_unconfirmed_or_weak": 1,
                 "watch_near_30w_MA": 2, "not_current_Stage2_proxy": 3}
        result["_order"] = result["screen_priority"].map(order).fillna(9)
        result["_rs"] = pd.to_numeric(result["relative_strength_13w_vs_EWJ_pct_points"], errors="coerce")
        result["_ma"] = pd.to_numeric(result["pct_vs_30w_sma"], errors="coerce")
        result = result.sort_values(["_order", "_rs", "_ma"], ascending=[True, False, False], na_position="last")
        result = result.drop(columns=["_order", "_rs", "_ma"])
    return result.reset_index(drop=True)


def main() -> int:
    candidate = pd.read_csv(CANDIDATE_PATH, dtype={"symbol": str})
    active = pd.read_csv(ACTIVE_PATH, dtype={"symbol": str})
    metadata = pd.read_csv(METADATA_PATH, dtype={"symbol": str}).fillna("")
    report = build_review(candidate, active, metadata)
    report.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(report)} inactive Japan candidate review rows to {OUTPUT_PATH.name}")
    if not report.empty:
        print(report[["symbol", "sector_or_theme", "pct_vs_30w_sma", "30w_sma_rising_over_4w",
                      "relative_strength_13w_vs_EWJ_pct_points", "relative_strength_26w_vs_EWJ_pct_points",
                      "screen_priority"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
