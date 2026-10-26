import pandas as pd

from yahoo_market_cap_supplement import collect_yahoo_market_caps


def _candidates():
    return pd.DataFrame([
        {"symbol": "AAA", "market": "United States", "exchange": "NAS", "instrument_type": "common_stock_candidate"},
        {"symbol": "BBB", "market": "United States", "exchange": "NYS", "instrument_type": "adr_candidate"},
        {"symbol": "000660", "market": "South Korea", "exchange": "KRX", "instrument_type": "common_stock_candidate_unverified"},
        {"symbol": "CCC", "market": "United States", "exchange": "AMS", "instrument_type": "common_stock_candidate_unverified"},
    ])


class FakeTicker:
    def __init__(self, info):
        self.info = info

    def get_info(self):
        return self.info


def test_only_us_common_stock_candidates_are_queried_and_usd_cap_is_converted_to_billions():
    seen = []

    def factory(symbol):
        seen.append(symbol)
        return FakeTicker({"currency": "USD", "marketCap": 12_500_000_000, "quoteType": "EQUITY", "regularMarketTime": 1792790400})

    result = collect_yahoo_market_caps(_candidates(), factory, "2026-10-26T00:00:00+00:00")

    assert seen == ["AAA", "CCC"]
    assert result["market_cap_usd_b_secondary"].tolist() == [12.5, 12.5]
    assert result["market_cap_status"].tolist() == ["not_verified", "not_verified"]
    assert result["source_url"].str.startswith("https://finance.yahoo.com/quote/").all()


def test_non_usd_cap_is_not_mislabelled_as_usd():
    def factory(symbol):
        return FakeTicker({"currency": "KRW", "marketCap": 9_000_000_000_000})

    result = collect_yahoo_market_caps(_candidates(), factory)

    assert result["market_cap_usd_b_secondary"].eq("").all()
    assert result["observation_status"].eq("observed_non_usd_not_converted").all()


def test_request_errors_are_recorded_and_do_not_stop_other_candidates():
    def factory(symbol):
        if symbol == "AAA":
            raise RuntimeError("temporary failure")
        return FakeTicker({"currency": "USD", "marketCap": 2_000_000_000})

    result = collect_yahoo_market_caps(_candidates(), factory)

    assert result.loc[result["symbol"].eq("AAA"), "observation_status"].item() == "request_failed"
    assert result.loc[result["symbol"].eq("CCC"), "market_cap_usd_b_secondary"].item() == 2.0


def test_missing_required_input_columns_raise_clear_error():
    try:
        collect_yahoo_market_caps(pd.DataFrame({"symbol": ["AAA"]}), lambda symbol: FakeTicker({}))
    except ValueError as exc:
        assert "market" in str(exc)
    else:
        raise AssertionError("Expected missing-column validation")
