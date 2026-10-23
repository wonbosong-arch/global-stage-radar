import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
import pandas as pd
from kis_provider import KISOverseasPrices

from stage_engine import classify_stage, relative_return_difference, weekly_bars, volume_confirmation
from refresh_daily_prices import preserve_failed_symbol_history


def weekly_frame(closes):
    dates = pd.date_range("2024-01-05", periods=len(closes), freq="W-FRI")
    return pd.DataFrame({
        "date": dates,
        "open": closes,
        "high": np.asarray(closes) * 1.01,
        "low": np.asarray(closes) * 0.99,
        "close": closes,
        "volume": np.full(len(closes), 1000),
    })



class FakeKISResponse:
    def __init__(self, status_code, payload, text=None, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else str(payload)
        self.headers = headers or {}
        self.ok = 200 <= status_code < 400

    def json(self):
        return self._payload


class FakeKISSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.get_calls = 0

    def post(self, *args, **kwargs):
        return FakeKISResponse(200, {"access_token": "test-token", "expires_in": 3600})

    def get(self, *args, **kwargs):
        self.get_calls += 1
        return self.responses.pop(0)


class StageEngineTests(unittest.TestCase):
    def test_weekly_bars_aggregates_daily_data(self):
        dates = pd.bdate_range("2024-01-01", periods=300)
        daily = pd.DataFrame({
            "date": dates,
            "open": np.arange(300) + 100.0,
            "high": np.arange(300) + 102.0,
            "low": np.arange(300) + 99.0,
            "close": np.arange(300) + 101.0,
            "volume": np.full(300, 100),
        })
        weekly = weekly_bars(daily)
        self.assertIsNotNone(weekly)
        self.assertGreaterEqual(len(weekly), 35)
        self.assertTrue((weekly["high"] >= weekly["low"]).all())
        self.assertAlmostEqual(weekly.iloc[0]["volume"], 500)

    def test_weekly_bars_does_not_include_future_friday_label(self):
        # When data ends during the current week, W-FRI would otherwise label
        # the incomplete bar with a Friday date that is still in the future.
        end = pd.Timestamp.today().normalize()
        dates = pd.bdate_range(end=end, periods=300)
        daily = pd.DataFrame({
            "date": dates,
            "open": np.full(len(dates), 100.0),
            "high": np.full(len(dates), 102.0),
            "low": np.full(len(dates), 99.0),
            "close": np.linspace(100.0, 150.0, len(dates)),
            "volume": np.full(len(dates), 100),
        })
        weekly = weekly_bars(daily)
        self.assertIsNotNone(weekly)
        self.assertLessEqual(weekly["date"].max().normalize(), end)


    def test_weekly_bars_excludes_current_week_even_on_friday(self):
        as_of = pd.Timestamp("2026-10-23")
        dates = pd.bdate_range(end=as_of, periods=300)
        daily = pd.DataFrame({
            "date": dates,
            "open": np.full(len(dates), 100.0),
            "high": np.full(len(dates), 102.0),
            "low": np.full(len(dates), 99.0),
            "close": np.linspace(100.0, 150.0, len(dates)),
            "volume": np.full(len(dates), 100),
        })
        weekly = weekly_bars(daily, as_of_date=as_of)
        self.assertIsNotNone(weekly)
        self.assertLess(weekly["date"].max().normalize(), as_of)

    @patch("kis_provider.time.sleep")
    def test_kis_provider_retries_transient_server_error(self, _sleep):
        session = FakeKISSession([
            FakeKISResponse(500, {"rt_cd": "1", "msg_cd": "EGW00201", "msg1": "rate limit"}),
            FakeKISResponse(200, {
                "rt_cd": "0",
                "output2": [{
                    "xymd": "20261020",
                    "open": "100",
                    "high": "105",
                    "low": "99",
                    "clos": "104",
                    "tvol": "12345",
                }],
            }),
        ])
        client = KISOverseasPrices(app_key="test-key", app_secret="test-secret", session=session)
        result = client.daily_bars("AAPL", max_pages=1, pause_seconds=0)
        self.assertEqual(session.get_calls, 2)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["symbol"], "AAPL")
        self.assertEqual(float(result.iloc[0]["close"]), 104.0)

    @patch("kis_provider.time.sleep")
    def test_kis_provider_rejects_response_without_success_code(self, _sleep):
        session = FakeKISSession([
            FakeKISResponse(200, {
                "output2": [{
                    "xymd": "20261020",
                    "open": "100",
                    "high": "105",
                    "low": "99",
                    "clos": "104",
                    "tvol": "12345",
                }],
            }),
        ])
        client = KISOverseasPrices(app_key="test-key", app_secret="test-secret", session=session)
        with self.assertRaisesRegex(RuntimeError, "unknown error|no error code"):
            client.daily_bars("AAPL", max_pages=1, pause_seconds=0)

    def test_relative_return_difference_uses_same_dates(self):
        asset = weekly_frame(np.linspace(100, 200, 60))
        benchmark = weekly_frame(np.linspace(100, 110, 60))
        relative = relative_return_difference(asset, benchmark, 26)
        self.assertGreater(relative.iloc[-1], 0)
        self.assertTrue(pd.isna(relative.iloc[0]))

    def test_stock_requires_market_and_sector_outperformance(self):
        label = classify_stage(120, 100, 2.0, 5.0, -1.0, "stock")
        self.assertEqual(label, "Stage 2A 관찰 후보")

    def test_etf_can_be_stage_two_without_sector_relative_series(self):
        label = classify_stage(120, 100, 2.0, 5.0, np.nan, "sector_etf")
        self.assertEqual(label, "Stage 2 후보")

    def test_market_proxy_can_be_classified_without_self_relative_strength(self):
        label = classify_stage(120, 100, 2.0, np.nan, np.nan, "market_etf")
        self.assertEqual(label, "Stage 2 후보")

    def test_volume_confirmation_is_soft_context_not_a_stage_gate(self):
        # Low volume is a note for review, not a reason to reject a Stage 2 label.
        self.assertEqual(volume_confirmation(0.5), "거래량 약함 · 참고만")
        self.assertEqual(volume_confirmation(1.0), "거래량 보통")
        self.assertEqual(volume_confirmation(1.8), "거래량 동반 · 추세 보강")
        self.assertEqual(volume_confirmation(np.nan), "거래량 데이터 부족")
        label = classify_stage(120, 100, 2.0, 5.0, 3.0, "stock")
        self.assertEqual(label, "Stage 2 후보")

    def test_declining_below_average_is_downtrend_watch(self):
        label = classify_stage(80, 100, -1.0, -3.0, -2.0, "stock")
        self.assertEqual(label, "하락 추세 관찰")


class RefreshSnapshotSafetyTests(unittest.TestCase):
    def test_failed_symbols_keep_old_history_while_successful_symbols_refresh(self):
        with TemporaryDirectory() as directory:
            previous_path = Path(directory) / "daily_prices.csv"
            pd.DataFrame([
                {"date": "2026-10-20", "symbol": "AAA", "close": 10.0},
                {"date": "2026-10-20", "symbol": "BBB", "close": 20.0},
            ]).to_csv(previous_path, index=False)
            fresh = pd.DataFrame([
                {"date": "2026-10-23", "symbol": "AAA", "close": 11.0},
            ])

            combined, preserved = preserve_failed_symbol_history(
                fresh, [{"symbol": "BBB", "error": "temporary API error"}], previous_path
            )

            self.assertEqual(preserved, ["BBB"])
            self.assertEqual(set(combined["symbol"]), {"AAA", "BBB"})
            self.assertEqual(
                combined.loc[combined["symbol"] == "AAA", "close"].tolist(), [11.0]
            )
            self.assertEqual(
                combined.loc[combined["symbol"] == "BBB", "close"].tolist(), [20.0]
            )

    def test_successful_refresh_does_not_retain_removed_symbols(self):
        with TemporaryDirectory() as directory:
            previous_path = Path(directory) / "daily_prices.csv"
            pd.DataFrame([
                {"date": "2026-10-20", "symbol": "OLD", "close": 20.0},
            ]).to_csv(previous_path, index=False)
            fresh = pd.DataFrame([
                {"date": "2026-10-23", "symbol": "NEW", "close": 30.0},
            ])

            combined, preserved = preserve_failed_symbol_history(
                fresh, [], previous_path
            )

            self.assertEqual(preserved, [])
            self.assertEqual(set(combined["symbol"]), {"NEW"})


if __name__ == "__main__":
    unittest.main()
