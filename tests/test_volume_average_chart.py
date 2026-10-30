import ast
from pathlib import Path
from unittest import TestCase
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from stage_engine import weekly_bars


class VolumeAverageChartTests(TestCase):
    def chart(self, daily, weekly=False):
        path = Path(__file__).resolve().parents[1] / "app.py"
        nodes = [node for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)
                 and node.name in {"configure_price_volume_hover", "make_price_chart"}]
        weeks = weekly_bars(daily, as_of_date="2026-10-30", min_bars=1) if weekly else None
        ns = dict(pd=pd, go=go, make_subplots=make_subplots, prices=daily, weekly_by_symbol={"TEST": weeks})
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), ns)
        return ns["make_price_chart"]("TEST", period_is_weekly=weekly, chart_period="주봉" if weekly else "일봉"), weeks

    def daily(self, count=400):
        dates = pd.bdate_range(end="2026-10-28", periods=count)
        return pd.DataFrame(dict(date=dates, symbol="TEST", open=100, high=102, low=99, close=101,
                                 volume=np.arange(count, dtype=float) + 1))

    def test_50_daily_and_10_completed_weekly_volume_averages(self):
        daily = self.daily()
        for weekly, window, label in [(False, 50, "50일 거래량 평균"), (True, 10, "10주 거래량 평균")]:
            with self.subTest(weekly=weekly):
                fig, weeks = self.chart(daily, weekly)
                trace = next(t for t in fig.data if t.meta and t.meta.get("role") == "volume_average")
                source = weeks if weekly else daily
                np.testing.assert_allclose(trace.y, source.volume.rolling(window, min_periods=window).mean(), equal_nan=True)
                self.assertEqual(trace.name, label)
                self.assertEqual(trace.yaxis, "y2")
                self.assertEqual(trace.xaxis, "x2")
                self.assertNotEqual(trace.line.color, fig.data[1].line.color)
                if weekly:
                    self.assertLessEqual(pd.to_datetime(weeks.date).max(), pd.Timestamp("2026-10-23"))
                    expected = daily.set_index("date").volume.resample("W-FRI").sum().loc[weeks.date]
                    np.testing.assert_allclose(weeks.volume, expected)

    def test_short_missing_and_zero_volume_do_not_fabricate_average(self):
        for volume in [None, 0, float("nan")]:
            daily = self.daily()
            daily["volume"] = volume
            fig, _ = self.chart(daily)
            self.assertFalse(any(t.meta and t.meta.get("role") == "volume_average" for t in fig.data))
        fig, _ = self.chart(self.daily(20))
        self.assertFalse(any(t.meta and t.meta.get("role") == "volume_average" for t in fig.data))
