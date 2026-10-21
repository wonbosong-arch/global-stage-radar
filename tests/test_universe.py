import io
import unittest

from universe import read_universe


HEADER = "symbol,name,market,sector,asset_type,market_cap_usd,market_benchmark,sector_benchmark,exchange\n"
VALID_ROW = "AAPL,Apple Inc.,United States,Technology,stock,3000000000000,QQQ,XLK,NAS\n"


class UniverseValidationTests(unittest.TestCase):
    def test_valid_universe_is_normalized(self):
        result = read_universe(io.StringIO(HEADER + VALID_ROW.lower().replace("apple inc.", "Apple Inc.")))
        self.assertEqual(result.iloc[0]["symbol"], "AAPL")
        self.assertEqual(result.iloc[0]["asset_type"], "stock")
        self.assertEqual(result.iloc[0]["exchange"], "NAS")

    def test_missing_asset_type_is_rejected(self):
        row = "AAPL,Apple Inc.,United States,Technology,,3000000000000,QQQ,XLK,NAS\n"
        with self.assertRaisesRegex(ValueError, "asset_type"):
            read_universe(io.StringIO(HEADER + row))

    def test_duplicate_symbols_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "중복 symbol"):
            read_universe(io.StringIO(HEADER + VALID_ROW + VALID_ROW))

    def test_negative_market_cap_is_rejected(self):
        row = "AAPL,Apple Inc.,United States,Technology,stock,-1,QQQ,XLK,NAS\n"
        with self.assertRaisesRegex(ValueError, "음수"):
            read_universe(io.StringIO(HEADER + row))

    def test_non_numeric_market_cap_is_rejected(self):
        row = "AAPL,Apple Inc.,United States,Technology,stock,unknown,QQQ,XLK,NAS\n"
        with self.assertRaisesRegex(ValueError, "숫자가 아닌"):
            read_universe(io.StringIO(HEADER + row))

    def test_stock_without_sector_benchmark_is_rejected(self):
        row = "AAPL,Apple Inc.,United States,Technology,stock,3000000000000,QQQ,,NAS\n"
        with self.assertRaisesRegex(ValueError, "업종 벤치마크"):
            read_universe(io.StringIO(HEADER + row))

    def test_korean_ticker_preserves_leading_zero_and_defaults_to_krx(self):
        header = "symbol,name,market,sector,asset_type,market_cap_usd,market_benchmark,sector_benchmark\n"
        row = "005930,Sample Co.,South Korea,Technology,stock,100000000000,069500,091160\n"
        result = read_universe(io.StringIO(header + row))
        self.assertEqual(result.iloc[0]["symbol"], "005930")
        self.assertEqual(result.iloc[0]["exchange"], "KRX")

    def test_exchange_defaults_to_nas_when_column_is_absent(self):
        header = "symbol,name,market,sector,asset_type,market_cap_usd,market_benchmark,sector_benchmark\n"
        row = "AAPL,Apple Inc.,United States,Technology,stock,3000000000000,QQQ,XLK\n"
        result = read_universe(io.StringIO(header + row))
        self.assertEqual(result.iloc[0]["exchange"], "NAS")


if __name__ == "__main__":
    unittest.main()
