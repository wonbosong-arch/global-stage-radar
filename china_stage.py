"""Readiness metrics for reconciled mainland research; no activation side effects."""
import pandas as pd
from stage_engine import weekly_bars


def stage_readiness(daily, *, as_of_date=None):
    """Only reconciled bars may enter here. Adjustment evidence is still absent.

    Never infer adjusted-history verification from length, a ticker or a flag.
    Existing engine supplies completed weeks and indicators, but all current
    mainland research remains withheld until adjustment evidence is reviewed.
    """
    weeks = weekly_bars(daily, as_of_date=as_of_date, calendar_name='XSHG', min_bars=1)
    count = 0 if weeks is None else len(weeks)
    return {'stage_label': '판정 보류', 'completed_weeks': count,
            'stage_reason': ('검증 주봉 35개 미만 · ' if count < 35 else '') + '조정 기준 미검증',
            'ma30': None, 'slope4_pct': None, 'ret26_pct': None,
            'stage2_new_entry': None, 'operational_eligible': False}
