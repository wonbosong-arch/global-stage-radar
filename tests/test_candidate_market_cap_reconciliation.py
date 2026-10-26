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
            "symbol": "CRM",
            "market_cap_usd_b_secondary": "204.57",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
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
            "symbol": "HD",
            "market_cap_usd_b_secondary": "319.09",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "NFLX",
            "market_cap_usd_b_secondary": "274.19",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "WELL",
            "market_cap_usd_b_secondary": "171.00",
            "market_cap_asof": "2026-10-23",
            "market_cap_status": "not_verified",
            "instrument_type": "common_stock_candidate",
        },
        {
            "symbol": "BAC",
            "market_cap_usd_b_secondary": "350.01",
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
        {"symbol": "TSM", "date": "2026-10-26", "close": 416.0},
        {"symbol": "CRM", "date": "2026-10-23", "close": 249.32},
        {"symbol": "UNKNOWN", "date": "2026-10-23", "close": 20.0},
        {"symbol": "CAT", "date": "2026-10-23", "close": 600.0},
        {"symbol": "PG", "date": "2026-10-23", "close": 160.0},
        {"symbol": "AMGN", "date": "2026-10-23", "close": 280.0},
        {"symbol": "HD", "date": "2026-10-23", "close": 322.8225},
        {"symbol": "NFLX", "date": "2026-10-23", "close": 65.9052},
        {"symbol": "WELL", "date": "2026-10-23", "close": 245.545},
        {"symbol": "BAC", "date": "2026-10-23", "close": 50.78},
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
    assert report.loc["TSM", "price_date"] == "2026-10-23"
    assert report.loc["TSM", "price_to_cap_asof_gap_days"] == 0
    assert report.loc["TSM", "price_to_share_count_asof_gap_days"] == 115
    assert report.loc["BABA", "price_to_share_count_asof_gap_days"] == 31
    assert report.loc["TSM", "date_review_priority"] == "P1_material_mismatch"
    assert report.loc["CRM", "reported_shares_m"] == 823.0
    assert report.loc["CRM", "reported_shares_asof"] == "2026-08-20"
    assert report.loc["CRM", "date_review_priority"] == "P3_routine_evidence"
    assert report.loc["CRM", "triage_outcome"] == "arithmetic_consistent_date_basis_still_unverified"
    assert report.loc["AMGN", "date_review_priority"] == "P1_stale_share_count"
    assert report.loc["ORCL", "market_cap_status_remains"] == "not_verified"
    assert report.loc["ORCL", "secondary_market_cap_source_url"] == "https://example.com/orcl-cap"
    assert report.loc["UNKNOWN", "triage_outcome"] == "official_share_count_not_captured"
    assert report.loc["CAT", "reported_shares_m"] == 459.674889
    assert report.loc["CAT", "reported_shares_asof"] == "2026-06-30"
    assert report.loc["PG", "reported_shares_m"] == 2324.433060
    assert report.loc["PG", "reported_shares_asof"] == "2026-07-31"
    assert report.loc["AMGN", "reported_shares_m"] == 540.632005
    assert report.loc["AMGN", "reported_shares_asof"] == "2026-07-30"
    assert report.loc["AMGN", "reported_shares_source_url"] == "https://www.sec.gov/Archives/edgar/data/318154/000031815426000126/amgn-20260630.htm"
    assert report.loc["AMGN", "date_review_priority"] != "P1_stale_share_count"
    assert report.loc["HD", "reported_shares_m"] == 997.689626
    assert report.loc["HD", "reported_shares_asof"] == "2026-08-18"
    assert report.loc["HD", "date_review_priority"] != "P1_stale_share_count"
    assert report.loc["NFLX", "reported_shares_m"] == 4106.325903
    assert report.loc["NFLX", "reported_shares_asof"] == "2026-09-30"
    assert report.loc["NFLX", "date_review_priority"] != "P1_stale_share_count"
    assert report.loc["WELL", "reported_shares_m"] == 720.744951
    assert report.loc["WELL", "reported_shares_asof"] == "2026-07-24"
    assert report.loc["WELL", "date_review_priority"] != "P1_stale_share_count"
    assert report.loc["BAC", "reported_shares_m"] == 6992.748365
    assert report.loc["BAC", "reported_shares_asof"] == "2026-07-30"
    assert report.loc["BAC", "date_review_priority"] != "P1_stale_share_count"
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


def test_confirmed_adr_ratio_is_distinguished_from_unverified_share_count():
    candidates = pd.DataFrame([{
        "symbol": "BABA",
        "market_cap_usd_b_secondary": "247.67",
        "market_cap_asof": "2026-10-23",
        "market_cap_status": "not_verified",
        "instrument_type": "adr_candidate",
        "depositary_ratio_status": "official_source_confirmed",
        "depositary_ratio_observed": "8",
        "depositary_ratio_source_url": "https://example.com/issuer-adr-ratio",
    }])
    prices = pd.DataFrame([{"symbol": "BABA", "date": "2026-10-23", "close": 100.0}])

    result = build_report(candidates, prices).iloc[0]

    assert result["triage_outcome"] == "adr_ratio_evidence_captured_share_count_review_required"
    assert result["depositary_ratio_evidence_confirmed"]
    assert result["depositary_ratio_observed"] == 8
    assert result["depositary_ratio_source_url"] == "https://example.com/issuer-adr-ratio"
    assert result["market_cap_status_remains"] == "not_verified"


def test_verified_adr_ratio_from_supplement_is_used_without_verifying_market_cap():
    candidates = pd.DataFrame([{
        "symbol": "TSM",
        "market_cap_usd_b_secondary": "2170.69",
        "market_cap_asof": "2026-10-23",
        "market_cap_status": "not_verified",
        "instrument_type": "adr_candidate",
        "depositary_ratio_status": "verified",
        "depositary_ratio_observed": "",
        "depositary_ratio_source_url": "",
    }])
    prices = pd.DataFrame([{"symbol": "TSM", "date": "2026-10-23", "close": 418.51}])
    ratio_evidence = pd.DataFrame([{
        "symbol": "TSM",
        "depositary_ratio_status": "verified",
        "depositary_ratio_observed": "5",
        "depositary_ratio_source_url": "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/2026-07/114aaca0fea2050e96b91fffbab9ed04ba09cd92/FS.pdf",
    }])

    result = build_report(candidates, prices, ratio_evidence).iloc[0]

    assert result["triage_outcome"] == "adr_ratio_evidence_captured_share_count_review_required"
    assert result["depositary_ratio_evidence_confirmed"]
    assert result["depositary_ratio_observed"] == 5
    assert result["market_cap_status_remains"] == "not_verified"



def test_missing_official_share_count_is_prioritized_for_evidence_collection():
    candidates = pd.DataFrame([{
        "symbol": "NEWCO",
        "market_cap_usd_b_secondary": "12",
        "market_cap_asof": "2026-10-23",
        "market_cap_source_url": "https://example.com/newco-cap",
        "market_cap_status": "not_verified",
        "instrument_type": "common_stock_candidate",
    }])
    prices = pd.DataFrame([{"symbol": "NEWCO", "date": "2026-10-23", "close": 12.0}])

    report = build_report(candidates, prices).iloc[0]

    assert report["triage_outcome"] == "official_share_count_not_captured"
    assert report["date_review_priority"] == "P2_share_count_evidence"
    assert report["date_review_reason"] == "official_share_count_not_captured"
    assert report["market_cap_status_remains"] == "not_verified"



def test_report_is_sorted_by_review_priority_before_symbol():
    candidates = pd.DataFrame([
        {"symbol": "ZZZ", "market_cap_usd_b_secondary": "10", "market_cap_asof": "2026-10-23", "market_cap_status": "not_verified", "instrument_type": "common_stock_candidate"},
        {"symbol": "AAA", "market_cap_usd_b_secondary": "20", "market_cap_asof": "2026-10-23", "market_cap_status": "not_verified", "instrument_type": "common_stock_candidate"},
    ])
    prices = pd.DataFrame([
        {"symbol": "ZZZ", "date": "2026-10-23", "close": 10.0},
        {"symbol": "AAA", "date": "2026-10-23", "close": 20.0},
    ])

    report = build_report(candidates, prices)

    assert report["date_review_priority"].tolist() == ["P2_share_count_evidence", "P2_share_count_evidence"]
    assert report["symbol"].tolist() == ["AAA", "ZZZ"]
