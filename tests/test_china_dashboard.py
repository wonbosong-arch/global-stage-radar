import json
from pathlib import Path
from china_dashboard import load_metadata, load_research, research_prices_authorized, RIGHTS_BLOCK


def test_published_tree_excludes_restricted_snapshots():
    import subprocess
    tracked = subprocess.check_output(['git', '-c', 'safe.directory=*', 'ls-files'], text=True).splitlines()
    excluded = {'data/china_candidate_prices.csv', 'data/china_candidate_prices_status.json',
                'data/china_candidate_stage_report.csv', 'data/china_candidate_screening_review.csv',
                'data/china_sector_candidate_review.json', 'data/china_sector_representative_review.csv'}
    assert not excluded.intersection(tracked)
    assert not any(p.startswith(('research/china_dashboard_snapshot/',
                                 'research/china_etf_review_20261102/')) for p in tracked)


def test_metadata_has_only_identity_fields():
    rows = load_metadata()
    assert len(rows) == len({r['symbol'] for r in rows}) == 12
    allowed = {'symbol', 'name_en', 'sector_category', 'tracked_index_code',
               'tracked_index_name', 'benchmark_source_url', 'index_source_url'}
    assert all(set(r) == allowed for r in rows)
    assert all(r['benchmark_source_url'].startswith('https://') for r in rows)


def test_price_access_blocked_without_files_or_with_environment(monkeypatch, tmp_path):
    import pytest
    monkeypatch.setenv('CHINA_RESEARCH_ENABLED', 'true')
    monkeypatch.setattr(Path, 'read_text', lambda *a, **k: (_ for _ in ()).throw(AssertionError('read')))
    assert not research_prices_authorized()
    with pytest.raises(PermissionError, match='사용권 미확인'):
        load_research(tmp_path / 'missing')


def test_real_widgets_block_prices_and_preserve_existing_areas(monkeypatch):
    import pandas as pd
    from streamlit.testing.v1 import AppTest
    def reject(*a, **k):
        raise AssertionError('unexpected provider request')
    monkeypatch.setattr('requests.sessions.Session.request', reject)
    original = pd.read_csv
    def guarded(path, *a, **k):
        if Path(path).name in {'china_candidate_prices.csv', 'china_candidate_stage_report.csv'}:
            raise AssertionError('restricted file read')
        return original(path, *a, **k)
    monkeypatch.setattr(pd, 'read_csv', guarded)
    app = AppTest.from_file(str(Path('app.py').resolve()), default_timeout=60).run()
    app.radio(key='active_analysis_area').set_value('sectors').run()
    app.radio(key='china_sector_source').set_value('중국 본토 SSE · 연구·관찰 12종').run()
    assert not app.exception
    assert any(e.value == RIGHTS_BLOCK for e in app.error)
    assert len([m for m in app.markdown if '**512' in m.value or '**515' in m.value or '**516' in m.value or '**588' in m.value]) == 12
    assert not app.get('plotly_chart')
    assert not [b for b in app.get('download_button') if str(b.key).startswith('china_')]
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    app.radio(key='active_analysis_area').set_value('sectors').run()
    assert app.radio(key='china_sector_source').value == '중국 본토 SSE · 연구·관찰 12종'
    assert any(e.value == RIGHTS_BLOCK for e in app.error)
    app.radio(key='china_sector_source').set_value('기존 업종 · 미국 상장 중국 프록시 포함').run()
    for area in ('markets_commodities', 'stocks', 'stage2', 'sectors'):
        app.radio(key='active_analysis_area').set_value(area).run()
        assert not app.exception
