import pandas as pd

from yahoo_market_cap_supplement import collect_yahoo_market_caps


def _candidates():
    return pd.DataFrame([
        {"symbol": "AAA", "market": "United States", "exchange": "NAS", "instrument_type": "common_stock_candidate"},
        {"symbol": "BBB", "market": "United States", "exchange": "NYS", "instrument_type": "adr_candidate"},
        {"symbol": "000660", "market": "South Korea", "exchange": "KRX", "instrument_type": "common_stock_candidate_unverified"},
        {"symbol": "CCC", "market": "United States", "exchange": "AMS", "instrument_type": "common_stock_candidate_unverified"},
        {"symbol": "DDD", "market": "United States", "exchange": "NAS", "instrument_type": "equity_candidate_unverified"},
        {"symbol": "EEE", "market": "United States", "exchange": "NYS", "instrument_type": "equity_candidate_unverified", "discovery_dr_country_code": "KR"},
        {"symbol": "FFF", "market": "United States", "exchange": "NAS", "instrument_type": "equity_candidate_unverified", "depositary_ratio_status": "verified"},
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

    assert seen == ["AAA", "CCC", "DDD"]
    assert result["market_cap_usd_b_secondary"].tolist() == [12.5, 12.5, 12.5]
    assert result["market_cap_status"].tolist() == ["not_verified", "not_verified", "not_verified"]
    assert result["market_cap_asof"].tolist() == ["", "", ""]
    assert result["market_cap_asof_basis"].tolist() == ["not_provided_by_yahoo"] * 3
    assert result["fetched_at_utc"].tolist() == ["2026-10-26T00:00:00+00:00"] * 3
    assert result["source_url"].str.startswith("https://finance.yahoo.com/quote/").all()


def test_share_class_symbols_use_yahoo_hyphen_format_but_preserve_candidate_symbol():
    candidates = pd.DataFrame([
        {"symbol": "BRK/A", "market": "United States", "exchange": "NYS", "instrument_type": "common_stock_candidate"},
        {"symbol": "BRK/B", "market": "United States", "exchange": "NYS", "instrument_type": "common_stock_candidate"},
    ])
    seen = []

    def factory(symbol):
        seen.append(symbol)
        return FakeTicker({"currency": "USD", "marketCap": 100_000_000_000, "quoteType": "EQUITY"})

    result = collect_yahoo_market_caps(candidates, factory)

    assert seen == ["BRK-A", "BRK-B"]
    assert result["symbol"].tolist() == ["BRK/A", "BRK/B"]
    assert result["source_url"].tolist() == [
        "https://finance.yahoo.com/quote/BRK-A/",
        "https://finance.yahoo.com/quote/BRK-B/",
    ]


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


def test_adr_with_official_ratio_can_receive_secondary_cap_observation_without_verification():
    candidates = pd.DataFrame([
        {"symbol": "HDB", "market": "United States", "exchange": "NYS", "instrument_type": "adr_candidate", "discovery_dr_country_code": "IN"},
        {"symbol": "BAD", "market": "United States", "exchange": "NYS", "instrument_type": "adr_candidate", "discovery_dr_country_code": "IN"},
    ])
    registry = pd.DataFrame([{
        "symbol": "HDB",
        "depositary_ratio_observed": "3",
        "depositary_ratio_basis": "ordinary_shares_per_depositary_share",
        "depositary_ratio_source_url": "https://www.hdfc.bank.in/about-us/investor-relations/adr",
        "status": "official_source_confirmed",
    }])
    seen = []

    def factory(symbol):
        seen.append(symbol)
        return FakeTicker({"currency": "USD", "marketCap": 15_000_000_000, "quoteType": "EQUITY", "fullExchangeName": "NYSE"})

    result = collect_yahoo_market_caps(candidates, factory, "2026-10-26T00:00:00+00:00", adr_ratio_registry=registry)

    assert seen == ["HDB"]
    row = result.iloc[0]
    assert row["symbol"] == "HDB"
    assert row["market_cap_usd_b_secondary"] == 15.0
    assert row["market_cap_status"] == "not_verified"
    assert row["depositary_ratio_status"] == "verified"
    assert row["depositary_ratio_observed"] == "3"
    assert row["depositary_ratio_source_url"] == "https://www.hdfc.bank.in/about-us/investor-relations/adr"


def test_korean_krx_candidate_uses_yahoo_and_converts_krw_cap_to_usd():
    candidates = pd.DataFrame([
        {"symbol": "000660", "market": "South Korea", "exchange": "KRX", "instrument_type": "common_stock_candidate_unverified"},
    ])
    seen = []

    def factory(symbol):
        seen.append(symbol)
        if symbol == "000660.KS":
            return FakeTicker({"currency": "KRW", "marketCap": 400_000_000_000_000, "quoteType": "EQUITY", "fullExchangeName": "KSE"})
        if symbol == "KRW=X":
            return FakeTicker({"regularMarketPrice": 1400.0})
        raise AssertionError(f"Unexpected Yahoo symbol: {symbol}")

    result = collect_yahoo_market_caps(candidates, factory, "2026-10-27T00:00:00+00:00")

    assert seen == ["000660.KS", "KRW=X"]
    row = result.iloc[0]
    assert row["symbol"] == "000660"
    assert row["market_cap_currency"] == "KRW"
    assert row["market_cap_usd_b_secondary"] == 400_000_000_000_000 / 1400 / 1_000_000_000
    assert row["observation_status"] == "observed_usd_fx_converted"
    assert row["market_cap_status"] == "not_verified"
    assert row["source_url"] == "https://finance.yahoo.com/quote/000660.KS/"


def test_missing_required_input_columns_raise_clear_error():
    try:
        collect_yahoo_market_caps(pd.DataFrame({"symbol": ["AAA"]}), lambda symbol: FakeTicker({}))
    except ValueError as exc:
        assert "market" in str(exc)
    else:
        raise AssertionError("Expected missing-column validation")


def test_successful_market_cap_observation_is_reused_within_same_kst_week():
    candidates = pd.DataFrame([
        {"symbol": "AAA", "market": "United States", "exchange": "NAS", "instrument_type": "common_stock_candidate"},
        {"symbol": "NEW", "market": "United States", "exchange": "NYS", "instrument_type": "common_stock_candidate"},
    ])
    previous = pd.DataFrame([{
        "symbol": "AAA",
        "market_cap_usd_b_secondary": "42.0",
        "market_cap_native": "42000000000",
        "market_cap_currency": "USD",
        "market_cap_asof": "",
        "market_cap_asof_basis": "not_provided_by_yahoo",
        "source": "Yahoo Finance",
        "source_url": "https://finance.yahoo.com/quote/AAA/",
        "fetched_at_utc": "2026-10-26T00:00:00+00:00",
        "quote_type": "EQUITY",
        "exchange_name": "NASDAQ",
        "market_cap_status": "not_verified",
        "depositary_ratio_status": "not_applicable",
        "depositary_ratio_observed": "",
        "depositary_ratio_basis": "",
        "depositary_ratio_source_url": "",
        "observation_status": "observed_usd",
        "error": "",
    }])
    seen = []

    def factory(symbol):
        seen.append(symbol)
        return FakeTicker({"currency": "USD", "marketCap": 7_000_000_000})

    result = collect_yahoo_market_caps(
        candidates,
        factory,
        "2026-10-27T00:00:00+00:00",
        previous_observations=previous,
    )

    assert seen == ["NEW"]
    aaa = result.loc[result["symbol"].eq("AAA")].iloc[0]
    assert aaa["market_cap_usd_b_secondary"] == "42.0"
    assert aaa["fetched_at_utc"] == "2026-10-26T00:00:00+00:00"
    assert result.loc[result["symbol"].eq("NEW"), "market_cap_usd_b_secondary"].item() == 7.0

def test_missing_or_invalid_market_cap_observations_retry_within_same_week():
    candidates = pd.DataFrame([
        {"symbol": "MISS", "market": "United States", "exchange": "NAS", "instrument_type": "common_stock_candidate"},
        {"symbol": "INVAL", "market": "United States", "exchange": "NYS", "instrument_type": "common_stock_candidate"},
    ])
    previous = pd.DataFrame([
        {"symbol": "MISS", "fetched_at_utc": "2026-10-26T00:00:00+00:00", "observation_status": "market_cap_missing"},
        {"symbol": "INVAL", "fetched_at_utc": "2026-10-26T00:00:00+00:00", "observation_status": "invalid_market_cap"},
    ])
    seen = []

    def factory(symbol):
        seen.append(symbol)
        return FakeTicker({"currency": "USD", "marketCap": 3_000_000_000})

    result = collect_yahoo_market_caps(
        candidates,
        factory,
        "2026-10-27T00:00:00+00:00",
        previous_observations=previous,
    )

    assert seen == ["MISS", "INVAL"]
    assert result["market_cap_usd_b_secondary"].tolist() == [3.0, 3.0]
    assert result["observation_status"].eq("observed_usd").all()

