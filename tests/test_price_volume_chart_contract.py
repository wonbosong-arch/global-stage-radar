import unittest

import pandas as pd

from browser_checks.chart_cases import chart_case


class PriceVolumeChartContractTests(unittest.TestCase):
    def test_short_history_keeps_all_available_bars(self):
        for case in ('weekly', 'daily', 'compact', 'review'):
            with self.subTest(case=case):
                fig = chart_case(case, bars=20)
                self.assertEqual(len(fig.data[0].x), 20)
                self.assertEqual(pd.Timestamp(fig.layout.xaxis2.range[0]), pd.Timestamp(fig.data[0].x[0]))
                self.assertEqual(pd.Timestamp(fig.layout.xaxis2.range[1]), pd.Timestamp(fig.data[0].x[-1]))

    def test_daily_weekly_compact_and_review_preserve_data_and_shared_hover(self):
        for case in ('weekly', 'daily', 'compact', 'review'):
            with self.subTest(case=case):
                fig = chart_case(case)
                candle = next(trace for trace in fig.data if trace.type == 'candlestick')
                volume = next(trace for trace in fig.data if trace.type == 'bar')
                hover = next(trace for trace in fig.data if trace.name == '캔들 정보')
                self.assertEqual(len(candle.x), 220)  # Viewport must not truncate history.
                self.assertEqual(list(candle.x), list(volume.x))
                self.assertEqual(list(candle.x), list(hover.x))
                self.assertEqual(candle.hoverinfo, 'skip')
                self.assertIsNone(candle.hovertemplate)
                self.assertTrue(all(trace.xaxis == 'x2' for trace in fig.data))
                self.assertEqual(fig.layout.hoversubplots, 'axis')
                self.assertFalse(fig.layout.xaxis2.autorange)
                self.assertFalse(fig.layout.xaxis2.rangeslider.visible)
                self.assertEqual(pd.Timestamp(fig.layout.xaxis2.range[0]), pd.Timestamp(candle.x[-150]))
                self.assertEqual(pd.Timestamp(fig.layout.xaxis2.range[1]), pd.Timestamp(candle.x[-1]))
                self.assertTrue(fig.layout.yaxis.fixedrange)
                self.assertTrue(fig.layout.yaxis2.fixedrange)
                self.assertFalse(hover.showlegend)
                self.assertEqual(candle.legendgroup, hover.legendgroup)
                self.assertEqual(float(hover.customdata[100][3]), float(candle.close[100]))
