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
            "symbol": "TSM",
            "market_cap_usd_b_secondary": "1900",
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
        {
            "symbol": "KO",
            "market_cap_usd_b_secondary": "300",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "ANET",
            "market_cap_usd_b_secondary": "120",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "ADBE",
            "market_cap_usd_b_secondary": "150",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "MCD",
            "market_cap_usd_b_secondary": "220",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "ETN",
            "market_cap_usd_b_secondary": "150",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "IBM",
            "market_cap_usd_b_secondary": "300",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "NOW",
            "market_cap_usd_b_secondary": "200",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "PLTR",
            "market_cap_usd_b_secondary": "400",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "COP",
            "market_cap_usd_b_secondary": "150",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "TJX",
            "market_cap_usd_b_secondary": "150",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "DIS",
            "market_cap_usd_b_secondary": "200",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "DE",
            "market_cap_usd_b_secondary": "100",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "LIN",
            "market_cap_usd_b_secondary": "220",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
    ])
    prices = pd.DataFrame([
        {"symbol": "ORCL", "date": "2026-10-23", "close": 180.0},
        {"symbol": "BABA", "date": "2026-10-23", "close": 100.0},
        {"symbol": "TSM", "date": "2026-10-23", "close": 418.51},
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
        {"symbol": "KO", "date": "2026-10-23", "close": 65.0},
        {"symbol": "ANET", "date": "2026-10-23", "close": 100.0},
        {"symbol": "ADBE", "date": "2026-10-23", "close": 350.0},
        {"symbol": "MCD", "date": "2026-10-23", "close": 300.0},
        {"symbol": "ETN", "date": "2026-10-23", "close": 380.0},
        {"symbol": "IBM", "date": "2026-10-23", "close": 280.0},
        {"symbol": "NOW", "date": "2026-10-23", "close": 900.0},
        {"symbol": "PLTR", "date": "2026-10-23", "close": 150.0},
        {"symbol": "COP", "date": "2026-10-23", "close": 100.0},
        {"symbol": "TJX", "date": "2026-10-23", "close": 150.0},
        {"symbol": "DIS", "date": "2026-10-23", "close": 100.0},
        {"symbol": "DE", "date": "2026-10-23", "close": 500.0},
        {"symbol": "LIN", "date": "2026-10-23", "close": 500.0},
    ])

    report = build_report(candidates, prices).set_index("symbol")

    assert report.loc["BABA", "triage_outcome"] == "adr_share_class_review_required"
    assert report.loc["BABA", "reported_shares_m"] == 2486.561
    assert report.loc["BABA", "reported_shares_asof"] == "2026-09-22"
    assert "divided by 8 ordinary shares per ADS" in report.loc["BABA", "reported_shares_note"]
    assert report.loc["TSM", "triage_outcome"] == "adr_share_class_review_required"
    assert report.loc["TSM", "reported_shares_m"] == 5186.474
    assert report.loc["TSM", "reported_shares_asof"] == "2026-06-30"
    assert "divided by 5 ordinary shares per ADS" in report.loc["TSM", "reported_shares_note"]
    assert report.loc["TSM", "price_to_cap_asof_gap_days"] == 0
    assert report.loc["TSM", "price_to_share_count_asof_gap_days"] == 115
    assert report.loc["BABA", "price_to_share_count_asof_gap_days"] == 31
    assert report.loc["TSM", "date_review_priority"] == "P1_material_mismatch"
    assert report.loc["CRM", "date_review_priority"] == "P1_material_mismatch"
    assert report.loc["AMGN", "date_review_priority"] == "P1_stale_share_count"
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
    assert report.loc["KO", "reported_shares_m"] == 4302.549243
    assert report.loc["KO", "reported_shares_asof"] == "2026-07-27"
    assert report.loc["ANET", "reported_shares_m"] == 1261.224648
    assert report.loc["ANET", "reported_shares_asof"] == "2026-07-30"
    assert report.loc["ADBE", "reported_shares_m"] == 389.2
    assert report.loc["ADBE", "reported_shares_asof"] == "2026-09-18"
    assert report.loc["MCD", "reported_shares_m"] == 707.641531
    assert report.loc["MCD", "reported_shares_asof"] == "2026-06-30"
    assert report.loc["ETN", "reported_shares_m"] == 388.4
    assert report.loc["ETN", "reported_shares_asof"] == "2026-06-30"
    assert report.loc["IBM", "reported_shares_m"] == 942.134390
    assert report.loc["IBM", "reported_shares_asof"] == "2026-06-30"
    assert report.loc["NOW", "reported_shares_m"] == 1034.0
    assert report.loc["NOW", "reported_shares_asof"] == "2026-06-30"
    assert report.loc["PLTR", "reported_shares_m"] == 2402.058480
    assert report.loc["PLTR", "reported_shares_asof"] == "2026-07-27"
    assert "Class A, Class B, and Class F" in report.loc["PLTR", "reported_shares_note"]
    assert report.loc["COP", "reported_shares_m"] == 1201.337479
    assert report.loc["COP", "reported_shares_asof"] == "2026-06-30"
    assert report.loc["TJX", "reported_shares_m"] == 1099.974061
    assert report.loc["TJX", "reported_shares_asof"] == "2026-08-21"
    assert report.loc["DIS", "reported_shares_m"] == 1726.686902
    assert report.loc["DIS", "reported_shares_asof"] == "2026-07-29"
    assert report.loc["DE", "reported_shares_m"] == 269.937425
    assert report.loc["DE", "reported_shares_asof"] == "2026-05-03"
    assert report.loc["LIN", "reported_shares_m"] == 460.980163
    assert report.loc["LIN", "reported_shares_asof"] == "2026-06-30"
    assert "net of treasury shares" in report.loc["LIN", "reported_shares_note"]
    assert report["market_cap_status_remains"].eq("not_verified").all()
