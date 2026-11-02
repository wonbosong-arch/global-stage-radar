"""Offline regression checks of official-source evidence, never live website tests."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'research/china_etf_review_20261102/followup'
sys.path.insert(0,str(HERE))
from analyze_followup import D,parse_holdings,weighted_overlap,validate_market

def rows(name):
    return list(csv.DictReader((HERE/name).open(encoding='utf-8-sig')))

def test_methodology_inventory_and_no_unearned_latest_claim():
    data=rows('methodology_versions_30.csv')
    assert len(data)==len({r['symbol'] for r in data})==30
    assert sum(r['document_level']=='official_pdf_body_version_and_code_confirmed' for r in data)==24
    assert all(r['latest_as_of_20261102']=='unverified' and not r['effective_date'] for r in data)
    assert all(r['activation_status']=='inactive_research_only' for r in data)

@pytest.mark.parametrize('code,new,old',[('000949','2023-12 V1.4','2023-02 V1.3'),('930726','2023-12 V1.3','2021-09 V1.2')])
def test_generic_official_url_can_be_older_than_other_official_copy(code,new,old):
    r=next(r for r in rows('methodology_versions_30.csv') if r['index_code']==code)
    assert new in r['retained_candidate_versions'] and old in r['retained_candidate_versions']
    assert r['document_month']+' '+r['document_version']==new
    assert r['latest_as_of_20261102']=='unverified'

def test_retained_source_hashes():
    catalog=json.loads((HERE/'retained_source_catalog.json').read_text(encoding='utf8'))
    assert len(catalog)>100
    for r in catalog:
        assert hashlib.sha256((HERE/r['local_path']).read_bytes()).hexdigest()==r['sha256'],r['local_path']

def test_version_and_code_are_in_actual_retained_official_pdf_body():
    import re
    from pypdf import PdfReader
    for r in rows('methodology_versions_30.csv'):
        if not r['source_path']:
            continue
        pages=PdfReader(HERE/r['source_path']).pages
        text=''.join(re.sub(r'\s','',p.extract_text() or '') for p in pages)
        assert r['index_code'] in text
        assert r['document_version'] in text
        year,month=r['document_month'].split('-')
        assert f'{year}年{int(month)}月' in text

def test_holdings_all_twelve_have_both_dates():
    data=rows('holdings_coverage.csv')
    assert len(data)==24
    assert {r['as_of'] for r in data}=={'2026-06-30','2026-09-30'}
    assert all(int(r['disclosed_rows'])>=10 for r in data)
    assert all(D(r['disclosed_weight_pct_nav'])>D('30') for r in data)

def test_wrapped_numeric_cells_are_preserved():
    data=rows('official_etf_holdings.csv')
    r=next(r for r in data if r['symbol']=='512880' and r['as_of']=='2026-09-30' and r['security_code']=='600030')
    assert r['quantity_shares']=='324142491'
    assert r['market_value_cny']=='8382324817.26'
    assert r['weight_pct_nav']=='14.38'
    r=next(r for r in data if r['symbol']=='515220' and r['as_of']=='2026-09-30' and r['security_code']=='601088')
    assert r['market_value_cny']=='1036257988.64'

def test_aggregate_discrepancies_are_not_silently_verified():
    data=[r for r in rows('holdings_coverage.csv') if r['as_of']=='2026-06-30']
    assert sum(r['total_reconciliation_status']=='matched' for r in data)==1
    r=next(r for r in data if r['symbol']=='512600')
    assert r['equity_table_minus_reported_total_cny']=='-1333.60'
    assert r['total_reconciliation_status'].startswith('unverified')

@pytest.mark.parametrize('date,a,b,expected',[('2026-06-30','512600','515650','49.53'),('2026-06-30','512400','516160','11.56'),('2026-09-30','512600','515650','40.70')])
def test_observed_weighted_overlap(date,a,b,expected):
    data=rows('official_etf_holdings.csv')
    aa=[r for r in data if r['symbol']==a and r['as_of']==date]
    bb=[r for r in data if r['symbol']==b and r['as_of']==date]
    assert weighted_overlap(aa,bb)[0]==D(expected)

def test_overlap_dates_and_incomplete_disclosures_cannot_be_upgraded():
    data=rows('official_etf_overlap_pairs.csv')
    assert len(data)==132
    assert all(r['normalization']=='none' and r['is_full_current_portfolio_overlap']=='false' for r in data)
    assert all('lower_bound' in r['verification_level'] for r in data if r['as_of']=='2026-09-30')
    with pytest.raises(ValueError):
        weighted_overlap([],[])
    with pytest.raises(ValueError):
        weighted_overlap([{'as_of':'2026-06-30'}],[{'as_of':'2026-09-30'}])

def test_holdings_wrong_fund_or_date_rejected():
    with pytest.raises(ValueError,match='identity'):
        parse_holdings(['2026年6月30日 512800'],'512880','2026-06-30')
    with pytest.raises(ValueError,match='date'):
        parse_holdings(['2026年6月30日 512800'],'512800','2026-09-30')

def test_official_volume_all_840_days_exact_and_amounts_real():
    data=rows('official_market_reconciliation.csv')
    assert len(data)==840
    assert len({(r['symbol'],r['date']) for r in data})==840
    assert all(r['volume_matches']=='true' and r['amount_over_volume_within_daily_price_range']=='true' for r in data)
    assert max(r['date'] for r in data)=='2026-10-27'
    assert all(D(r['official_turnover_cny'])>0 for r in data)

def test_price_differences_do_not_erase_confirmed_volume_units():
    data=rows('official_liquidity_60d.csv')
    assert len(data)==14
    assert all(r['volume_matched_days']=='60' and r['volume_unit_status']=='shares_confirmed_all_60_days' for r in data)
    assert {r['symbol'] for r in data if r['ohlc_matched_days']!='60'}=={'512400','512700'}
    assert next(r for r in data if r['symbol']=='512400')['ohlc_matched_days']=='29'
    assert all(r['spread_status'].startswith('unverified') and r['liquidity_superiority_status']=='not_established' for r in data)

@pytest.mark.parametrize('payload',[{}, {'code':'wrong','kline':[[20261027,1,1,1,1,100,100]]}, {'code':'512800','kline':[]}, {'code':'512800','kline':[[20261027,1,1,1,1,100]]}])
def test_empty_stale_or_malformed_market_responses_are_not_zero_data(payload):
    with pytest.raises(ValueError):
        validate_market(payload,'512800')
