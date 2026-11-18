"""Specialist ETF candidates are evidence for review, never automatic replacements."""
import unittest

import pandas as pd

from us_etf_subindustry_review import ETF_CANDIDATES, find_etf_alternative


class ETFResearchReviewTests(unittest.TestCase):
    def test_catalog_keeps_the_current_etf(self):
        cases = [
            ("Technology", "Computer Software: Prepackaged Software", "IGV"),
            ("Health Care", "Biotechnology: Biological Products (No Diagnostic Substances)", "XBI"),
            ("Real Estate", "Real Estate Investment Trusts", "IYR"),
            ("Finance", "Major Banks", "KBE"),
            ("Finance", "Property-Casualty Insurers", "KIE"),
            ("Finance", "Life Insurance", "KIE"),
            ("Consumer Discretionary", "Air Freight/Delivery Services", "JETS"),
        ]
        for native, industry, etf in cases:
            with self.subTest(industry=industry):
                universe = pd.DataFrame([{"symbol": "XLK", "provider": "KIS",
                                          "asset_type": "sector_etf", "active": "true"}])
                packet = {"native_classification_join_pass": True,
                          "native_sector": native, "native_industry": industry}
                before = universe.copy(deep=True)
                out = find_etf_alternative(packet, "XLK", universe)
                self.assertEqual(out["preferred_sector_etf_review"], etf)
                self.assertEqual(out["preferred_etf_existing_benchmark_preserved"], "XLK")
                self.assertTrue(out["preferred_etf_official_source"].startswith("https://"))
                self.assertFalse(out["preferred_etf_approved"])
                self.assertIn("미검증", out["preferred_etf_review_status"])
                self.assertTrue(out["preferred_etf_fit_note"])
                self.assertEqual(find_etf_alternative(packet, etf, universe), {})
                self.assertEqual(ETF_CANDIDATES[(native, industry)][0], etf)
                pd.testing.assert_frame_equal(universe, before)

    def test_bad_identity_or_mixed_industry_is_not_an_etf_signal(self):
        universe = pd.DataFrame(columns=["symbol", "provider", "asset_type", "active"])
        packet = {"native_classification_join_pass": False,
                  "native_sector": "Technology",
                  "native_industry": "Computer Software: Prepackaged Software"}
        self.assertEqual(find_etf_alternative(packet, "XLK", universe), {})
        packet["native_classification_join_pass"] = True
        packet["native_industry"] = "EDP Services"  # includes non-software businesses
        self.assertEqual(find_etf_alternative(packet, "XLK", universe), {})
        packet["native_sector"] = "Real Estate"
        packet["native_industry"] = "Other Consumer Services"
        self.assertEqual(find_etf_alternative(packet, "XLRE", universe), {})

    def test_kis_metadata_alone_does_not_approve_a_new_etf(self):
        packet = {"native_classification_join_pass": True,
                  "native_sector": "Technology",
                  "native_industry": "Computer Software: Prepackaged Software"}
        for active, provider, kind in [
            ("true", "KIS", "sector_etf"),
            ("false", "KIS", "sector_etf"),
            ("true", "Yahoo", "sector_etf"),
            ("true", "KIS", "stock"),
        ]:
            with self.subTest(active=active, provider=provider, kind=kind):
                universe = pd.DataFrame([{"symbol": "IGV", "provider": provider,
                                          "asset_type": kind, "active": active}])
                out = find_etf_alternative(packet, "XLK", universe)
                self.assertFalse(out["preferred_etf_approved"])
                self.assertEqual(out["preferred_etf_existing_benchmark_preserved"], "XLK")
                if provider == "KIS" and active == "true" and kind == "sector_etf":
                    self.assertIn("가격 이력 검토 필요", out["preferred_etf_review_status"])
                else:
                    self.assertIn("미검증", out["preferred_etf_review_status"])


if __name__ == "__main__":
    unittest.main()
