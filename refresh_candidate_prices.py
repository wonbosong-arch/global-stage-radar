"""Refresh pending candidate price history into a separate review-only file."""
from __future__ import annotations
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from data_providers import KISUSProvider, KISKoreaProvider
from kis_provider import KISOverseasPrices
from kis_domestic_provider import KISDomesticPrices
from market_data import completed_bar_cutoff_date

ROOT = Path(__file__).resolve().parent
CANDIDATES = ROOT / "data" / "stock_universe_candidates.csv"
UNIVERSE = ROOT / "data" / "monitoring_universe.csv"
PRICES = ROOT / "data" / "candidate_daily_prices.csv"
STATUS = ROOT / "data" / "candidate_daily_prices_status.json"


def filter_candidate_completed_bars(frame, exchange_by_symbol, now_kst):
    """Reject invalid/future dates and incomplete local sessions, including old snapshots."""
    result = frame.copy()
    if result.empty:
        return result
    result["symbol"] = result["symbol"].astype(str).str.strip().str.upper()
    result["date"] = pd.to_datetime(result["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    allowed = result["date"].notna() & result["date"].le(now_kst.date().isoformat())
    for symbol, exchange in exchange_by_symbol.items():
        mask = result["symbol"].eq(symbol)
        cutoff = completed_bar_cutoff_date(exchange, now_kst=now_kst)
        allowed.loc[mask] &= result.loc[mask, "date"].le(cutoff)
    return result.loc[allowed].reset_index(drop=True)


def fetch_candidate_daily(row, us_provider, korea_provider, max_pages=3):
    """Fetch a candidate using its listing venue, not its issuer country."""
    requested_exchange = str(row.exchange).strip().upper()
    if requested_exchange == "KRX":
        bars = korea_provider.fetch_daily(
            row.symbol, market="South Korea", asset_type=row.asset_type,
            exchange="KRX", max_pages=max_pages
        )
        return bars, "KRX"
    bars = us_provider.fetch_daily(
        row.symbol, market="United States", asset_type="stock",
        exchange=requested_exchange, max_pages=max_pages
    )
    return bars, requested_exchange


def merge_listing_transfer_history(
    current_bars: pd.DataFrame,
    prior_exchange_bars: pd.DataFrame,
    transfer_date: str = "2026-10-05",
) -> tuple[pd.DataFrame, int]:
    """Join documented pre-transfer venue history with current venue bars, current rows winning duplicates."""
    current = current_bars.copy()
    prior = prior_exchange_bars.copy()
    if current.empty or prior.empty or "date" not in current.columns or "date" not in prior.columns:
        return current, 0

    current["date"] = pd.to_datetime(current["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    prior["date"] = pd.to_datetime(prior["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    current = current.dropna(subset=["date"])
    prior = prior.dropna(subset=["date"])
    cutoff = pd.Timestamp(transfer_date).strftime("%Y-%m-%d")
    prior = prior[prior["date"] < cutoff].copy()
    if prior.empty:
        return current, 0

    current_dates = set(current["date"].astype(str))
    rows_added = len(set(prior["date"].astype(str)) - current_dates)
    combined = pd.concat([prior, current], ignore_index=True, sort=False)
    if "symbol" in combined.columns:
        combined["symbol"] = combined["symbol"].astype(str).str.strip().str.upper()
        combined = combined.drop_duplicates(["symbol", "date"], keep="last")
    else:
        combined = combined.drop_duplicates(["date"], keep="last")
    combined = combined.sort_values("date").reset_index(drop=True)
    return combined, rows_added


def history_pages_for_candidate(symbol: str, prior_row_counts: dict[str, int], max_pages_new: int = 3) -> int:
    """Fetch more history only for candidates whose stored history is below the Stage gate."""
    normalized = str(symbol).strip().upper()
    if normalized not in prior_row_counts:
        return max_pages_new
    if int(prior_row_counts.get(normalized, 0) or 0) < 150:
        return 5
    return 1


def preserve_failed_symbol_history(
    fresh: pd.DataFrame,
    errors: list[dict],
    previous_path: Path = PRICES,
) -> tuple[pd.DataFrame, list[str]]:
    """Keep history for failed or partially refreshed symbols; fresh rows win duplicates."""
    failed_symbols = {
        str(item.get("symbol", "")).strip().upper()
        for item in errors
        if str(item.get("symbol", "")).strip() not in {"", "*"}
    }
    fresh_frame = fresh.copy()
    if not previous_path.exists():
        return fresh_frame, []

    previous = pd.read_csv(previous_path, dtype={"symbol": str})
    if previous.empty or not {"symbol", "date"}.issubset(previous.columns):
        return fresh_frame, []

    previous["symbol"] = previous["symbol"].astype(str).str.strip().str.upper()
    fresh_symbols = (
        set(fresh_frame["symbol"].astype(str).str.strip().str.upper())
        if "symbol" in fresh_frame.columns else set()
    )
    symbols_to_preserve = failed_symbols | fresh_symbols
    if not symbols_to_preserve:
        return fresh_frame, []

    preserved_rows = previous[previous["symbol"].isin(symbols_to_preserve)].copy()
    preserved_symbols = sorted(
        set(preserved_rows["symbol"].unique().tolist()) & failed_symbols
    )
    if preserved_rows.empty:
        return fresh_frame, []

    combined = pd.concat([preserved_rows, fresh_frame], ignore_index=True, sort=False)
    combined["symbol"] = combined["symbol"].astype(str).str.strip().str.upper()
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    combined = combined.dropna(subset=["date"])
    combined = combined.drop_duplicates(["symbol", "date"], keep="last")
    combined = combined.sort_values(["symbol", "date"]).reset_index(drop=True)
    return combined, preserved_symbols


def main() -> int:
    key, secret = os.environ.get("KIS_APP_KEY", ""), os.environ.get("KIS_APP_SECRET", "")
    if not key or not secret:
        raise RuntimeError("Repository secrets KIS_APP_KEY and KIS_APP_SECRET are required.")
    candidates = pd.read_csv(CANDIDATES, dtype={"symbol": str})
    universe = pd.read_csv(UNIVERSE, dtype={"symbol": str})
    # Fill only textual columns; blanket fillna("") on numeric columns emits
    # pandas compatibility warnings and may become an error in future releases.
    for frame in (candidates, universe):
        text_columns = frame.select_dtypes(include=["object", "string"]).columns
        frame[text_columns] = frame[text_columns].fillna("")
    active = set(universe["symbol"].str.strip().str.upper())
    candidates = candidates[candidates["activation_status"].eq("pending_review")].copy()
    candidates["symbol"] = candidates["symbol"].str.strip().str.upper()
    candidates = candidates[~candidates["symbol"].isin(active)].drop_duplicates("symbol")
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    exchange_by_symbol = {
        row.symbol: str(row.exchange).strip().upper()
        for row in candidates.itertuples(index=False)
    }
    us_provider = KISUSProvider(KISOverseasPrices(app_key=key, app_secret=secret))
    korea_provider = KISKoreaProvider(KISDomesticPrices(app_key=key, app_secret=secret))
    prior_row_counts: dict[str, int] = {}
    if PRICES.exists():
        try:
            prior_snapshot = pd.read_csv(PRICES, dtype={"symbol": str}, usecols=["symbol", "date"])
            prior_snapshot["symbol"] = prior_snapshot["symbol"].astype(str).str.strip().str.upper()
            prior_row_counts = (
                prior_snapshot.dropna(subset=["date"])
                .groupby("symbol")["date"].nunique().astype(int).to_dict()
            )
        except (OSError, ValueError, pd.errors.ParserError):
            prior_row_counts = {}
    frames, errors, fresh_data_symbols, provider_observations = [], [], [], []
    for i, row in enumerate(candidates.itertuples(index=False)):
        try:
            # Existing Stage-ready histories need only a recent page. Retry short histories
            # more deeply; new candidates get the standard initial backfill.
            max_pages = history_pages_for_candidate(row.symbol, prior_row_counts)
            bars, exchange_used = fetch_candidate_daily(row, us_provider, korea_provider, max_pages=max_pages)
            history_extension_status = "not_applicable"
            history_extension_rows_added = 0
            history_extension_source_url = ""
            # Energy Transfer moved its unchanged ET ticker from NYSE to TXSE on
            # 2026-10-05. KIS currently returns only post-transfer rows via the
            # candidate's AMS route, so retain documented pre-transfer NYSE history.
            if str(row.symbol).strip().upper() == "ET" and str(row.exchange).strip().upper() == "AMS" and len(bars) < 150:
                history_extension_source_url = "https://ir.energytransfer.com/news-releases/news-release-details/energy-transfer-transfer-stock-exchange-listings-texas-stock"
                try:
                    prior_venue_bars = us_provider.client.daily_bars(
                        str(row.symbol).strip().upper(),
                        exchange="NYS",
                        end_date="20261002",
                        max_pages=5,
                    )
                    bars, history_extension_rows_added = merge_listing_transfer_history(
                        bars, prior_venue_bars, transfer_date="2026-10-05"
                    )
                    history_extension_status = (
                        "pre_transfer_history_added" if history_extension_rows_added > 0
                        else "no_pre_transfer_history_returned"
                    )
                    if history_extension_rows_added > 0:
                        exchange_used = "AMS_current+NYS_pre_transfer"
                except Exception as history_exc:
                    # Preserve current venue data even if the historical venue query fails.
                    history_extension_status = f"historical_query_failed:{type(history_exc).__name__}"
            response_was_empty = bars.empty
            bars = filter_candidate_completed_bars(
                bars, {row.symbol: exchange_by_symbol[row.symbol]}, now_kst
            )
            if bars.empty:
                errors.append({"symbol": row.symbol, "error": (
                    "empty_response" if response_was_empty else "no_completed_daily_bars"
                )})
            else:
                frames.append(bars)
                fresh_data_symbols.append(row.symbol)
                parsed_dates = pd.to_datetime(bars["date"], errors="coerce") if "date" in bars.columns else pd.Series(dtype="datetime64[ns]")
                provider_observations.append({
                    "symbol": row.symbol,
                    "requested_exchange": str(row.exchange).strip().upper(),
                    "response_exchange": exchange_used,
                    "response_rows": int(bars["date"].nunique()) if "date" in bars.columns else int(len(bars)),
                    "latest_response_date": parsed_dates.max().strftime("%Y-%m-%d") if parsed_dates.notna().any() else None,
                    "history_extension_status": history_extension_status,
                    "history_extension_rows_added": history_extension_rows_added,
                    "history_extension_source_url": history_extension_source_url,
                    "observation_scope": "price_response_only_not_identity_verification",
                })
        except Exception as exc:
            errors.append({"symbol": row.symbol, "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
        if i + 1 < len(candidates):
            time.sleep(0.75)
    fresh = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"])
    fresh, preserved = preserve_failed_symbol_history(fresh, errors, previous_path=PRICES)
    if fresh.empty:
        # Record the failed attempt while preserving any prior snapshot.
        if PRICES.exists():
            fresh = pd.read_csv(PRICES, dtype={"symbol": str}).fillna("")
        else:
            fresh = pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"])
    fresh["symbol"] = fresh["symbol"].astype(str).str.strip().str.upper()
    # Filtering responses alone is insufficient: older snapshots may contain
    # partial/future bars, and failed refreshes deliberately retain their history.
    fresh = filter_candidate_completed_bars(fresh, exchange_by_symbol, now_kst)
    preserved = sorted(set(preserved) & set(fresh["symbol"]))
    if not fresh.empty:
        fresh["date"] = pd.to_datetime(fresh["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        fresh = fresh.dropna(subset=["date"]).drop_duplicates(["symbol", "date"]).sort_values(["symbol", "date"])
    # Replace snapshots atomically so an interrupted write cannot leave a partial CSV.
    prices_tmp = PRICES.with_suffix(PRICES.suffix + ".tmp")
    fresh.to_csv(prices_tmp, index=False)
    os.replace(prices_tmp, PRICES)
    coverage = []
    for symbol, group in fresh.groupby("symbol"):
        dates = pd.to_datetime(group["date"], errors="coerce").dropna()
        coverage.append({"symbol": symbol, "rows": int(group["date"].nunique()), "first_date": dates.min().strftime("%Y-%m-%d") if not dates.empty else None, "latest_date": dates.max().strftime("%Y-%m-%d") if not dates.empty else None})
    status = {"updated_at_utc": datetime.now(timezone.utc).isoformat(), "updated_at_kst": datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Seoul")).isoformat(), "requested_symbols": int(len(candidates)), "symbols_with_data": int(fresh["symbol"].nunique()), "fresh_data_symbols": sorted(set(fresh_data_symbols)), "fresh_data_symbol_count": len(set(fresh_data_symbols)), "failed_symbols": sorted({item["symbol"] for item in errors if item.get("symbol") != "*"}), "symbols_preserved_from_previous_snapshot": preserved, "error_count": len(errors), "errors": errors, "per_symbol_coverage": coverage, "provider_observations": provider_observations, "data_note": "Separate manual review snapshot; exchange response metadata is diagnostic only and never verifies identity or activates candidates."}
    # Publish status atomically; readers see either the previous complete status or this complete status.
    status_tmp = STATUS.with_suffix(STATUS.suffix + ".tmp")
    status_tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(status_tmp, STATUS)
    print(json.dumps({k: v for k, v in status.items() if k != "errors"}, ensure_ascii=False))
    if errors:
        print("Per-symbol errors:", json.dumps(errors, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
