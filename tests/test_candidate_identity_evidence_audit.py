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
    assert report.loc["XYZ", "identity_evidence_source_class"] == "other_domain_requires_manual_classification"
    assert report.loc["XYZ", "market_cap_source_class"] == "other_domain_requires_manual_classification"
    assert bool(report.loc["ADR", "depositary_ratio_required"])
    assert not bool(report.loc["ADR", "depositary_ratio_verified"])
    assert "adr_ratio_not_verified" in report.loc["ADR", "review_gaps"]
    assert report.loc["ADR", "identity_evidence_source_class"] == "other_domain_requires_manual_classification"



def test_official_adr_ratio_source_is_reported_without_verifying_full_identity():
    candidates = pd.DataFrame([
        {
            "symbol": "BHP",
            "name": "BHP GROUP LTD SPON ADS EACH REP 2 ORD SHS",
            "exchange": "NYS",
            "country": "Unknown",
            "instrument_type": "adr_candidate",
            "identity_status": "issuer_proxy_review_required",
            "identity_evidence_url": "",
            "identity_reviewed_at": "",
            "market_cap_status": "not_verified",
            "market_cap_source_url": "",
            "market_cap_asof": "",
            "market_cap_usd_b_secondary": "",
            "depositary_ratio_status": "verified",
            "depositary_ratio_observed": "2",
            "depositary_ratio_basis": "ordinary_shares_per_depositary_share",
            "depositary_ratio_evidence_text": "Each ADS represents two underlying ordinary shares.",
            "depositary_ratio_source_url": "https://www.bhp.com/investor-centre/shareholder-information/frequently-asked-questions",
            "depositary_ratio_verified_at": "2026-10-26",
            "depositary_ratio_source_class": "Issuer investor FAQ",
            "provider_status": "not_checked",
            "activation_status": "pending_review",
        },
    ])

    report = build_report(candidates).set_index("symbol")
    row = report.loc["BHP"]

    assert bool(row["depositary_ratio_verified"])
    assert row["depositary_ratio_observed"] == "2"
    assert row["depositary_ratio_source_url"].startswith("https://www.bhp.com/")
    assert row["depositary_ratio_verified_at"] == "2026-10-26"
    assert not bool(row["identity_marked_verified"])
    assert not bool(row["market_cap_marked_verified"])
    assert "adr_ratio_not_verified" not in row["review_gaps"]
    assert "identity_not_verified" in row["review_gaps"]
    assert "market_cap_not_verified" in row["review_gaps"]
