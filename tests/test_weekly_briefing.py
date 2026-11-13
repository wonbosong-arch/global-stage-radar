import unittest

import pandas as pd

from weekly_briefing import (STAGE2, UNAVAILABLE, percent, ranked_rows, stage_summary,
                             transition, weekly_snapshot)


def fixture():
    rows = pd.DataFrame([
        dict(symbol='A', exchange='NYS', asset_type_norm='market_etf', market='US',
             last_date='2026-11-06', stage_label=STAGE2, previous_stage_label='중립 / 추가 확인', ret26_pct=20),
        dict(symbol='B', exchange='NAS', asset_type_norm='market_etf', market='JP',
             last_date='2026-11-06', stage_label='중립 / 추가 확인', previous_stage_label=STAGE2, ret26_pct=10),
        dict(symbol='C', exchange='NYS', asset_type_norm='market_etf', market='US',
             last_date='2026-11-06', stage_label=STAGE2, previous_stage_label=STAGE2, ret26_pct=10),
    ])
    history = {symbol: pd.DataFrame(dict(date=pd.to_datetime(['2026-10-30', '2026-11-06']),
        close=[100.0, 105.0], ret26_pct=[float(prior), float(current)]))
        for symbol, prior, current in [('A', 9, 20), ('B', 20, 10), ('C', 10, 10)]}
    return rows, history


class WeeklyBriefingTests(unittest.TestCase):
    def test_aligned_weekly_values_membership_conservation_ties_and_no_mutation(self):
        screen, history = fixture()
        original = screen.copy(deep=True)
        rows, week = weekly_snapshot(screen, history)
        self.assertEqual(week, pd.Timestamp('2026-11-06'))
        counts = stage_summary(rows)
        self.assertEqual((counts['current'], counts['previous'], counts['delta'], counts['entries'], counts['exits']), (2, 2, 0, 1, 1))
        self.assertEqual(counts['delta'], counts['entries'] - counts['exits'])
        self.assertAlmostEqual(rows.iloc[0].return1w, 5)
        self.assertEqual(rows.iloc[0].strength_change, 11)
        ranks = ranked_rows(rows).set_index('symbol')
        self.assertEqual(ranks.loc['A', 'rank_move'], 2)
        self.assertEqual(ranks.loc['B', 'rank'], ranks.loc['C', 'rank'])
        pd.testing.assert_frame_equal(screen, original)

    def test_missing_stage_history_never_implies_new_entry_or_zero_delta(self):
        screen, history = fixture()
        screen['previous_stage_label'] = '이전 주 데이터 부족'
        rows, _ = weekly_snapshot(screen, history)
        counts = stage_summary(rows)
        self.assertEqual(counts['current'], 2)
        for key in ('previous', 'delta', 'entries', 'exits'):
            self.assertIsNone(counts[key])
        self.assertEqual(transition(rows.iloc[0]), UNAVAILABLE)
        # Prices alone still support a real weekly return, not a Stage history.
        self.assertAlmostEqual(rows.iloc[0].return1w, 5)

    def test_gaps_missing_prices_mixed_dates_and_ambiguous_venues_withhold_comparisons(self):
        for kind in ('gap', 'missing', 'mixed', 'duplicate', 'nonfinite'):
            with self.subTest(kind=kind):
                screen, history = fixture()
                if kind == 'gap':
                    history['A'].loc[0, 'date'] = pd.Timestamp('2026-10-23')
                elif kind == 'missing':
                    history.pop('A')
                elif kind == 'mixed':
                    screen.loc[0, 'last_date'] = '2026-10-30'
                elif kind == 'duplicate':
                    screen = pd.concat([screen, screen.iloc[[0]].assign(exchange='NAS')])
                else:
                    history['A'].loc[0, 'close'] = float('inf')
                rows, _ = weekly_snapshot(screen, history)
                self.assertFalse(rows.iloc[0].week_comparable)
                self.assertIsNone(stage_summary(rows)['delta'])
                self.assertTrue(ranked_rows(rows).rank_move.isna().all())
                self.assertEqual(percent(rows.iloc[0].return1w), UNAVAILABLE)

    def test_holds_are_not_exits_and_filtered_ranking_recomputes_both_weeks(self):
        screen, history = fixture()
        screen.loc[1, 'stage_label'] = '벤치마크 데이터 부족 · 판정 보류'
        rows, _ = weekly_snapshot(screen, history)
        self.assertFalse(rows.iloc[1].stage_comparable)
        self.assertIsNone(stage_summary(rows)['exits'])
        us = ranked_rows(rows[rows.market.eq('US')]).set_index('symbol')
        self.assertEqual(us.loc['A', 'rank_move'], 1)

    def test_unavailable_return_is_never_an_example_and_empty_scope_is_unknown(self):
        screen, history = fixture()
        history['A'].loc[0, 'ret26_pct'] = float('nan')
        rows, _ = weekly_snapshot(screen, history)
        self.assertTrue(ranked_rows(rows).rank_move.isna().all())
        self.assertEqual(percent(None), UNAVAILABLE)
        self.assertEqual(percent(float('inf')), UNAVAILABLE)
        self.assertIsNone(stage_summary(rows.iloc[:0])['delta'])


if __name__ == '__main__':
    unittest.main()
