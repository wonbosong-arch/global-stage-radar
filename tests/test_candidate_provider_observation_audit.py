import pandas as pd

from candidate_provider_observation_audit import build_report


def test_provider_response_is_diagnostic_not_identity_or_support_verification():
    report = build_report({
        "provider_observations": [
            {
                "symbol": "SPY",
                "requested_exchange": "NYS",
                "response_exchange": "AMS",
                "response_rows": 300,
                "latest_response_date": "2026-10-23",
                "observation_scope": "price_response_only_not_identity_verification",
            }
        ]
    })
    row = report.iloc[0]
    assert row["exchange_fallback_used"]
    assert row["provider_support_status"] == "not_verified"
    assert row["instrument_identity_status"] == "not_verified"
    assert row["activation_recommendation"] == "keep_pending_review"


def test_missing_observations_produces_empty_report_with_expected_columns():
    report = build_report({})
    assert report.empty
    assert "response_exchange" in report.columns
