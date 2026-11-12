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

def test_research_ui_filters_period_page_and_selection_are_independent(tmp_path, monkeypatch):
    import ast
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    root=Path(__file__).resolve().parents[1]
    tree=ast.parse((root/'app.py').read_text(encoding='utf-8'))
    names={'load_us_research','render_pending_candidate_chart_explorer','configure_price_volume_hover','_render_grid_pager','_change_grid_page','_select_pending_research_symbol','_remember_pending_research_controls'}
    functions='\n\n'.join(ast.unparse(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names)
    data=tmp_path/'data';data.mkdir()
    symbols=['TEST'+str(i).zfill(3) for i in range(120)]
    report=pd.DataFrame([dict(symbol=s,name=s,proposed_sector='Materials' if i<60 else 'Financials',market_benchmark='SPY',suggested_sector_benchmark='XLB' if i<60 else 'XLF',provisional_stage_label='Stage 2 후보',research_eligible=True,native_sector='Basic Materials',native_industry='Metal Mining',weekly_bars=40,activation_status='pending_review_not_activated') for i,s in enumerate(symbols)])
    report.to_csv(data/'provisional_candidate_stage_report.csv',index=False)
    prices=pd.DataFrame([dict(symbol=s,date=d,open=100,high=102,low=99,close=101,volume=1000) for s in symbols for d in pd.bdate_range(end='2026-10-23',periods=200)])
    prices.to_csv(data/'candidate_daily_prices.csv',index=False)
    pd.DataFrame(dict(symbol=symbols,exchange='NYS')).to_csv(data/'stock_universe_candidates.csv',index=False)
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
make_price_chart=lambda *a, **k:None
get_secret=lambda key: None
remember_dashboard_state=lambda:None
read_prices=lambda p:pd.read_csv(p,parse_dates=['date'])
cached_us_research_classification=lambda:(b'synthetic',{'downloaded_on_utc':'2026-10-23'})
def cached_us_research_inputs(*args):
    return pd.read_csv('data/provisional_candidate_stage_report.csv'),read_prices('data/candidate_daily_prices.csv')
'''+functions+'''
st.session_state.setdefault('stocks_grid_page',3)
st.session_state.setdefault('global_asset_view_mode','3×3 차트')
if st.radio('Test area',['research','other'],key='test_area')=='research':
    render_pending_candidate_chart_explorer()
'''
    monkeypatch.chdir(tmp_path)
    app=AppTest.from_string(wrapper,default_timeout=30).run()
    assert not app.exception
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
