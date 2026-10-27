import pandas as pd

from yahoo_master_cap_batch import build_coverage_status, collect_bounded_batch, master_to_yahoo_input


def _master():
    return pd.DataFrame([
        {"listing_exchange":"NAS","symbol":"AAA","master_security_type":"2","master_dr_flag":"N","master_dr_country_code":""},
        {"listing_exchange":"NYS","symbol":"BBB","master_security_type":"2","master_dr_flag":"Y","master_dr_country_code":"IN"},
        {"listing_exchange":"AMS","symbol":"ETF","master_security_type":"3","master_dr_flag":"N","master_dr_country_code":""},
        {"listing_exchange":"KRX","symbol":"KR1","master_security_type":"2","master_dr_flag":"N","master_dr_country_code":""},
        {"listing_exchange":"NAS","symbol":"CCC","master_security_type":"2","master_dr_flag":"N","master_dr_country_code":""},
    ])


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    def get_info(self):
        return {"currency":"USD","marketCap":2_000_000_000,"quoteType":"EQUITY"}


def test_master_maps_common_stocks_and_keeps_adrs_separate():
    result = master_to_yahoo_input(_master()).set_index("symbol")
    assert result.loc["AAA", "instrument_type"] == "equity_candidate_unverified"
    assert result.loc["BBB", "instrument_type"] == "adr_candidate"
    assert result.loc["ETF", "instrument_type"] == "unsupported_master_security"
    assert result.loc["BBB", "discovery_dr_country_code"] == "IN"


def test_batch_is_bounded_and_checkpoints_successful_symbols():
    seen = []
    result, stats = collect_bounded_batch(_master(), batch_size=1, ticker_factory=lambda symbol: (seen.append(symbol) or FakeTicker(symbol)))
    assert seen == ["AAA"]
    assert stats["processed_this_run"] == 1
    assert stats["eligible_remaining"] == 1
    assert result["symbol"].tolist() == ["AAA"]
    next_result, next_stats = collect_bounded_batch(_master(), result, batch_size=1, ticker_factory=lambda symbol: FakeTicker(symbol))
    assert next_stats["processed_this_run"] == 1
    assert next_result["symbol"].tolist() == ["AAA", "CCC"]


def test_only_officially_confirmed_adrs_are_queried():
    seen = []
    registry = pd.DataFrame([{
        "symbol":"BBB","depositary_ratio_observed":"2",
        "depositary_ratio_basis":"ordinary_shares_per_depositary_share",
        "depositary_ratio_source_url":"https://example.com/adr","status":"official_source_confirmed",
    }])
    result, stats = collect_bounded_batch(_master(), batch_size=10, ticker_factory=lambda symbol: (seen.append(symbol) or FakeTicker(symbol)), adr_ratio_registry=registry)
    assert set(seen) == {"AAA", "BBB", "CCC"}
    assert result.loc[result["symbol"].eq("BBB"), "market_cap_status"].item() == "not_verified"
    assert stats["processed_this_run"] == 3



def test_triage_never_treats_secondary_cap_as_verified():
    from yahoo_master_cap_batch import build_cap_triage

    master = pd.DataFrame([
        {"listing_exchange":"NAS","symbol":"AAA","master_security_type":"2","master_dr_flag":"N","master_dr_country_code":""},
        {"listing_exchange":"NAS","symbol":"BBB","master_security_type":"2","master_dr_flag":"N","master_dr_country_code":""},
        {"listing_exchange":"NYS","symbol":"CCC","master_security_type":"2","master_dr_flag":"Y","master_dr_country_code":"IN"},
    ])
    observations = pd.DataFrame([
        {"symbol":"AAA","market_cap_usd_b_secondary":2.1,"quote_type":"EQUITY","exchange_name":"NasdaqGS","observation_status":"observed_usd","market_cap_asof":"","market_cap_asof_basis":"not_provided_by_yahoo","source_url":"https://finance.yahoo.com/quote/AAA/","fetched_at_utc":"2026-10-26T00:00:00Z","market_cap_status":"not_verified"},
        {"symbol":"BBB","market_cap_usd_b_secondary":0.4,"quote_type":"EQUITY","exchange_name":"NasdaqGS","observation_status":"observed_usd","market_cap_asof":"","market_cap_asof_basis":"not_provided_by_yahoo","source_url":"https://finance.yahoo.com/quote/BBB/","fetched_at_utc":"2026-10-26T00:00:00Z","market_cap_status":"not_verified"},
        {"symbol":"CCC","market_cap_usd_b_secondary":3.0,"quote_type":"EQUITY","exchange_name":"NYSE","observation_status":"observed_usd","market_cap_asof":"","market_cap_asof_basis":"not_provided_by_yahoo","source_url":"https://finance.yahoo.com/quote/CCC/","fetched_at_utc":"2026-10-26T00:00:00Z","market_cap_status":"not_verified"},
    ])
    result = build_cap_triage(observations, master).set_index("symbol")
    assert result.loc["AAA", "triage_status"] == "priority_review_cap_ge_1b"
    assert result.loc["BBB", "triage_status"] == "priority_review_cap_lt_1b"
    assert result.loc["CCC", "triage_status"] == "adr_review_required"


def test_fresh_symbols_are_processed_before_retrying_persistent_failures():
    previous = pd.DataFrame([{
        "symbol": "AAA",
        "observation_status": "request_failed",
        "market_cap_status": "not_verified",
    }])
    seen = []
    result, stats = collect_bounded_batch(
        _master(),
        previous=previous,
        batch_size=1,
        ticker_factory=lambda symbol: (seen.append(symbol) or FakeTicker(symbol)),
    )
    assert seen == ["CCC"]
    assert stats["processed_this_run"] == 1
    assert stats["eligible_remaining"] == 1
    assert set(result["symbol"]) == {"AAA", "CCC"}


def test_large_observed_cap_stays_visible_when_listing_identity_needs_review():
    from yahoo_master_cap_batch import build_cap_triage

    master = pd.DataFrame([{
        "listing_exchange":"NYS","symbol":"BIG","master_security_type":"2",
        "master_dr_flag":"N","master_dr_country_code":"",
    }])
    observations = pd.DataFrame([{
        "symbol":"BIG","market_cap_usd_b_secondary":5.2,"quote_type":"EQUITY",
        "exchange_name":"Unrecognized Venue","observation_status":"observed_usd",
        "market_cap_asof":"","market_cap_asof_basis":"not_provided_by_yahoo",
        "source_url":"https://finance.yahoo.com/quote/BIG/",
        "fetched_at_utc":"2026-10-26T00:00:00Z","market_cap_status":"not_verified",
    }])
    result = build_cap_triage(observations, master).iloc[0]
    assert result["triage_status"] == "listing_identity_review_required"
    assert result["cap_threshold_review"] == "observed_ge_1b_review_only"
    assert result["market_cap_status"] == "not_verified"



def test_coverage_status_reports_pending_inventory_and_estimated_batches():
    master = pd.DataFrame([
        {"listing_exchange":"NAS","symbol":"AAA","master_security_type":"2","master_dr_flag":"N","master_dr_country_code":""},
        {"listing_exchange":"NYS","symbol":"CCC","master_security_type":"2","master_dr_flag":"N","master_dr_country_code":""},
        {"listing_exchange":"AMS","symbol":"ETF","master_security_type":"3","master_dr_flag":"N","master_dr_country_code":""},
    ])
    observations = pd.DataFrame([
        {"symbol":"AAA","market_cap_usd_b_secondary":2.1,"observation_status":"observed_usd"},
    ])
    status = build_coverage_status(master, observations, batch_size=1, processed_this_run=1)
    assert status["eligible_inventory_total"] == 2
    assert status["eligible_symbols_with_observation"] == 1
    assert status["eligible_symbols_pending"] == 1
    assert status["estimated_batches_remaining"] == 1
    assert status["coverage_pct"] == 50.0
    assert status["observed_cap_ge_1b"] == 1
    assert status["market_cap_status"] == "secondary_estimates_only_not_verified"
    assert status["activation_status"] == "no_candidates_activated"
