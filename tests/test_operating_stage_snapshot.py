from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from operating_stage_snapshot import operating_stage


AS_OF = "2026-11-24"


class OperatingStageSnapshotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.universe = pd.DataFrame([
            ("SPY", "NYS", "market_etf", "SPY", "SPY", "Market"),
            ("XLI", "AMS", "sector_etf", "SPY", "XLI", "Industrials"),
            ("TEST", "NAS", "stock", "SPY", "XLI", "Industrials"),
            ("BTC-USD", "CRYPTO", "crypto_asset", "BTC-USD", "BTC-USD", "Crypto"),
        ], columns=["symbol", "exchange", "asset_type", "market_benchmark", "sector_benchmark", "sector"])
        histories = []
        for number, row in enumerate(cls.universe.itertuples(index=False), 1):
            frequency = "D" if row.exchange == "CRYPTO" else "B"
            dates = pd.date_range("2026-01-01", "2026-11-23", freq=frequency)
            close = 50 + pd.RangeIndex(len(dates)) * number / 10
            histories.append(pd.DataFrame({
                "date": dates, "symbol": row.symbol, "open": close, "high": close + 1,
                "low": close - 1, "close": close, "volume": 10000,
            }))
        cls.prices = pd.concat(histories, ignore_index=True)

    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "operating.zip"

    def check_equal(self, actual, expected):
        assert_frame_equal(actual[0], expected[0])
        self.assertEqual(list(actual[1]), list(expected[1]))
        for symbol in actual[1]:
            assert_frame_equal(actual[1][symbol], expected[1][symbol])
        self.assertEqual(actual[2], expected[2])

    def test_saved_results_are_reused_with_identical_prices_and_metadata(self):
        expected = operating_stage(self.universe, self.prices, AS_OF)
        self.assertIn("SPY", expected[1])
        self.check_equal(
            operating_stage(self.universe, self.prices, AS_OF, snapshot_path=self.path),
            expected,
        )
        with patch("operating_stage_snapshot.build_stage", side_effect=AssertionError("cache miss")):
            self.check_equal(
                operating_stage(self.universe, self.prices, AS_OF, snapshot_path=self.path),
                expected,
            )

    def test_price_classification_and_reference_date_invalidate_results(self):
        changed_prices = self.prices.copy()
        row = changed_prices.index[changed_prices.symbol.eq("SPY")][-1]
        changed_prices.loc[row, "volume"] += 1
        changed_universe = self.universe.copy()
        changed_universe.loc[changed_universe.symbol.eq("SPY"), "sector"] = "Updated classification"
        for universe, prices, day in (
            (self.universe, changed_prices, AS_OF),
            (changed_universe, self.prices, AS_OF),
            (self.universe, self.prices, "2026-11-25"),
        ):
            with self.subTest(day=day, changed_metadata=universe is changed_universe):
                operating_stage(self.universe, self.prices, AS_OF, snapshot_path=self.path)
                with patch("operating_stage_snapshot.build_stage", side_effect=ValueError("recomputed")):
                    with self.assertRaisesRegex(ValueError, "recomputed"):
                        operating_stage(universe, prices, day, snapshot_path=self.path)

    def test_damaged_or_unwritable_snapshot_falls_back_to_existing_calculation(self):
        expected = operating_stage(self.universe, self.prices, AS_OF)
        self.path.write_bytes(b"invalid archive")
        self.check_equal(
            operating_stage(self.universe, self.prices, AS_OF, snapshot_path=self.path),
            expected,
        )
        self.check_equal(
            operating_stage(self.universe, self.prices, AS_OF, snapshot_path=self.path / "nested.zip"),
            expected,
        )
