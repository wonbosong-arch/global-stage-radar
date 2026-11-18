import copy, hashlib, io
from datetime import datetime, timezone
import pandas as pd
import unittest
from test_us_sector_mapping_batch import fixture
from us_research_dashboard import build_research, size_screen

NOW = datetime(2026, 10, 24, 6, tzinfo=timezone.utc)

def inputs():
    registry, _, universe, master, prices = fixture()
    master['market_cap_usd'] = '1000000000'
    universe['exchange'] = 'AMS'
    old = pd.DataFrame(dict(symbol=registry.symbol, proposed_sector='', market_benchmark='SPY', suggested_sector_benchmark=''))
    candidate = prices[prices.symbol.isin(registry.symbol)].copy()
    active = prices[~prices.symbol.isin(registry.symbol)].copy()
    native = pd.DataFrame([dict(Symbol=s, Name=s+' Corporation Common Stock', Sector='Basic Materials', Industry='Metal Mining', **{'Market Cap':'1'}) for s in registry.symbol])
    return registry, master, universe, candidate, active, old, native

def run(parts, native=True):
    raw = parts[-1].to_csv(index=False).encode()
    receipt = dict(version=1, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), downloaded_on_utc='2026-10-23', approved_at_utc='2026-10-24T00:00:00+00:00')
    return build_research(*parts[:-1], raw=raw if native else None, receipt=receipt if native else None, as_of='2026-10-24', now=NOW)

def test_existing_saved_prices_gain_sector_stage_analysis_without_collection_or_mutation(monkeypatch):
    def reject_provider(*args, **kwargs):
        raise AssertionError('provider call')
    monkeypatch.setattr('requests.get', reject_provider)
    p=inputs(); before=copy.deepcopy(p)
    old, prior_prices=run(p, False); report, chart=run(p)
    assert len(old)==len(report)==2 and not old.research_eligible.any()
    assert report.research_eligible.all()
    assert report.suggested_sector_benchmark.eq('XLB').all()
    assert report.provisional_stage_label.notna().all()
    assert report.activation_status.eq('pending_review_not_activated').all()
    pd.testing.assert_frame_equal(prior_prices,chart)
    for a,b in zip(p,before): pd.testing.assert_frame_equal(a,b)
    # Nasdaq $1 capitalization cannot affect the KIS $1B threshold.
    assert report.market_cap_usd.eq(1e9).all()

def test_new_etf_is_review_only_and_preserves_existing_stage_and_price_inputs():
    p = list(inputs())
    p[-1].loc[0, "Sector"] = "Technology"
    p[-1].loc[0, "Industry"] = "Computer Software: Prepackaged Software"
    before = copy.deepcopy(p)
    report, chart = run(p)
    candidate = report.loc[report.symbol.eq("TESTA")].iloc[0]
    assert candidate.preferred_sector_etf_review == "IGV"
    assert candidate.preferred_etf_official_source.startswith("https://www.ishares.com/")
    assert "미검증" in candidate.preferred_etf_review_status
    # The missing KIS price/universe registration does not become an
    # operational or saved Stage benchmark.
    assert candidate.suggested_sector_benchmark == ""
    assert not candidate.research_eligible
    assert candidate.activation_status == "pending_review_not_activated"
    assert "IGV" not in set(chart.symbol)
    for frame, original in zip(p, before):
        pd.testing.assert_frame_equal(frame, original)
    without_source, _ = run(p, native=False)
    assert without_source.set_index("symbol").loc["TESTA", "preferred_sector_etf_review"] == ""


def test_existing_saved_etf_remains_the_stage_benchmark_when_better_candidate_exists():
    p = list(inputs())
    p[5].loc[0, ["proposed_sector", "suggested_sector_benchmark"]] = ["Materials", "XLB"]
    p[-1].loc[0, "Sector"] = "Technology"
    p[-1].loc[0, "Industry"] = "Computer Software: Prepackaged Software"
    old, _ = run(p, native=False)
    new, _ = run(p, native=True)
    before = old.set_index("symbol").loc["TESTA"]
    after = new.set_index("symbol").loc["TESTA"]
    assert after.preferred_sector_etf_review == "IGV"
    assert after.suggested_sector_benchmark == before.suggested_sector_benchmark == "XLB"
    assert after.provisional_stage_label == before.provisional_stage_label
    assert after.research_eligible == before.research_eligible
    assert after.sector_rs_26w_pct == before.sector_rs_26w_pct


def test_kis_cap_priority_and_saved_yahoo_only_when_kis_missing():
    row=dict(discovery_source='KIS market-cap ranking',discovery_market_cap_usd='2000000000', market_cap_source_url='https://finance.yahoo.com/quote/TEST/',market_cap_usd_b_secondary='100')
    assert size_screen(row,pd.DataFrame([dict(market_cap_usd='999999999')]))==(999999999.,'KIS master')
    assert size_screen(row,pd.DataFrame())==(2e9,'KIS ranking')
    row['discovery_market_cap_usd']=''
    assert size_screen(row,pd.DataFrame())==(1e11,'Yahoo saved supplement')

def test_bad_inputs_hold_only_affected_candidate():
    for fault in ['short','invalid','duplicate','stale','anomaly','type','low_cap','benchmark','source_name','source_duplicate']:
        p=inputs(); r,m,u,c,a,o,n=p
        if fault=='short': c.drop(c[c.symbol.eq('TESTA')].index[:-40],inplace=True)
        if fault=='invalid': c.loc[c.index[0],'high']=1
        if fault=='duplicate':
            c.loc[len(c)]=c.iloc[0]; c.loc[len(c)-1,'close']=100
        if fault=='stale': c.drop(c[c.symbol.eq('TESTA') & c.date.gt('2026-10-01')].index,inplace=True)
        if fault=='anomaly':
            k=c[c.symbol.eq('TESTA')].index[-1];c.loc[k,['open','high','low','close']]=[1000,1002,999,1001]
        if fault=='type': m.loc[0,'master_security_type']='3'
        if fault=='low_cap': m.loc[0,'market_cap_usd']='999999999'
        if fault=='benchmark': u.loc[u.symbol.eq('XLB'),'provider']='Yahoo'
        if fault=='source_name': n.loc[0,'Name']='Unrelated Issuer'
        if fault=='source_duplicate': n.loc[len(n)]=n.iloc[0]
        report,charts=run(p); rr=report.set_index('symbol')
        assert not rr.loc['TESTA','research_eligible']
        assert rr.loc['TESTA','provisional_stage_label']=='연구 판정 보류'
        if fault!='benchmark': assert rr.loc['TESTB','research_eligible']
        if fault in {'invalid','duplicate'}: assert 'TESTA' not in set(charts.symbol)

def test_saved_mapping_and_other_market_are_preserved_with_native_conflict():
    p=inputs();p[5].loc[0,['proposed_sector','suggested_sector_benchmark']]=['Materials','XLB']
    p[6].loc[0,['Sector','Industry']]=['Finance','Major Banks']
    report,_=run(p)
    assert report.iloc[0].suggested_sector_benchmark=='XLB'
    assert report.iloc[0].research_eligible
    p[0].loc[len(p[0])]={**p[0].iloc[0].to_dict(),'symbol':'KRTEST','exchange':'KRX'}
    assert set(run(p)[0].symbol)=={'TESTA','TESTB'}

def test_receipt_mismatch_fails_closed():
    p=inputs()
    with unittest.TestCase().assertRaises(ValueError):
        build_research(*p[:-1],raw=b'changed',receipt={},as_of='2026-10-24',now=NOW)


def test_exact_duplicate_records_coalesce_without_losing_candidates_or_prices():
    p = inputs()
    expected, prices = run(p)
    p = list(p)
    for index in (0, 5):
        p[index] = pd.concat([p[index], p[index].iloc[[0]]], ignore_index=True)
    before = copy.deepcopy(p)
    report, charts = run(p)
    pd.testing.assert_frame_equal(expected, report)
    pd.testing.assert_frame_equal(prices, charts)
    for a, b in zip(p, before):
        pd.testing.assert_frame_equal(a, b)


def test_registry_and_saved_report_conflicts_hold_only_affected_symbol(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('provider request')
    monkeypatch.setattr('requests.get', deny)
    baseline, baseline_prices = run(inputs())
    # All differences are real conflicts, even within the same venue. Symbol
    # prices cannot resolve a venue/type/issuer conflict by selecting a first row.
    for field, value in [('exchange', 'NAS'), ('exchange', 'KRX'),
                         ('name', 'Other Issuer'), ('discovery_security_type', 'etp')]:
        for native in (False, True):
            p = list(inputs())
            other = p[0].iloc[[0]].copy()
            other[field] = value
            p[0] = pd.concat([p[0], other], ignore_index=True)
            # Reproduce the second exception hidden behind the original guard:
            # a duplicate-symbol legacy report with differing saved mappings.
            other_report = p[5].iloc[[0]].copy()
            other_report['suggested_sector_benchmark'] = 'XLF'
            p[5] = pd.concat([p[5], other_report], ignore_index=True)
            before = copy.deepcopy(p)
            report, charts = run(p, native)
            held = report.set_index('symbol').loc['TESTA']
            assert not held.research_eligible
            assert held.exchange == held.suggested_sector_benchmark == ''
            assert 'candidate_identity_conflict' in held.review_note
            assert 'saved_report_identity_conflict' in held.review_note
            assert set(charts.symbol) == {'TESTB'}
            assert report.set_index('symbol').loc['TESTB', 'research_eligible'] == native
            if native:
                pd.testing.assert_frame_equal(
                    report[report.symbol.eq('TESTB')].reset_index(drop=True),
                    baseline[baseline.symbol.eq('TESTB')].reset_index(drop=True), check_dtype=False)
            pd.testing.assert_frame_equal(charts.reset_index(drop=True),
                baseline_prices[baseline_prices.symbol.eq('TESTB')].reset_index(drop=True))
            reverse = p.copy()
            reverse[0] = p[0].iloc[::-1]
            reverse[5] = p[5].iloc[::-1]
            reversed_report, reversed_prices = run(reverse, native)
            pd.testing.assert_frame_equal(report, reversed_report)
            pd.testing.assert_frame_equal(charts, reversed_prices)
            for a, b in zip(p, before):
                pd.testing.assert_frame_equal(a, b)


def test_legacy_report_collision_alone_is_local_and_all_held_is_supported():
    from us_research_dashboard import comparison_rows
    p = list(inputs())
    other = p[5].copy()
    other['suggested_sector_benchmark'] = 'XLF'
    p[5] = pd.concat([p[5], other.iloc[[0]]], ignore_index=True)
    report, charts = run(p)
    assert set(charts.symbol) == {'TESTB'}
    assert list(comparison_rows(report).symbol) == ['TESTB']
    p[5] = pd.concat([p[5], other.iloc[[1]]], ignore_index=True)
    report, charts = run(p)
    assert len(report) == 2 and not report.research_eligible.any()
    assert charts.empty and comparison_rows(report).empty

def test_research_ui_filters_period_page_and_selection_are_independent(tmp_path, monkeypatch):
    import ast
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    root=Path(__file__).resolve().parents[1]
    tree=ast.parse((root/'app.py').read_text(encoding='utf-8'))
    names={'load_us_research','render_pending_candidate_chart_explorer','configure_price_volume_hover','_render_grid_pager','_change_grid_page','_select_pending_research_symbol','_remember_pending_research_controls','analysis_download_button','raw_management_table'}
    functions='\n\n'.join(ast.unparse(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names)
    data=tmp_path/'data';data.mkdir()
    symbols=['TEST'+str(i).zfill(3) for i in range(120)]
    report=pd.DataFrame([dict(symbol=s,name=s,proposed_sector='Materials' if i<60 else 'Financials',market_benchmark='SPY',suggested_sector_benchmark='XLB' if i<60 else 'XLF',provisional_stage_label='Stage 2 후보',research_eligible=True,native_sector='Basic Materials',native_industry='Metal Mining',weekly_bars=40,activation_status='pending_review_not_activated') for i,s in enumerate(symbols)])
    report=pd.concat([report, report.iloc[[0,1]]], ignore_index=True)
    report.to_csv(data/'provisional_candidate_stage_report.csv',index=False)
    prices=pd.DataFrame([dict(symbol=s,date=d,open=100,high=102,low=99,close=101,volume=1000) for s in symbols for d in pd.bdate_range(end='2026-10-23',periods=200)])
    prices.to_csv(data/'candidate_daily_prices.csv',index=False)
    registry=pd.DataFrame(dict(symbol=symbols,exchange='NYS',activation_status='pending_review'))
    registry=pd.concat([registry,registry.iloc[[1]],pd.DataFrame([dict(symbol='TEST000',exchange='NAS',activation_status='pending_review')])],ignore_index=True)
    registry.to_csv(data/'stock_universe_candidates.csv',index=False)
    for n in ['unranked_us_stock_master.csv','monitoring_universe.csv','daily_prices.csv','yahoo_market_cap_supplement.csv']:(data/n).write_text('symbol\n')
    wrapper='''import os, requests
from hashlib import sha256
from functools import partial
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from stage_engine import weekly_bars
from market_data import filter_incomplete_daily_bars
from private_analysis_access import chart_config, protected_download, management_table
make_price_chart=lambda *a, **k:None
get_secret=lambda key: None
remember_dashboard_state=lambda:None
read_prices=lambda p:pd.read_csv(p,parse_dates=['date'])
cached_us_research_classification=lambda:(b'synthetic',{'downloaded_on_utc':'2026-10-23'})
def cached_us_research_inputs(*args):
    from us_research_dashboard import research_identities
    report=pd.read_csv('data/provisional_candidate_stage_report.csv')
    _,_,held=research_identities(pd.read_csv('data/stock_universe_candidates.csv'), report)
    prices=read_prices('data/candidate_daily_prices.csv')
    return report[~report.symbol.isin(held)].drop_duplicates(),prices[~prices.symbol.isin(held)]
'''+functions+'''
st.session_state.setdefault('stocks_grid_page',3)
st.session_state.setdefault('global_asset_view_mode','3×3 차트')
if st.radio('Test area',['research','other'],key='test_area')=='research':
    render_pending_candidate_chart_explorer()
'''
    monkeypatch.chdir(tmp_path)
    app=AppTest.from_string(wrapper,default_timeout=30).run()
    assert not app.exception
    assert all('TEST000' not in label for label in app.selectbox(key='pending_candidate_chart_symbol').options)
    assert any('신원 충돌 1종목' in c.value for c in app.caption)
    assert not any(b.key=='pending_candidate_research_pick_TEST000' for b in app.button)
    assert len([b for b in app.button if b.key=='pending_candidate_research_pick_TEST001']) == 1
    app.toggle(key='us_research_enabled').set_value(True).run()
    assert not app.exception
    selected=app.selectbox(key='pending_candidate_chart_symbol')
    selected.set_value('TEST055').run()
    app.radio(key='pending_candidate_chart_period').set_value('일봉').run()
    app.button(key='pending_candidate_table_grid_next').click().run()
    assert app.session_state['pending_candidate_table_page']==1
    app.button(key='pending_candidate_research_pick_TEST055').click().run()
    assert app.selectbox(key='pending_candidate_chart_symbol').value=='TEST055'
    assert app.radio(key='pending_candidate_chart_period').value=='일봉'
    app.selectbox(key='pending_candidate_chart_sector_filter').set_value('Materials').run()
    assert app.selectbox(key='pending_candidate_chart_symbol').value=='TEST055'
    app.selectbox(key='pending_candidate_chart_sector_filter').set_value('Financials').run()
    assert app.selectbox(key='pending_candidate_chart_symbol').value.startswith('TEST0')
    app.text_input(key='pending_candidate_chart_search').set_value('no such symbol').run()
    assert not app.exception
    app.text_input(key='pending_candidate_chart_search').set_value('').run()
    app.radio(key='pending_candidate_chart_market').set_value('전체 시장').run()
    assert not app.exception
    chosen=app.selectbox(key='pending_candidate_chart_symbol').value
    app.radio(key='test_area').set_value('other').run()
    app.radio(key='test_area').set_value('research').run()
    assert app.toggle(key='us_research_enabled').value
    assert app.selectbox(key='pending_candidate_chart_symbol').value==chosen
    assert app.radio(key='pending_candidate_chart_period').value=='일봉'
    assert app.session_state['stocks_grid_page']==3
    assert app.session_state['global_asset_view_mode']=='3×3 차트'
