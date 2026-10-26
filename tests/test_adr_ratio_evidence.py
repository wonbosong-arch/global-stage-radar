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

    def test_ratio_with_ordinary_label_but_no_shares_suffix_is_captured(self):
        ratio, basis = extract_adr_ratio_from_listing_name(
            "HSBC HOLDINGS PLC ADR EACH REPR 5 ORD"
        )
        self.assertEqual(ratio, "5")
        self.assertEqual(basis, "ordinary_shares_per_depositary_share")

    def test_ratio_before_ordinary_label_is_captured(self):
        ratio, basis = extract_adr_ratio_from_listing_name(
            "UNILEVER PLC SPONSORED ADS EACH 1 ORD (REV SPT)"
        )
        self.assertEqual(ratio, "1")
        self.assertTrue(basis)

    def test_missing_description_is_not_guessed(self):
        self.assertEqual(extract_adr_ratio_from_listing_name("UNKNOWN"), ("", ""))


if __name__ == "__main__":
    unittest.main()
