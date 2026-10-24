import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
import pandas as pd
from kis_provider import KISOverseasPrices
from kis_domestic_provider import KISDomesticPrices

from stage_engine import classify_stage, relative_return_difference, weekly_bars, volume_confirmation, is_stale_daily_data
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
        self.get_kwargs = []

    def post(self, *args, **kwargs):
        return FakeKISResponse(200, {"access_token": "test-token", "expires_in": 3600})

    def get(self, *args, **kwargs):
        self.get_calls += 1
        self.get_kwargs.append(kwargs)
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

    def test_weekly_bars_includes_completed_friday_when_as_of_is_saturday(self):
        as_of = pd.Timestamp("2026-10-24")
        dates = pd.bdate_range(end=pd.Timestamp("2026-10-23"), periods=300)
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
        self.assertEqual(weekly["date"].max().normalize(), pd.Timestamp("2026-10-23"))

    def test_weekly_bars_excludes_stale_partial_week_when_latest_data_is_old(self):
        # Data stopped on Tuesday of the prior week. W-FRI would label that
        # partial bar with Friday's date, so it must not be treated as complete.
        as_of = pd.Timestamp("2026-10-23")
        dates = pd.bdate_range(end=pd.Timestamp("2026-10-13"), periods=300)
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
        self.assertLess(weekly["date"].max().normalize(), pd.Timestamp("2026-10-16"))

    def test_weekly_bars_excludes_thursday_only_latest_week_until_calendar_is_known(self):
        # A Thursday latest bar could mean Friday is a market holiday or that
        # the feed missed a session. Without an exchange calendar, fail closed.
        as_of = pd.Timestamp("2026-10-24")  # Saturday
        dates = pd.bdate_range(end=pd.Timestamp("2026-10-22"), periods=300)
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
        self.assertLess(weekly["date"].max().normalize(), pd.Timestamp("2026-10-23"))

    def test_weekly_aggregation_tolerates_a_missing_session_without_inventing_ohlc(self):
        dates = pd.bdate_range(end=pd.Timestamp("2026-10-23"), periods=300)
        dates = dates[dates != pd.Timestamp("2026-10-21")]  # missing Wednesday session
        daily = pd.DataFrame({
            "date": dates,
            "open": np.full(len(dates), 100.0),
            "high": np.full(len(dates), 102.0),
            "low": np.full(len(dates), 99.0),
            "close": np.full(len(dates), 101.0),
            "volume": np.full(len(dates), 100),
        })
        # Explicit values for the current week, with Wednesday absent.
        daily.loc[daily["date"] == pd.Timestamp("2026-10-19"), ["open", "high", "low", "close", "volume"]] = [100, 102, 99, 101, 100]
        daily.loc[daily["date"] == pd.Timestamp("2026-10-20"), ["open", "high", "low", "close", "volume"]] = [101, 103, 100, 102, 200]
        daily.loc[daily["date"] == pd.Timestamp("2026-10-22"), ["open", "high", "low", "close", "volume"]] = [103, 105, 102, 104, 300]
        daily.loc[daily["date"] == pd.Timestamp("2026-10-23"), ["open", "high", "low", "close", "volume"]] = [104, 106, 103, 105, 400]
        weekly = weekly_bars(daily, as_of_date="2026-10-24")
        self.assertIsNotNone(weekly)
        current = weekly.loc[weekly["date"].dt.normalize().eq(pd.Timestamp("2026-10-23"))]
        self.assertEqual(len(current), 1)
        self.assertEqual(float(current.iloc[0]["open"]), 100.0)
        self.assertEqual(float(current.iloc[0]["high"]), 106.0)
        self.assertEqual(float(current.iloc[0]["low"]), 99.0)
        self.assertEqual(float(current.iloc[0]["close"]), 105.0)
        self.assertEqual(float(current.iloc[0]["volume"]), 1000.0)

    @patch("kis_provider.time.sleep")
    def test_us_daily_prices_request_adjusted_price_mode(self, _sleep):
        session = FakeKISSession([
            FakeKISResponse(200, {"rt_cd": "0", "output2": [{
                "xymd": "20261020", "open": "100", "high": "105",
                "low": "99", "clos": "104", "tvol": "12345",
            }]}, headers={}),
        ])
        client = KISOverseasPrices(app_key="test-key", app_secret="test-secret", session=session)
        result = client.daily_bars("AAPL", max_pages=1, pause_seconds=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(session.get_kwargs[0]["params"]["MODP"], "1")

    @patch("kis_provider.time.sleep")
    def test_korea_daily_prices_request_adjusted_price_mode(self, _sleep):
        session = FakeKISSession([
            FakeKISResponse(200, {"rt_cd": "0", "output2": [{
                "stck_bsop_date": "20261020", "stck_oprc": "100",
                "stck_hgpr": "105", "stck_lwpr": "99",
                "stck_clpr": "104", "acml_vol": "12345",
            }]}, headers={}),
        ])
        client = KISDomesticPrices(app_key="test-key", app_secret="test-secret", session=session)
        result = client.domestic_daily_bars("005930", max_pages=1, pause_seconds=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(session.get_kwargs[0]["params"]["FID_ORG_ADJ_PRC"], "0")

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

    def test_stale_daily_data_guard_handles_old_future_and_recent_dates(self):
        as_of = pd.Timestamp("2026-10-23")
        self.assertTrue(is_stale_daily_data("2026-10-12", as_of_date=as_of, max_age_days=10))
        self.assertTrue(is_stale_daily_data("2026-10-24", as_of_date=as_of, max_age_days=10))
        self.assertFalse(is_stale_daily_data("2026-10-22", as_of_date=as_of, max_age_days=10))
        self.assertTrue(is_stale_daily_data(None, as_of_date=as_of, max_age_days=10))

    def test_relative_return_difference_uses_same_dates(self):
        asset = weekly_frame(np.linspace(100, 200, 60))
        benchmark = weekly_frame(np.linspace(100, 110, 60))
        relative = relative_return_difference(asset, benchmark, 26)
        self.assertGreater(relative.iloc[-1], 0)
        self.assertTrue(pd.isna(relative.iloc[0]))

    def test_relative_return_difference_does_not_match_different_week_labels(self):
        asset = weekly_frame(np.linspace(100, 200, 60))
        benchmark = weekly_frame(np.linspace(100, 110, 60))
        # Shift benchmark labels by one week: exact-date alignment must not
        # silently compare returns from different weekly endpoints.
        benchmark["date"] = benchmark["date"] + pd.Timedelta(days=1)
        relative = relative_return_difference(asset, benchmark, 26)
        self.assertTrue(relative.isna().all())

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


class UniverseDataIntegrityTests(unittest.TestCase):
    def test_active_universe_symbols_and_benchmarks_exist_in_price_snapshot(self):
        root = Path(__file__).resolve().parents[1]
        universe = pd.read_csv(root / "data" / "monitoring_universe.csv", dtype={"symbol": str})
        prices = pd.read_csv(root / "data" / "daily_prices.csv", dtype={"symbol": str})

        active = universe[universe["active"].astype(str).str.lower().eq("true")]
        available_symbols = set(prices["symbol"].astype(str).str.upper())
        required_symbols = set(active["symbol"].astype(str).str.upper())

        for column in ("market_benchmark", "sector_benchmark"):
            required_symbols.update(
                active[column].dropna().astype(str).str.upper().loc[lambda values: values.ne("")]
            )

        missing = sorted(required_symbols - available_symbols)
        self.assertEqual(
            missing, [],
            f"Active universe symbols or their benchmarks are missing from daily_prices.csv: {missing}",
        )

    def test_price_snapshot_has_recent_data_for_every_active_universe_symbol(self):
        root = Path(__file__).resolve().parents[1]
        universe = pd.read_csv(root / "data" / "monitoring_universe.csv", dtype={"symbol": str})
        prices = pd.read_csv(root / "data" / "daily_prices.csv", dtype={"symbol": str})
        active_symbols = set(
            universe.loc[universe["active"].astype(str).str.lower().eq("true"), "symbol"]
            .astype(str).str.upper()
        )
        latest_by_symbol = prices.assign(
            symbol=prices["symbol"].astype(str).str.upper(),
            date=pd.to_datetime(prices["date"], errors="coerce"),
        ).groupby("symbol")["date"].max()

        missing = sorted(symbol for symbol in active_symbols if symbol not in latest_by_symbol.index)
        self.assertEqual(missing, [], f"Active symbols have no price history: {missing}")
        invalid_dates = sorted(
            symbol for symbol in active_symbols
            if pd.isna(latest_by_symbol.get(symbol))
        )
        self.assertEqual(invalid_dates, [], f"Active symbols have invalid latest dates: {invalid_dates}")

        # The test name promises freshness, so reject both stale and future-dated
        # records. Ten calendar days matches the dashboard's Stage freshness guard.
        as_of = pd.Timestamp.today().normalize()
        stale_or_future = sorted(
            symbol for symbol in active_symbols
            if not pd.isna(latest_by_symbol.get(symbol))
            and (
                latest_by_symbol.get(symbol).normalize() > as_of
                or (as_of - latest_by_symbol.get(symbol).normalize()).days > 10
            )
        )
        self.assertEqual(
            stale_or_future, [],
            f"Active symbols have stale or future-dated prices: {stale_or_future}",
        )


if __name__ == "__main__":
    unittest.main()
