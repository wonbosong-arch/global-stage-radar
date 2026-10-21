import unittest
import pandas as pd

from market_data import MarketDataError, normalize_ohlcv


class MarketDataNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.valid = pd.DataFrame([{
            "date": "2026-10-20",
            "symbol": "aapl",
            "open": 100,
            "high": 105,
            "low": 99,
            "close": 104,
            "volume": 12345,
        }])

    def test_normalizes_symbol_and_sorts_output(self):
        result = normalize_ohlcv(self.valid)
        self.assertEqual(result.iloc[0]["symbol"], "AAPL")
        self.assertEqual(pd.Timestamp(result.iloc[0]["date"]), pd.Timestamp("2026-10-20"))

    def test_rejects_inconsistent_high_low(self):
        bad = self.valid.copy()
        bad.loc[0, "high"] = 98
        with self.assertRaisesRegex(MarketDataError, "고가/저가"):
            normalize_ohlcv(bad)

    def test_rejects_negative_volume(self):
        bad = self.valid.copy()
        bad.loc[0, "volume"] = -1
        with self.assertRaisesRegex(MarketDataError, "거래량"):
            normalize_ohlcv(bad)

    def test_rejects_conflicting_duplicate_dates(self):
        second = self.valid.copy()
        second.loc[0, "close"] = 103
        second.loc[0, "high"] = 106
        with self.assertRaisesRegex(MarketDataError, "서로 다른 가격"):
            normalize_ohlcv(pd.concat([self.valid, second], ignore_index=True))

    def test_collapses_identical_duplicate_rows(self):
        result = normalize_ohlcv(pd.concat([self.valid, self.valid], ignore_index=True))
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
