from pathlib import Path
import pandas as pd
import unittest
try:
    import pytest
except ImportError:
    raise unittest.SkipTest("pytest-only private research regressions")
from china_dashboard import load_research, load_metadata
from china_stage import stage_readiness


def test_default_does_not_read_price_data(monkeypatch):
    monkeypatch.delenv('CHINA_PRIVATE_SNAPSHOT_DIR', raising=False)
    with pytest.raises(PermissionError, match='미설정'):
        load_research()
    with pytest.raises(PermissionError, match='공개 저장소 밖'):
        load_research(Path(__file__).resolve().parents[1])
    assert len(load_metadata()) == 12


@pytest.mark.parametrize('days', [60, 250])
def test_even_long_unadjusted_history_cannot_promote(days):
    dates = pd.bdate_range('2025-01-01', periods=days)
    frame = pd.DataFrame({'date': dates, 'open': 10., 'high': 11., 'low': 9., 'close': 10., 'volume': 100})
    result = stage_readiness(frame, as_of_date='2026-11-03')
    assert result['stage_label'] == '판정 보류'
    assert result['ret26_pct'] is None
    assert result['stage2_new_entry'] is None
    assert not result['operational_eligible']


def test_metadata_navigation_without_private_input(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv('CHINA_PRIVATE_SNAPSHOT_DIR', raising=False)
    app = AppTest.from_file(str(Path('app.py').resolve()), default_timeout=60).run()
    app.radio(key='analysis_navigation_choice').set_value('sectors').run()
    app.radio(key='china_sector_source').set_value('중국 본토 SSE · 연구·관찰 12종').run()
    assert not app.exception
    assert any('12종 모두' in x.value for x in app.caption)
    assert not app.get('plotly_chart')
    for area in ('markets_commodities', 'stocks', 'stage2', 'sectors', 'favorites'):
        app.radio(key='analysis_navigation_choice').set_value(area).run()
        assert not app.exception
