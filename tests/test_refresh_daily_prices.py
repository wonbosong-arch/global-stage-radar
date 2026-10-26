import pandas as pd

from refresh_daily_prices import (
    FULL_HISTORY_PAGES,
    LATEST_UPDATE_PAGES,
    merge_daily_snapshots,
    pages_needed,
)


def test_merge_preserves_history_and_prefers_fresh_duplicate_rows():
    existing = pd.DataFrame([
        {"date": "2025-01-01", "symbol": "aaa", "close": 10.0},
        {"date": "2025-01-02", "symbol": "AAA", "close": 11.0},
    ])
    fresh = pd.DataFrame([
        {"date": "2025-01-02", "symbol": "AAA", "close": 12.0},
        {"date": "2025-01-03", "symbol": "AAA", "close": 13.0},
        {"date": "not-a-date", "symbol": "AAA", "close": 99.0},
    ])

    result = merge_daily_snapshots(existing, fresh)

    assert list(result["date"]) == ["2025-01-01", "2025-01-02", "2025-01-03"]
    assert list(result["close"]) == [10.0, 12.0, 13.0]
    assert list(result["symbol"]) == ["AAA", "AAA", "AAA"]


def test_merge_empty_fresh_snapshot_keeps_existing_history():
    existing = pd.DataFrame([
        {"date": "2025-01-01", "symbol": "AAA", "close": 10.0},
    ])

    result = merge_daily_snapshots(existing, pd.DataFrame())

    assert len(result) == 1
    assert result.iloc[0]["close"] == 10.0


def test_page_count_limits_daily_requests_for_established_symbols():
    assert pages_needed(0) == FULL_HISTORY_PAGES
    assert pages_needed(749) == FULL_HISTORY_PAGES
    assert pages_needed(750) == LATEST_UPDATE_PAGES
    assert pages_needed(1000) == LATEST_UPDATE_PAGES
