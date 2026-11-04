import pandas as pd
import unittest

from us_kis_evidence_readiness import assess_candidates


def fixtures():
    registry = pd.DataFrame([dict(symbol="ABC", exchange="NAS", name="ABC INC",
        discovery_security_type="2", instrument_type="common_stock_candidate",
        provider_status="not_checked", identity_status="review_required",
        activation_status="pending_review", mapping_status="proposed")])
    master = pd.DataFrame([dict(symbol="ABC", listing_exchange="NAS",
        english_name="ABC INC", master_security_type="2", master_dr_flag="N")])
    dims = {"ABC": dict(cap_screen_pass=True, cap_value_present=True,
        price_quality_pass=True, weeks35=True, assigned_stage_data_inputs_available=True,
        mapping_fields_present=True, proposed_mapping_present=True)}
    return registry, master, dims


class KISEvidenceReadinessTests(unittest.TestCase):
    def test_kis_evidence_suffices_without_status_promotion_or_mutation(self):
        r, m, d = fixtures()
        original = r.copy(deep=True)
        row = assess_candidates(r, m, d)[0]
        assert row["identity_basis"] == "kis_master_consistent"
        assert row["offline_review_eligible"]
        assert not row["additional_review_required"]
        assert row["provider_evidence"] == "stored_valid_prices"
        assert row["provider_status_recorded"] == "not_checked"
        assert row["activation_status_recorded"] == "pending_review"
        assert row["cap_basis"] == "estimate"
        assert not row["operational_approval_granted"]
        pd.testing.assert_frame_equal(r, original)


    def test_anomalies_need_review(self):
        for field,value,reason in [
        ("listing_exchange", "NYS", "exchange_conflict"),
        ("master_security_type", "3", "security_type_unknown_or_non_stock"),
        ("master_security_type", "", "security_type_unknown_or_non_stock"),
        ("english_name", "ABC PREFERRED", "non_common_or_fund_signal"),
        ("english_name", "ABC WARRANT", "non_common_or_fund_signal"),
        ("english_name", "ABC RIGHTS", "non_common_or_fund_signal"),
        ("english_name", "ABC ETF", "non_common_or_fund_signal"),
        ("master_dr_flag", "Y", "adr_ratio_unconfirmed"),
    ]:
            r, m, d = fixtures()
            m.loc[0, field] = value
            row = assess_candidates(r, m, d)[0]
            assert reason in row["review_reasons"]
            assert not row["offline_review_eligible"]

    def test_missing_master_is_not_conflict_and_prices_are_not_identity(self):
        r, m, d = fixtures()
        row = assess_candidates(r, m.iloc[:0], d)[0]
        assert row["identity_basis"] == "missing_kis_master"
        assert not row["additional_review_required"]
        assert not row["offline_review_eligible"]


    def test_stored_kis_ranking_type_and_duplicate_conflict(self):
        r, m, d = fixtures()
        r["discovery_source"] = "KIS market-cap ranking"
        r["discovery_security_type"] = "stock"
        assert assess_candidates(r, m.iloc[:0], d)[0]["offline_review_eligible"]
        assert not assess_candidates(pd.concat([r, r]), m, d)[0]["offline_review_eligible"]
        assert not assess_candidates(r, pd.concat([m, m]), d)[0]["offline_review_eligible"]


    def test_data_and_benchmark_gates_remain_required(self):
        for key in ["cap_screen_pass", "price_quality_pass", "weeks35", "assigned_stage_data_inputs_available"]:
            r, m, d = fixtures()
            d["ABC"][key] = False
            row = assess_candidates(r, m, d)[0]
            assert row["identity_basis"] == "kis_master_consistent"
            assert not row["offline_review_eligible"]

    def test_adr_verified_ratio_still_requires_all_data(self):
        r, m, d = fixtures()
        m["master_dr_flag"] = "Y"
        r["depositary_ratio_status"] = "verified"
        assert assess_candidates(r, m, d)[0]["offline_review_eligible"]


    def test_registry_type_conflict_and_missing_benchmark_do_not_pass(self):
        r, m, d = fixtures()
        r["discovery_security_type"] = "etp"
        assert "registry_master_type_conflict" in assess_candidates(r, m, d)[0]["review_reasons"]
        r["discovery_security_type"] = "2"
        d["ABC"]["assigned_stage_data_inputs_available"] = False
        d["ABC"]["mapping_fields_present"] = False
        row = assess_candidates(r, m, d)[0]
        assert row["proposed_mapping_present"]
        assert not row["assigned_mapping_present"]
        assert not row["offline_review_eligible"]


    def test_kis_ranking_adr_country_signal_survives_missing_master_file_row(self):
        r, m, d = fixtures()
        r["discovery_source"] = "KIS market-cap ranking"
        r["discovery_security_type"] = "stock"
        r["discovery_dr_country_code"] = "CN"
        assert "adr_ratio_unconfirmed" in assess_candidates(r, m.iloc[:0], d)[0]["review_reasons"]
