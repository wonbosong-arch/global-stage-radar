import pandas as pd
import pytest

from approved_stock_universe import approved_candidates_for_stage


def _candidate(**overrides):
    row = {
        "symbol": "AAPL", "name": "Apple Inc.", "market": "United States",
        "sector": "Information Technology", "asset_type": "stock",
        "market_benchmark": "SPY", "sector_benchmark": "XLK",
        "exchange": "NAS", "activation_status": "pending_review",
        "market_cap_usd": 3_000_000_000_000,
        "market_cap_usd_b_secondary": 3_100_000_000_000,
    }
    row.update(overrides)
    return row


def test_pending_candidate_never_enters_stage_universe():
    result = approved_candidates_for_stage(pd.DataFrame([_candidate()]))
    assert result.empty


def test_only_explicitly_active_candidate_enters_stage_universe():
    result = approved_candidates_for_stage(pd.DataFrame([
        _candidate(),
        _candidate(symbol="MSFT", name="Microsoft", activation_status="active"),
    ]))
    assert result["symbol"].tolist() == ["MSFT"]
    assert result.loc[0, "market_cap_usd"] == 3_000_000_000_000


def test_secondary_yahoo_cap_is_not_used_as_verified_cap():
    row = _candidate(activation_status="active")
    row.pop("market_cap_usd")
    result = approved_candidates_for_stage(pd.DataFrame([row]))
    assert pd.isna(result.loc[0, "market_cap_usd"])


def test_active_stock_requires_sector_benchmark():
    with pytest.raises(ValueError, match="Stage mapping"):
        approved_candidates_for_stage(pd.DataFrame([
            _candidate(activation_status="active", sector_benchmark="")
        ]))


def test_duplicate_active_symbols_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        approved_candidates_for_stage(pd.DataFrame([
            _candidate(activation_status="active"),
            _candidate(activation_status="active"),
        ]))
