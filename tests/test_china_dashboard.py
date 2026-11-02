import ast
import hashlib
import json
from pathlib import Path
import shutil
import pandas as pd
from china_dashboard import SNAPSHOT, load_research


def test_frozen_evidence_limits_preview_and_never_promotes_stage():
    candidates, preview, manifest = load_research()
    assert len(candidates) == 12
    assert not candidates.operational_eligible.any()
    assert not candidates.stage2_new_entry.any()
    assert candidates.stage_label.str.contains('판정 보류').all()
    assert set(preview.symbol) == set(candidates.symbol) - {'512400'}
    assert len(preview) == 660
    assert preview.date.min() == pd.Timestamp('2026-07-28')
    assert preview.date.max() == pd.Timestamp('2026-10-27')
    assert len(pd.read_csv(SNAPSHOT / 'china_candidate_prices.csv')) == 8905
    assert manifest['rights'] == 'unverified_research_only_no_operational_use'


def test_tampered_snapshot_fails_closed(tmp_path):
    import pytest
    shutil.copytree(SNAPSHOT, tmp_path / 'snapshot')
    root = tmp_path / 'snapshot'
    with (root / 'china_candidate_prices.csv').open('ab') as f:
        f.write(b'\n')
    with pytest.raises(ValueError, match='무결성'):
        load_research(root)


def test_structural_price_change_still_blocks_after_manifest_refresh(tmp_path):
    root = tmp_path / 'snapshot'
    shutil.copytree(SNAPSHOT, root)
    path = root / 'china_candidate_prices.csv'
    prices = pd.read_csv(path, dtype={'symbol': str})
    prices.loc[prices.symbol.eq('512800') & prices.date.eq('2026-10-27'), 'close'] = -1
    prices.to_csv(path, index=False)
    manifest = json.loads((root / 'manifest.json').read_text())
    manifest['files'][path.name]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    (root / 'manifest.json').write_text(json.dumps(manifest))
    _, preview, _ = load_research(root)
    assert '512800' not in set(preview.symbol)


def test_research_chart_uses_shared_hover_volume_and_short_150_bar_window():
    from browser_checks.chart_cases import chart_case
    # Execute the real chart builder with research frames and no active prices.
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    tree = ast.parse(Path('app.py').read_text(encoding='utf-8'))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in {'configure_price_volume_hover', 'make_price_chart'}]
    ns = dict(pd=pd, go=go, make_subplots=make_subplots, prices=pd.DataFrame(), weekly_by_symbol={})
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'app.py', 'exec'), ns)
    _, preview, _ = load_research()
    from stage_engine import weekly_bars
    daily = preview[preview.symbol.eq('512800')]
    weeks = {'512800': weekly_bars(daily, as_of_date='2026-11-02', calendar_name='XSHG', min_bars=1)}
    for weekly in (False, True):
        fig = ns['make_price_chart']('512800', daily_data=preview, weekly_data=weeks,
                                     period_is_weekly=weekly, chart_period='주봉' if weekly else '일봉')
        assert len(fig.data[0].x) == (len(weeks['512800']) if weekly else 60)
        assert all(t.xaxis == 'x2' for t in fig.data)
        assert any(t.type == 'bar' for t in fig.data)
        assert any(t.name == '캔들 정보' for t in fig.data)
        assert pd.Timestamp(fig.layout.xaxis2.range[0]) == pd.Timestamp(fig.data[0].x[0])
    assert len(chart_case('daily').data[0].x) == 220


def test_real_widgets_research_pages_period_click_and_existing_areas(monkeypatch):
    from streamlit.testing.v1 import AppTest
    def reject_network(*args, **kwargs):
        raise AssertionError('unexpected network')
    monkeypatch.setattr('requests.sessions.Session.request', reject_network)
    app = AppTest.from_file(str(Path('app.py').resolve()), default_timeout=60).run()
    assert not app.exception
    app.radio(key='active_analysis_area').set_value('sectors').run()
    app.radio(key='china_sector_source').set_value('중국 본토 SSE · 연구·관찰 12종').run()
    assert not app.exception
    assert len([b for b in app.button if str(b.key).startswith('china_research_pick_')]) == 12
    app.radio(key='china_research_period_512800').set_value('일봉').run()
    app.radio(key='china_research_view').set_value('3×3 차트').run()
    assert len([r for r in app.radio if str(r.key).startswith('china_research_period_')]) == 9
    app.button(key='china_research_grid_next').click().run()
    assert app.session_state['china_research_grid_page'] == 1
    assert len([r for r in app.radio if str(r.key).startswith('china_research_period_')]) == 3
    assert any('공식 가격 불일치' in e.value for e in app.error)
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    app.radio(key='active_analysis_area').set_value('sectors').run()
    assert app.radio(key='china_sector_source').value == '중국 본토 SSE · 연구·관찰 12종'
    assert app.radio(key='china_research_view').value == '3×3 차트'
    assert app.session_state['china_research_grid_page'] == 1
    assert len([r for r in app.radio if str(r.key).startswith('china_research_period_')]) == 3
    app.button(key='china_research_grid_515220_open').click().run()
    assert app.session_state['china_research_selected'] == '515220'
    assert app.radio(key='china_research_view').value == '차트 고정 목록'
    app.button(key='china_research_pick_512400').click().run()
    assert any('차트 및 Stage 계산 차단' in e.value for e in app.error)
    app.button(key='china_research_pick_512800').click().run()
    assert app.radio(key='china_research_period_512800').value == '일봉'
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    app.radio(key='active_analysis_area').set_value('sectors').run()
    assert app.radio(key='china_research_view').value == '차트 고정 목록'
    assert app.session_state['china_research_selected'] == '512800'
    assert app.radio(key='china_research_period_512800').value == '일봉'
    app.radio(key='china_sector_source').set_value('기존 업종 · 미국 상장 중국 프록시 포함').run()
    for area in ('markets_commodities', 'stocks', 'stage2', 'sectors'):
        app.radio(key='active_analysis_area').set_value(area).run()
        assert not app.exception, [e.value for e in app.exception]
