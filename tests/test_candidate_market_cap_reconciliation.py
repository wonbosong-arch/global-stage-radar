import pandas as pd

from candidate_market_cap_reconciliation import build_report


def test_reconciliation_is_triage_only_and_does_not_change_status():
    candidates = pd.DataFrame([
        {
            "symbol": "ORCL",
            "market_cap_usd_b_secondary": "382.45",
            "market_cap_asof": "2026-10-23",
            "market_cap_source_url": "https://example.com/orcl-cap",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "BABA",
            "market_cap_usd_b_secondary": "247.67",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "adr_candidate",
        },
        {
            "symbol": "UNKNOWN",
            "market_cap_usd_b_secondary": "10",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "CAT",
            "market_cap_usd_b_secondary": "300",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "market_cap_source_url": "https://example.com/cat-cap",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "PG",
            "market_cap_usd_b_secondary": "380",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "market_cap_source_url": "https://example.com/pg-cap",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "AMGN",
            "market_cap_usd_b_secondary": "150",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "SBUX",
            "market_cap_usd_b_secondary": "110",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "CSCO",
            "market_cap_usd_b_secondary": "300",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "CEG",
            "market_cap_usd_b_secondary": "120",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "CVX",
            "market_cap_usd_b_secondary": "300",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "TMUS",
            "market_cap_usd_b_secondary": "200",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "AEP",
            "market_cap_usd_b_secondary": "50",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
    ])
    prices = pd.DataFrame([
        {"symbol": "ORCL", "date": "2026-10-23", "close": 180.0},
        {"symbol": "BABA", "date": "2026-10-23", "close": 100.0},
        {"symbol": "UNKNOWN", "date": "2026-10-23", "close": 20.0},
        {"symbol": "CAT", "date": "2026-10-23", "close": 600.0},
        {"symbol": "PG", "date": "2026-10-23", "close": 160.0},
        {"symbol": "AMGN", "date": "2026-10-23", "close": 280.0},
        {"symbol": "SBUX", "date": "2026-10-23", "close": 100.0},
        {"symbol": "CSCO", "date": "2026-10-23", "close": 70.0},
        {"symbol": "CEG", "date": "2026-10-23", "close": 350.0},
        {"symbol": "CVX", "date": "2026-10-23", "close": 150.0},
        {"symbol": "TMUS", "date": "2026-10-23", "close": 200.0},
        {"symbol": "AEP", "date": "2026-10-23", "close": 110.0},
    ])

    report = build_report(candidates, prices).set_index("symbol")

    assert report.loc["BABA", "triage_outcome"] == "adr_share_class_review_required"
    assert report.loc["ORCL", "market_cap_status_remains"] == "not_verified"
    assert report.loc["ORCL", "secondary_market_cap_source_url"] == "https://example.com/orcl-cap"
    assert report.loc["UNKNOWN", "triage_outcome"] == "official_share_count_not_captured"
    assert report.loc["CAT", "reported_shares_m"] == 459.674889
    assert report.loc["CAT", "reported_shares_asof"] == "2026-06-30"
    assert report.loc["PG", "reported_shares_m"] == 2324.433060
    assert report.loc["PG", "reported_shares_asof"] == "2026-07-31"
    assert report.loc["AMGN", "reported_shares_m"] == 539.067675
    assert report.loc["AMGN", "reported_shares_asof"] == "2026-02-10"
    assert report.loc["SBUX", "reported_shares_m"] == 1140.0
    assert report.loc["SBUX", "reported_shares_asof"] == "2026-07-23"
    assert report.loc["CSCO", "reported_shares_m"] == 3942.586873
    assert report.loc["CSCO", "reported_shares_asof"] == "2026-08-27"
    assert report.loc["CEG", "reported_shares_m"] == 354.307379
    assert report.loc["CEG", "reported_shares_asof"] == "2026-07-31"
    assert report.loc["CVX", "reported_shares_m"] == 1975.771274
    assert report.loc["CVX", "reported_shares_asof"] == "2026-06-30"
    assert report.loc["TMUS", "reported_shares_m"] == 1072.671613
    assert report.loc["TMUS", "reported_shares_asof"] == "2026-07-17"
    assert report.loc["AEP", "reported_shares_m"] == 544.397352
    assert report.loc["AEP", "reported_shares_asof"] == "2026-07-30"
    assert report["market_cap_status_remains"].eq("not_verified").all()
