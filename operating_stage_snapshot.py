"""Prepare the operating Stage data shared by the dashboard and analysis menus."""
from datetime import datetime
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from candidate_stage_integration import extend_universe_with_approved_candidates
from market_data import filter_incomplete_daily_bars, normalize_ohlcv
from stage_engine import weekly_bars, weekly_stage_metrics
from universe import read_universe
from us_research_snapshot import cache_path, read_snapshot, source_revision, write_snapshot


FRAMES = ("screen.feather", "weekly.feather")
CALENDARS = {
    "NYS": "XNYS", "NAS": "XNYS", "AMS": "XNYS",
    "KRX": "XKRX", "KOSDAQ": "XKRX", "KOSPI": "XKRX", "CRYPTO": "CRYPTO",
}


def saved_price_versions(data_dir):
    versions = []
    for name in ("daily_prices.csv", "daily_prices_status.json", "crypto_daily_prices.csv",
                 "candidate_daily_prices.csv", "monitoring_universe.csv", "stock_universe_candidates.csv"):
        try:
            stat = (data_dir / name).stat()
            versions.append((stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size))
        except FileNotFoundError:
            versions.append(None)
    return tuple(versions)


def snapshot_key(universe, prices, as_of):
    root = Path(__file__).resolve().parent
    paths = (root / name for name in ("operating_stage_snapshot.py", "stage_engine.py"))
    files = tuple((str(path), path.stat().st_mtime_ns, path.stat().st_size) for path in paths)
    digest = sha256(json.dumps(
        (as_of, source_revision(files), pd.__version__, version("exchange-calendars"))
    ).encode())
    for frame in (universe, prices):
        digest.update(json.dumps(list(zip(frame.columns, frame.dtypes.astype(str)))).encode())
        digest.update(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes())
    return digest.hexdigest()


def build_stage(universe, prices, latest_dates, as_of):
    calendars = {
        str(row.symbol): CALENDARS.get(str(getattr(row, "exchange", "")).upper())
        for row in universe.itertuples(index=False)
    }
    weekly = {}
    for symbol, daily in prices.groupby("symbol"):
        bars = weekly_bars(daily, as_of_date=as_of, calendar_name=calendars.get(str(symbol)))
        if bars is not None:
            weekly[symbol] = bars
    rows = []
    for _, item in universe.iterrows():
        symbol = item.symbol
        if symbol in weekly:
            weekly[symbol], metrics = weekly_stage_metrics(
                symbol, item.asset_type, item.market_benchmark, item.sector_benchmark,
                weekly[symbol], weekly, latest_dates, as_of_date=as_of,
            )
            rows.append({**item.to_dict(), **metrics})
    return pd.DataFrame(rows), weekly


def operating_stage(universe, prices, as_of, *, snapshot_path=None):
    latest_dates = prices.groupby("symbol")["date"].max().to_dict()
    key = snapshot_key(universe, prices, as_of) if snapshot_path is not None else None
    if key:
        cached = read_snapshot(snapshot_path, key, names=FRAMES)
        if cached is not None:
            screen, bars = cached
            if {"symbol", "last_daily_date", "stage_label"} <= set(screen) and {
                "symbol", "date", "ma30", "close"
            } <= set(bars) and set(screen.symbol) <= set(bars.symbol):
                weekly = {
                    symbol: group.drop(columns="symbol").reset_index(drop=True)
                    for symbol, group in bars.groupby("symbol", sort=False)
                }
                return screen, weekly, latest_dates
    screen, weekly = build_stage(universe, prices, latest_dates, as_of)
    if key and not screen.empty:
        bars = pd.concat(
            [frame.assign(symbol=symbol) for symbol, frame in weekly.items()], ignore_index=True,
        )
        write_snapshot(snapshot_path, key, (screen, bars), names=FRAMES)
    return screen, weekly, latest_dates


def load_saved_inputs(data_dir, now):
    """Build only from the same approved files used by the default app view."""
    universe = read_universe(data_dir / "monitoring_universe.csv")
    base_symbols = set(universe.symbol)
    prices = normalize_ohlcv(pd.read_csv(data_dir / "daily_prices.csv"))
    candidate_path = data_dir / "stock_universe_candidates.csv"
    if candidate_path.exists():
        registry = pd.read_csv(candidate_path, dtype={"symbol": "string"})
        status = registry.get("activation_status", pd.Series(index=registry.index, dtype="string"))
        active = registry[status.fillna("").str.strip().str.lower().eq("active")]
        if not active.empty:
            candidate_prices = normalize_ohlcv(pd.read_csv(data_dir / "candidate_daily_prices.csv"))
            universe, _ = extend_universe_with_approved_candidates(
                universe, active, pd.concat([prices, candidate_prices], ignore_index=True),
                latest_snapshot_date=prices.date.max(),
            )
            prices = pd.concat(
                [prices, candidate_prices[candidate_prices.symbol.isin(set(universe.symbol) - base_symbols)]],
                ignore_index=True,
            )
    crypto_path = data_dir / "crypto_daily_prices.csv"
    if crypto_path.exists():
        prices = pd.concat([prices, normalize_ohlcv(pd.read_csv(crypto_path))], ignore_index=True)
    exchanges = dict(zip(universe.symbol, universe.exchange))
    prices = normalize_ohlcv(filter_incomplete_daily_bars(prices, exchanges, now_kst=now))
    return universe[universe.symbol.isin(prices.symbol)].copy(), prices


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent / "data"
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    versions = saved_price_versions(data_dir)
    universe, prices = load_saved_inputs(data_dir, now)
    if versions != saved_price_versions(data_dir):
        raise SystemExit("Saved prices changed during Stage preparation")
    screen, _, _ = operating_stage(
        universe, prices, pd.Timestamp.today().date().isoformat(),
        snapshot_path=cache_path(data_dir, scope="operating"),
    )
    if screen.empty:
        raise SystemExit("No eligible operating Stage rows")
    print(f"Prepared Stage for {len(screen):,} operating assets.")
