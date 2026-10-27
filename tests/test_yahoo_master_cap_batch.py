import pandas as pd

from yahoo_master_cap_batch import build_coverage_status, collect_bounded_batch, collect_multiple_batches, master_to_yahoo_input


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
        {"symbol":"CCC","market_cap_usd_b_secondary":"","observation_status":"request_failed"},
    ])
    status = build_coverage_status(master, observations, batch_size=1, processed_this_run=1)
    assert status["eligible_inventory_total"] == 2
    assert status["eligible_symbols_with_observation"] == 1
    assert status["eligible_symbols_pending"] == 1
    assert status["estimated_batches_remaining"] == 1
    assert status["coverage_pct"] == 50.0
    assert status["observed_cap_ge_1b"] == 1
    assert status["request_failures"] == 1
    assert status["market_cap_status"] == "secondary_estimates_only_not_verified"
    assert status["activation_status"] == "no_candidates_activated"

def test_coverage_status_reports_unconfirmed_adrs_separately(tmp_path, monkeypatch):
    import yahoo_master_cap_batch as batch

    registry_path = tmp_path / "adr_registry.csv"
    registry_path.write_text(
        "symbol,status\nADR1,official_source_confirmed\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(batch, "ADR_RATIO_REGISTRY", registry_path)
    master = pd.DataFrame([
        {"listing_exchange":"NAS","symbol":"COMMON","master_security_type":"2","master_dr_flag":"N","master_dr_country_code":""},
        {"listing_exchange":"NYS","symbol":"ADR1","master_security_type":"2","master_dr_flag":"Y","master_dr_country_code":"GB"},
        {"listing_exchange":"NAS","symbol":"ADR2","master_security_type":"2","master_dr_flag":"Y","master_dr_country_code":"IN"},
    ])
    status = build_coverage_status(master, pd.DataFrame(), batch_size=10)

    assert status["eligible_common_stock_symbols"] == 1
    assert status["eligible_confirmed_adr_symbols"] == 1
    assert status["adr_master_symbols_total"] == 2
    assert status["unconfirmed_adr_symbols_pending"] == 1
    assert status["unconfirmed_adr_symbol_sample"] == ["ADR2"]



def test_multiple_batches_preserve_checkpoints_and_report_total_processed():
    calls = []

    def fake_collector(master, previous, batch_size, adr_ratio_registry=None):
        previous = previous.copy()
        calls.append((batch_size, len(previous)))
        row = {"symbol": f"S{len(calls)}", "observation_status": "observed_usd"}
        result = pd.concat([previous, pd.DataFrame([row])], ignore_index=True)
        return result, {"processed_this_run": 1, "observations_total": len(result)}

    result, stats, completed = collect_multiple_batches(
        pd.DataFrame([{"symbol": "ignored"}]),
        previous=pd.DataFrame(),
        batch_size=200,
        batches_per_run=2,
        collector=fake_collector,
    )
    assert calls == [(200, 0), (200, 1)]
    assert result["symbol"].tolist() == ["S1", "S2"]
    assert stats["processed_this_run"] == 2
    assert completed == 2


def test_multiple_batches_stop_when_no_more_symbols_are_available():
    calls = []

    def fake_collector(master, previous, batch_size, adr_ratio_registry=None):
        calls.append(1)
        return previous, {"processed_this_run": 0, "observations_total": len(previous)}

    result, stats, completed = collect_multiple_batches(
        pd.DataFrame(), previous=pd.DataFrame(), batch_size=200,
        batches_per_run=3, collector=fake_collector,
    )
    assert len(calls) == 1
    assert stats["processed_this_run"] == 0
    assert completed == 0

def test_cap_triage_includes_kis_identity_fields_without_verifying_or_activating():
    from yahoo_master_cap_batch import build_cap_triage

    master = pd.DataFrame([{
        "listing_exchange": "NAS",
        "symbol": "AAA",
        "english_name": "Example Corporation",
        "master_security_type": "2",
        "master_dr_flag": "N",
        "master_dr_country_code": "",
        "master_industry_code": "720",
    }])
    observations = pd.DataFrame([{
        "symbol": "AAA",
        "market_cap_usd_b_secondary": 2.1,
        "quote_type": "EQUITY",
        "exchange_name": "NasdaqGS",
        "observation_status": "observed_usd",
        "market_cap_status": "not_verified",
        "market_cap_asof": "",
        "market_cap_asof_basis": "not_provided_by_yahoo",
        "source_url": "https://finance.yahoo.com/quote/AAA/",
        "fetched_at_utc": "2026-10-27T00:00:00Z",
    }])

    result = build_cap_triage(observations, master).iloc[0]
    assert result["kis_english_name"] == "Example Corporation"
    assert result["kis_listing_exchange"] == "NAS"
    assert result["kis_security_type"] == "2"
    assert result["kis_industry_code"] == "720"
    assert result["triage_status"] == "priority_review_cap_ge_1b"
    assert result["market_cap_status"] == "not_verified"



def test_multiple_batches_accepts_four_bounded_batches():
    calls = []

    def fake_collector(master, previous, batch_size, adr_ratio_registry=None):
        calls.append(1)
        row = {"symbol": f"S{len(calls)}", "observation_status": "observed_usd"}
        previous = previous.copy()
        result = pd.concat([previous, pd.DataFrame([row])], ignore_index=True)
        return result, {"processed_this_run": 1, "observations_total": len(result)}

    result, stats, completed = collect_multiple_batches(
        pd.DataFrame([{"symbol": "ignored"}]), previous=pd.DataFrame(),
        batch_size=200, batches_per_run=4, collector=fake_collector,
    )
    assert len(calls) == 4
    assert stats["processed_this_run"] == 4
    assert completed == 4
    assert result["symbol"].tolist() == ["S1", "S2", "S3", "S4"]


def test_large_cap_candidate_queue_is_separate_and_never_activates():
    from yahoo_master_cap_batch import build_large_cap_candidate_review_queue

    triage = pd.DataFrame([
        {"symbol":"AAA","kis_english_name":"Alpha Inc","kis_listing_exchange":"NAS","kis_security_type":"2","kis_dr_flag":"N","kis_industry_code":"720","market_cap_usd_b_secondary":2.1,"quote_type":"EQUITY","triage_status":"priority_review_cap_ge_1b","source_url":"https://finance.yahoo.com/quote/AAA/","market_cap_asof":"","fetched_at_utc":"2026-10-27T00:00:00Z"},
        {"symbol":"ADR1","kis_english_name":"ADR One","kis_listing_exchange":"NYS","kis_security_type":"2","kis_dr_flag":"Y","market_cap_usd_b_secondary":5.0,"quote_type":"EQUITY","triage_status":"adr_review_required"},
        {"symbol":"ETF1","kis_english_name":"ETF One","kis_listing_exchange":"NAS","kis_security_type":"3","kis_dr_flag":"N","market_cap_usd_b_secondary":10.0,"quote_type":"ETF","triage_status":"instrument_type_review_required"},
        {"symbol":"NVDA","kis_english_name":"NVIDIA CORP","kis_listing_exchange":"NAS","kis_security_type":"2","kis_dr_flag":"N","market_cap_usd_b_secondary":5.0,"quote_type":"EQUITY","triage_status":"priority_review_cap_ge_1b","source_url":"https://finance.yahoo.com/quote/NVDA/"},
        {"symbol":"PBR","kis_english_name":"PETROLEO BRASILEIRO SPON ADS EACH REP 2 ORD SHS","kis_listing_exchange":"NYS","kis_security_type":"2","kis_dr_flag":"N","kis_dr_country_code":"BR","market_cap_usd_b_secondary":50.0,"quote_type":"EQUITY","triage_status":"priority_review_cap_ge_1b","source_url":"https://finance.yahoo.com/quote/PBR/"},
    ])
    result = build_large_cap_candidate_review_queue(triage)
    assert result["symbol"].tolist() == ["PBR", "NVDA", "AAA"]
    row = result[result["symbol"] == "AAA"].iloc[0]
    assert row["activation_status"] == "pending_review"
    assert row["market_cap_status"] == "not_verified"
    assert row["identity_status"] == "review_required"
    assert row["discovery_market_cap_usd_b_secondary"] == 2.1
    nvda = result[result["symbol"] == "NVDA"].iloc[0]
    assert nvda["sector"] == "Semiconductors"
    assert nvda["sector_benchmark"] == "SOXX"
    pbr = result[result["symbol"] == "PBR"].iloc[0]
    assert pbr["identity_status"] == "possible_adr_review_required"
    assert pbr["instrument_type"] == "possible_adr_or_equity_review"
    assert pbr["activation_status"] == "pending_review"
