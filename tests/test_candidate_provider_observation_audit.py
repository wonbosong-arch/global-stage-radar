from candidate_provider_observation_audit import build_report


def test_price_response_is_positive_observation_not_formal_support_or_identity_verification():
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
    assert row["provider_support_status"] == "price_response_observed_formal_support_unverified"
    assert row["instrument_identity_status"] == "not_verified"
    assert row["activation_recommendation"] == "keep_pending_review"


def test_no_price_response_is_not_mislabeled_as_observed_support():
    report = build_report({
        "provider_observations": [
            {
                "symbol": "XYZ",
                "requested_exchange": "NYS",
                "response_exchange": "",
                "response_rows": 0,
            }
        ]
    })
    assert report.iloc[0]["provider_support_status"] == "no_price_response_observed"


def test_failed_fetch_observation_keeps_symbol_and_error_in_audit():
    report = build_report({
        "provider_observations": [
            {
                "symbol": "FAIL",
                "requested_exchange": "NAS",
                "response_exchange": "",
                "response_rows": 0,
                "response_error": "TimeoutError: request timed out",
            }
        ]
    })
    row = report.iloc[0]
    assert row["symbol"] == "FAIL"
    assert row["provider_support_status"] == "no_price_response_observed"
    assert row["response_error"] == "TimeoutError: request timed out"
    assert row["activation_recommendation"] == "keep_pending_review"


def test_missing_observations_produces_empty_report_with_expected_columns():
    report = build_report({})
    assert report.empty
    assert "response_exchange" in report.columns
