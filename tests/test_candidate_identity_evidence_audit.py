import pandas as pd

from candidate_identity_evidence_audit import build_report


def test_identity_audit_distinguishes_review_date_from_verified_identity():
    candidates = pd.DataFrame([
        {
            "symbol": "XYZ",
            "name": "Example Corp.",
            "exchange": "NYS",
            "country": "United States",
            "instrument_type": "common_stock_candidate",
            "identity_status": "review_required",
            "identity_evidence_url": "https://example.com/ir",
            "identity_reviewed_at": "2026-10-24",
            "market_cap_status": "not_verified",
            "market_cap_source_url": "https://example.com/cap",
            "market_cap_asof": "2026-10-23",
            "market_cap_usd_b_secondary": "10",
            "depositary_ratio_status": "not_applicable",
            "provider_status": "not_checked",
            "activation_status": "pending_review",
        },
        {
            "symbol": "ADR",
            "name": "Example ADR",
            "exchange": "NYS",
            "country": "Foreign",
            "instrument_type": "adr_candidate",
            "identity_status": "issuer_proxy_review_required",
            "identity_evidence_url": "https://example.com/adr",
            "identity_reviewed_at": "2026-10-24",
            "market_cap_status": "not_verified",
            "market_cap_source_url": "https://example.com/cap",
            "market_cap_asof": "2026-10-23",
            "market_cap_usd_b_secondary": "10",
            "depositary_ratio_status": "not_verified",
            "provider_status": "not_checked",
            "activation_status": "pending_review",
        },
    ])

    report = build_report(candidates).set_index("symbol")

    assert not bool(report.loc["XYZ", "identity_marked_verified"])
    assert "identity_not_verified" in report.loc["XYZ", "review_gaps"]
    assert bool(report.loc["ADR", "depositary_ratio_required"])
    assert not bool(report.loc["ADR", "depositary_ratio_verified"])
    assert "adr_ratio_not_verified" in report.loc["ADR", "review_gaps"]
