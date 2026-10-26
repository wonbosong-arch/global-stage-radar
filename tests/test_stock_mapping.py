import unittest

from stock_mapping import proposed_stock_mapping


class ProposedStockMappingTests(unittest.TestCase):
    def test_semiconductor_mapping_uses_supported_benchmark(self):
        result = proposed_stock_mapping("NVDA", "NAS")
        self.assertEqual(result["proposed_sector"], "Semiconductors")
        self.assertEqual(result["proposed_market_benchmark"], "SPY")
        self.assertEqual(result["proposed_sector_benchmark"], "SOXX")
        self.assertEqual(result["mapping_status"], "first_pass_review_required")
        self.assertIn("verify", result["mapping_note"].lower())

    def test_unknown_us_ticker_does_not_guess_sector(self):
        result = proposed_stock_mapping("UNKNOWNXYZ", "NYS")
        self.assertEqual(result["proposed_market_benchmark"], "SPY")
        self.assertEqual(result["proposed_sector"], "")
        self.assertEqual(result["proposed_sector_benchmark"], "")
        self.assertEqual(result["mapping_status"], "sector_mapping_missing")

    def test_adr_country_suggests_region_proxy_without_claiming_verified(self):
        result = proposed_stock_mapping("TME", "NAS", issuer_country_code="CN")
        self.assertEqual(result["proposed_market"], "China (ADR issuer; proxy)")
        self.assertEqual(result["proposed_market_benchmark"], "MCHI")
        self.assertEqual(result["mapping_status"], "sector_mapping_missing")
        self.assertIn("verify", result["mapping_note"].lower())

    def test_krx_semiconductor_mapping_preserves_string_ticker(self):
        result = proposed_stock_mapping("005930", "KRX")
        self.assertEqual(result["proposed_market"], "South Korea")
        self.assertEqual(result["proposed_sector"], "Semiconductors")
        self.assertEqual(result["proposed_market_benchmark"], "069500")
        self.assertEqual(result["proposed_sector_benchmark"], "091160")
        self.assertEqual(result["mapping_status"], "first_pass_review_required")

    def test_current_us_candidates_with_missing_sector_get_review_only_suggestions(self):
        expected = {
            "CCEP": "Consumer Staples",
            "SPOT": "Communication Services",
            "SYK": "Health Care",
            "EQNR": "Energy",
            "SNOW": "Information Technology",
        }
        for symbol, sector in expected.items():
            with self.subTest(symbol=symbol):
                result = proposed_stock_mapping(symbol, "NYS")
                self.assertEqual(result["proposed_sector"], sector)
                self.assertEqual(result["mapping_status"], "first_pass_review_required")
                self.assertTrue(result["proposed_market_benchmark"])
                self.assertIn("verify", result["mapping_note"].lower())

    def test_current_krx_candidates_get_sector_suggestions_but_no_invented_sector_etf(self):
        expected = {
            "402340": "Financials", "373220": "Industrials",
            "009150": "Information Technology", "207940": "Health Care",
            "005380": "Consumer Discretionary", "105560": "Financials",
            "032830": "Financials", "028260": "Industrials",
            "068270": "Health Care", "055550": "Financials",
            "000270": "Consumer Discretionary", "006400": "Industrials",
            "012450": "Industrials", "034020": "Industrials",
            "034730": "Financials", "086790": "Financials",
            "329180": "Industrials", "012330": "Consumer Discretionary",
            "000810": "Financials", "035420": "Communication Services",
            "066570": "Consumer Discretionary", "096770": "Energy",
            "010120": "Industrials", "316140": "Financials",
            "005490": "Materials", "011200": "Industrials",
            "138040": "Financials",
        }
        for symbol, sector in expected.items():
            with self.subTest(symbol=symbol):
                result = proposed_stock_mapping(symbol, "KRX")
                self.assertEqual(result["proposed_sector"], sector)
                self.assertEqual(result["proposed_market_benchmark"], "069500")
                self.assertEqual(result["proposed_sector_benchmark"], "")
                self.assertEqual(result["mapping_status"], "first_pass_review_required")
                self.assertIn("verify", result["mapping_note"].lower())

    def test_every_sector_benchmark_suggestion_is_nonempty(self):
        symbols = ["NVDA", "AAPL", "GOOGL", "AMZN", "WMT", "XOM", "JPM",
                   "LLY", "CAT", "LIN", "CEG", "PLD"]
        for symbol in symbols:
            with self.subTest(symbol=symbol):
                result = proposed_stock_mapping(symbol, "NAS")
                self.assertTrue(result["proposed_sector"])
                self.assertTrue(result["proposed_sector_benchmark"])
                self.assertEqual(result["proposed_market_benchmark"], "SPY")
                self.assertEqual(result["mapping_status"], "first_pass_review_required")


if __name__ == "__main__":
    unittest.main()
