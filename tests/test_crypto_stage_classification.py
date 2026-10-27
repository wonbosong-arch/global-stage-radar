import unittest

from stage_engine import classify_stage


class CryptoStageClassificationTests(unittest.TestCase):
    def test_btc_can_be_screened_on_its_own_trend(self):
        label = classify_stage(
            close=110, ma30=100, slope4_pct=2.0,
            market_rs=float("nan"), sector_rs=float("nan"),
            asset_type="crypto_asset",
        )
        self.assertEqual(label, "Stage 2 후보")

    def test_eth_requires_positive_relative_strength_vs_btc_for_stage_two(self):
        label = classify_stage(
            close=110, ma30=100, slope4_pct=2.0,
            market_rs=-3.0, sector_rs=float("nan"),
            asset_type="crypto_asset",
        )
        self.assertNotEqual(label, "Stage 2 후보")


if __name__ == "__main__":
    unittest.main()
