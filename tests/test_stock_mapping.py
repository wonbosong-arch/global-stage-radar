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


    def test_active_stock_mappings_reference_existing_benchmarks(self):
        from pathlib import Path
        import pandas as pd

        repo_root = Path(__file__).resolve().parents[1]
        universe = pd.read_csv(
            repo_root / "data" / "monitoring_universe.csv",
            dtype={"symbol": str},
        ).fillna("")
        active = universe[
            universe["active"].astype(str).str.lower().eq("true")
            & universe["asset_type"].eq("stock")
        ]
        available_symbols = set(universe.loc[
            universe["active"].astype(str).str.lower().eq("true"), "symbol"
        ].astype(str))
        for row in active.itertuples(index=False):
            with self.subTest(symbol=row.symbol):
                suggestion = proposed_stock_mapping(row.symbol, row.exchange)
                self.assertIn(
                    suggestion["proposed_market_benchmark"],
                    available_symbols,
                    "Proposed market benchmark must exist in the active monitoring universe.",
                )
                self.assertEqual(
                    suggestion["proposed_sector"],
                    row.sector,
                    "Active-stock sector should agree with the first-pass mapping.",
                )
                self.assertEqual(
                    suggestion["proposed_sector_benchmark"],
                    row.sector_benchmark,
                    "Proposed sector benchmark should agree with the active mapping.",
                )
                self.assertIn(
                    suggestion["proposed_sector_benchmark"],
                    available_symbols,
                    "Proposed sector benchmark must exist in the active monitoring universe.",
                )


    def test_unknown_krx_stock_does_not_guess_sector_or_sector_benchmark(self):
        result = proposed_stock_mapping("123456", "KRX")
        self.assertEqual(result["proposed_market"], "South Korea")
        self.assertEqual(result["proposed_market_benchmark"], "069500")
        self.assertEqual(result["proposed_sector"], "")
        self.assertEqual(result["proposed_sector_benchmark"], "")
        self.assertEqual(result["mapping_status"], "sector_mapping_missing")
        self.assertIn("manually", result["mapping_note"].lower())

    def test_krx_mapping_keeps_leading_zeroes_and_requires_review(self):
        for symbol in ("005930", "000660"):
            with self.subTest(symbol=symbol):
                result = proposed_stock_mapping(symbol, "KRX")
                self.assertEqual(result["proposed_market_benchmark"], "069500")
                self.assertEqual(result["proposed_sector_benchmark"], "091160")
                self.assertEqual(result["mapping_status"], "first_pass_review_required")
                self.assertIn("verify", result["mapping_note"].lower())


if __name__ == "__main__":
    unittest.main()
