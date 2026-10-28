"""Build a review-only Stage/relative-strength screen for inactive China ETF candidates."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
CANDIDATE_PATH = ROOT / "data" / "china_candidate_prices.csv"
ACTIVE_PATH = ROOT / "data" / "daily_prices.csv"
UNIVERSE_PATH = ROOT / "data" / "monitoring_universe.csv"
OUTPUT_PATH = ROOT / "data" / "china_candidate_screening_review.csv"
BENCHMARK = "MCHI"


def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["date", "symbol", "close", "volume"])
    d = frame.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]
    required = {"date", "symbol", "close"}
    if not required.issubset(d.columns):
        raise ValueError("Price file must include date, symbol, and close columns.")
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d["symbol"] = d["symbol"].fillna("").astype(str).str.strip().str.upper()
    d["close"] = pd.to_numeric(d["close"], errors="coerce")
    if "volume" not in d.columns:
        d["volume"] = float("nan")
    else:
        d["volume"] = pd.to_numeric(d["volume"], errors="coerce")
    return d.dropna(subset=["date", "close"]).loc[lambda x: x["symbol"].ne("") & x["close"].gt(0)]


def _weekly_close(frame: pd.DataFrame, as_of_date=None) -> pd.Series:
    """Return Friday-ending weekly closes, excluding an incomplete current week."""
    d = frame.sort_values("date").set_index("date")["close"]
    weekly = d.resample("W-FRI").last().dropna()
    if weekly.empty or frame.empty:
        return weekly

    as_of = pd.Timestamp(as_of_date).normalize() if as_of_date is not None else pd.Timestamp.today().normalize()
    latest_source_date = pd.to_datetime(frame["date"], errors="coerce").dropna().max()
    if pd.isna(latest_source_date):
        return weekly.iloc[0:0]
    latest_source_date = pd.Timestamp(latest_source_date).normalize()
    week_start = as_of - pd.Timedelta(days=as_of.weekday())
    week_friday = week_start + pd.Timedelta(days=4)

    # During Monday-Friday, W-FRI labels partial current-week data as Friday.
    # Exclude that bucket. On weekends, also exclude it if the latest available
    # session ended before Thursday (likely stale data or a holiday-shortened week).
    if week_start <= latest_source_date <= as_of:
        incomplete = as_of.weekday() < 5 or latest_source_date.weekday() < 3
        if incomplete:
            weekly = weekly[weekly.index.normalize() < week_friday]
    elif latest_source_date < week_start and latest_source_date.weekday() < 4:
        latest_week_friday = latest_source_date + pd.Timedelta(days=4 - latest_source_date.weekday())
        weekly = weekly[weekly.index.normalize() < latest_week_friday]

    return weekly[weekly.index.normalize() <= as_of]


def _return(series: pd.Series, weeks: int) -> float | None:
    if len(series) <= weeks:
        return None
    start, end = float(series.iloc[-weeks - 1]), float(series.iloc[-1])
    return (end / start - 1.0) * 100.0 if start > 0 else None


def _sma30(series: pd.Series) -> tuple[float | None, bool | None]:
    if len(series) < 34:
        return None, None
    ma = series.rolling(30).mean()
    latest = float(ma.iloc[-1])
    prior = float(ma.iloc[-5])
    return latest, latest > prior


def build_review(candidate_prices: pd.DataFrame, active_prices: pd.DataFrame,
                 universe: pd.DataFrame, as_of_date=None) -> pd.DataFrame:
    candidates = _normalize(candidate_prices)
    active = _normalize(active_prices)
    uni = universe.copy()
    uni.columns = [str(c).strip().lower() for c in uni.columns]
    for col in ("symbol", "name", "sector", "active", "exchange"):
        if col not in uni.columns:
            uni[col] = ""
    uni["symbol"] = uni["symbol"].astype(str).str.strip().str.upper()
    metadata = uni.set_index("symbol", drop=False).to_dict("index")
    benchmark = active[active["symbol"].eq(BENCHMARK)]
    b_week = _weekly_close(benchmark, as_of_date=as_of_date) if not benchmark.empty else pd.Series(dtype=float)
    b_latest = str(benchmark["date"].max().date()) if not benchmark.empty else ""

    # Correlation is only used to flag overlapping proxies, not to pick a winner alone.
    pair_groups = [
        ({"512480", "512760"}, "semiconductors"),
        ({"512700", "512800"}, "banks"),
        ({"512010", "512170"}, "healthcare"),
    ]
    rows = []
    for symbol, frame in candidates.groupby("symbol"):
        frame = frame.sort_values("date")
        latest = frame.iloc[-1]
        week = _weekly_close(frame, as_of_date=as_of_date)
        sma, rising = _sma30(week)
        above = (float(latest["close"]) / sma - 1.0) * 100.0 if sma else None
        r13, r26, r52 = _return(week, 13), _return(week, 26), _return(week, 52)
        aligned13 = aligned26 = None
        if not b_week.empty:
            common = pd.concat([week.rename("candidate"), b_week.rename("benchmark")], axis=1).dropna()
            aligned13 = _return(common["candidate"], 13) - _return(common["benchmark"], 13) if len(common) > 13 else None
            aligned26 = _return(common["candidate"], 26) - _return(common["benchmark"], 26) if len(common) > 26 else None
        corr_group = ""
        corr_value = None
        for group, label in pair_groups:
            if symbol in group:
                corr_group = label
                other = next(iter(group - {symbol}))
                other_frame = candidates[candidates["symbol"].eq(other)].sort_values("date")
                joined = frame[["date", "close"]].merge(
                    other_frame[["date", "close"]], on="date", suffixes=("_a", "_b")
                ).sort_values("date")
                if len(joined) > 2:
                    ra = joined["close_a"].pct_change().dropna()
                    rb = joined["close_b"].pct_change().dropna()
                    pair = pd.concat([ra.rename("a"), rb.rename("b")], axis=1).dropna()
                    if len(pair) > 20:
                        corr_value = float(pair["a"].corr(pair["b"]))
                break
        meta = metadata.get(symbol, {})
        stage_proxy = bool(above is not None and above > 0 and rising is True)
        rs_positive = aligned13 is not None and aligned26 is not None and aligned13 > 0 and aligned26 > 0
        if stage_proxy and rs_positive:
            priority = "priority_for_manual_review"
        elif stage_proxy:
            priority = "trend_candidate_RS_unconfirmed_or_weak"
        elif above is not None and above > -5 and rising is True:
            priority = "watch_near_30w_MA"
        else:
            priority = "not_current_Stage2_proxy"
        rows.append({
            "symbol": symbol,
            "name": meta.get("name", ""),
            "sector": meta.get("sector", ""),
            "active": str(meta.get("active", "false")).lower(),
            "exchange": meta.get("exchange", ""),
            "bars": int(len(frame)),
            "first_date": str(frame["date"].min().date()),
            "latest_date": str(latest["date"].date()),
            "latest_close": float(latest["close"]),
            "pct_vs_30w_sma": round(above, 2) if above is not None else "",
            "30w_sma_rising_over_4w": rising if rising is not None else "",
            "return_13w_pct": round(r13, 2) if r13 is not None else "",
            "return_26w_pct": round(r26, 2) if r26 is not None else "",
            "return_52w_pct": round(r52, 2) if r52 is not None else "",
            "relative_strength_13w_vs_MCHI_pct_points": round(aligned13, 2) if aligned13 is not None else "",
            "relative_strength_26w_vs_MCHI_pct_points": round(aligned26, 2) if aligned26 is not None else "",
            "MCHI_latest_date": b_latest,
            "duplicate_group": corr_group,
            "duplicate_daily_return_correlation": round(corr_value, 4) if corr_value is not None else "",
            "avg_daily_volume_60d": round(float(frame["volume"].tail(60).mean()), 0) if frame["volume"].notna().any() else "",
            "screen_priority": priority,
            "activation_status": "inactive_research_only",
            "limitations": "Screening proxy only; verify official product identity, adjusted-price quality, benchmark mapping, liquidity, and data-use rights before activation.",
        })
    result = pd.DataFrame(rows)
    if not result.empty:
        priority_order = {
            "priority_for_manual_review": 0,
            "trend_candidate_RS_unconfirmed_or_weak": 1,
            "watch_near_30w_MA": 2,
            "not_current_Stage2_proxy": 3,
        }
        result["_priority_order"] = result["screen_priority"].map(priority_order).fillna(9)
        result["_rs_sort"] = pd.to_numeric(
            result["relative_strength_13w_vs_MCHI_pct_points"], errors="coerce"
        )
        result["_ma_sort"] = pd.to_numeric(result["pct_vs_30w_sma"], errors="coerce")
        result = result.sort_values(
            ["_priority_order", "_rs_sort", "_ma_sort"],
            ascending=[True, False, False], na_position="last"
        ).drop(columns=["_priority_order", "_rs_sort", "_ma_sort"])
    return result.reset_index(drop=True)


def main() -> int:
    candidate = pd.read_csv(CANDIDATE_PATH, dtype={"symbol": str})
    active = pd.read_csv(ACTIVE_PATH, dtype={"symbol": str})
    universe = pd.read_csv(UNIVERSE_PATH, dtype={"symbol": str}).fillna("")
    report = build_review(candidate, active, universe)
    report.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(report)} inactive China candidate review rows to {OUTPUT_PATH.name}")
    print(report[["symbol", "sector", "pct_vs_30w_sma", "30w_sma_rising_over_4w",
                  "relative_strength_13w_vs_MCHI_pct_points", "relative_strength_26w_vs_MCHI_pct_points",
                  "screen_priority"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
