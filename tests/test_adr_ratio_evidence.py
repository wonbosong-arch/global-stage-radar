import unittest

from collect_stock_candidates import extract_adr_ratio_from_listing_name


class AdrRatioDescriptionTests(unittest.TestCase):
    def test_decimal_ratio_is_captured_as_observed_not_verified(self):
        ratio, basis = extract_adr_ratio_from_listing_name(
            "SK HYNIX INC SPON ADS EACH REP 0.1 SHS"
        )
        self.assertEqual(ratio, "0.1")
        self.assertEqual(basis, "ordinary_shares_per_depositary_share")

    def test_multiple_ordinary_shares_per_ads_are_captured(self):
        ratio, basis = extract_adr_ratio_from_listing_name(
            "PDD HOLDINGS INC SPON ADS EACH REP 4 ORD SHS"
        )
        self.assertEqual(ratio, "4")
        self.assertEqual(basis, "ordinary_shares_per_depositary_share")

    def test_simple_share_description_is_captured(self):
        ratio, basis = extract_adr_ratio_from_listing_name(
            "ARM HOLDINGS PLC SPON ADS EACH REP 1 ORD SHS"
        )
        self.assertEqual(ratio, "1")
        self.assertTrue(basis)

    def test_ambiguous_description_is_not_guessed(self):
        ratio, basis = extract_adr_ratio_from_listing_name(
            "ADR-EACH REP 1 CHF0.5(REGD)"
        )
        self.assertEqual(ratio, "")
        self.assertEqual(basis, "")

    def test_missing_description_is_not_guessed(self):
        self.assertEqual(extract_adr_ratio_from_listing_name("UNKNOWN"), ("", ""))


if __name__ == "__main__":
    unittest.main()
