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
    ])
    prices = pd.DataFrame([
        {"symbol": "ORCL", "date": "2026-10-23", "close": 180.0},
        {"symbol": "BABA", "date": "2026-10-23", "close": 100.0},
        {"symbol": "UNKNOWN", "date": "2026-10-23", "close": 20.0},
    ])

    report = build_report(candidates, prices).set_index("symbol")

    assert report.loc["BABA", "triage_outcome"] == "adr_share_class_review_required"
    assert report.loc["ORCL", "market_cap_status_remains"] == "not_verified"
    assert report.loc["ORCL", "secondary_market_cap_source_url"] == "https://example.com/orcl-cap"
    assert report.loc["UNKNOWN", "triage_outcome"] == "official_share_count_not_captured"
    assert report["market_cap_status_remains"].eq("not_verified").all()
