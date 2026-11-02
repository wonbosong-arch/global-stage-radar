"""Rebuild research-only tables from retained official sources and fixed git HEAD inputs."""
import csv
import hashlib
import io
import itertools
import json
import re
import subprocess
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import pdfplumber
from collect_official_documents import HERE, ROOT

D = Decimal

def read_csv(path):
    return list(csv.DictReader(path.open(encoding='utf-8-sig')))

def write_csv(name, rows):
    if not rows:
        raise ValueError(f'No rows: {name}')
    with (HERE/name).open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def fixed_input(path):
    return subprocess.check_output(['git','show',f'fda15a0:{path}'],cwd=ROOT)

def pdf_pages(path):
    cached=path.with_name(path.stem+'_layout.txt')
    if cached.exists():
        return re.split(r'--- PAGE \d+ ---\n',cached.read_text(encoding='utf8'))[1:]
    with pdfplumber.open(path) as pdf:
        return [p.extract_text() or '' for p in pdf.pages]

def supplement_wrapped_rows(path,rows):
    """Recover line-wrapped numeric cells from actual PDF table boundaries."""
    if path.stem not in ['512880_holdings_20260930','515220_holdings_20260930']:
        return rows
    pages=[12,13] if path.stem.startswith('512880') else [10,11]
    with pdfplumber.open(path) as pdf:
        for page in pages:
            for table in pdf.pages[page-1].extract_tables():
                for cells in table:
                    if len(cells)!=6 or not re.fullmatch(r'\d+',cells[0] or '') or not re.fullmatch(r'\d{6}',cells[1] or ''):
                        continue
                    if any(r['security_code']==cells[1] for r in rows):
                        continue
                    item=dict(rows[0])
                    item.update(security_code=cells[1],security_name=cells[2].replace('\n',''),
                                quantity_shares=re.sub(r'[\s,]','',cells[3]),
                                market_value_cny=re.sub(r'[\s,]','',cells[4]),
                                weight_pct_nav=cells[5].strip(),source_page=page)
                    rows.append(item)
    return rows

def parse_holdings(pages, symbol, asof):
    """Restrict to the holdings section, including positive active/IPO positions.

    Quarterly reports disclose top ten only. Never renormalize missing holdings.
    Retain rounded %NAV as published, including 0.00 weights.
    """
    text='\n'.join(f'\n@@PAGE {i+1}@@\n{t}' for i,t in enumerate(pages))
    if symbol not in text:
        raise ValueError(f'Fund identity absent: {symbol}')
    year,month,day=asof.split('-')
    date_zh=f'{year}年{int(month)}月{int(day)}日'
    if date_zh not in re.sub(r'\s','',text) and asof not in text:
        raise ValueError(f'Holdings date absent: {asof}')
    if asof=='2026-06-30':
        starts=list(re.finditer(r'(?m)^\s*7\.3\s*期末',text))
        ends_pattern=r'(?m)^\s*7\.4\s*报告'
    else:
        starts=list(re.finditer(r'(?m)^\s*5\.3\s*(?:报告)?期末',text))
        ends_pattern=r'(?m)^\s*5\.4\s*报告'
    if not starts:
        raise ValueError(f'Holdings heading absent: {symbol} {asof}')
    start=starts[-1].start()
    end=re.search(ends_pattern,text[start:])
    if not end:
        raise ValueError(f'Holdings ending absent: {symbol} {asof}')
    prefix=text[:start]
    page=int(re.findall(r'@@PAGE (\d+)@@',prefix)[-1])
    section=text[start:start+end.start()]
    pattern=re.compile(r'^\s*(\d+)\s+(\d{6})\s+(.+?)\s+([\d,]+(?:\.\d+)?)\s+([\d,]+\.\d{2})\s+(\d+\.\d{2})\s*$')
    rows=[]
    for line in section.splitlines():
        m=re.search(r'@@PAGE (\d+)@@',line)
        if m:
            page=int(m.group(1))
        match=pattern.match(line)
        if match:
            rank,code,name,quantity,value,weight=match.groups()
            rows.append(dict(symbol=symbol,as_of=asof,security_code=code,
                             security_name=name,quantity_shares=quantity.replace(',',''),
                             market_value_cny=value.replace(',',''),weight_pct_nav=weight,
                             source_page=page,disclosure_scope='all_disclosed_equities' if asof.endswith('06-30') else 'top10_index_and_reported_active_equities',
                             weight_precision_pct='0.01'))
    if not rows:
        raise ValueError(f'No holdings: {symbol} {asof}')
    return rows

def weighted_overlap(a,b):
    if not a or not b:
        raise ValueError('Missing holdings is not zero overlap')
    if {r['as_of'] for r in a} != {r['as_of'] for r in b}:
        raise ValueError('Mixed holdings dates')
    x,y=defaultdict(D),defaultdict(D)
    for rows,target in [(a,x),(b,y)]:
        for r in rows:
            target[r['security_code']]+=D(r['weight_pct_nav'])
    common=x.keys() & y.keys()
    return sum((min(x[k],y[k]) for k in common),D(0)),sorted(common)

def validate_market(payload,symbol):
    if payload.get('code')!=symbol:
        raise ValueError('Wrong market symbol')
    rows=payload.get('kline',[])
    if not rows or any(len(r)!=7 for r in rows):
        raise ValueError('Missing market fields')
    if len({r[0] for r in rows})!=len(rows):
        raise ValueError('Duplicate market dates')
    return {f'{r[0]//10000:04d}-{r[0]//100%100:02d}-{r[0]%100:02d}':r for r in rows}

def main():
    selected=read_csv(ROOT/'research/china_sector_representative_12_selection.csv')
    registry=read_csv(ROOT/'research/china_mainland_30_etf_verification_register.csv')
    methods=read_csv(ROOT/'research/china_index_official_methodology_evidence.csv')
    manifests=[]
    for name in ['acquisition_manifest.json','supplemental_manifest.json','fund_report_manifest.json','market_manifest.json']:
        manifests.extend(json.loads((HERE/name).read_text(encoding='utf8')))
    # Prefer the final successful response for a retained file, since hints can share a filename.
    bypath={r['local_path']:r for r in manifests if 'local_path' in r}
    # Retained catalog, not a claim that every historical attempt still has its own body.
    for path,record in bypath.items():
        if hashlib.sha256((HERE/path).read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError(f'Source hash mismatch: {path}')
    (HERE/'retained_source_catalog.json').write_text(json.dumps(list(bypath.values()),ensure_ascii=False,indent=2),encoding='utf8')
    holding_rows=[]
    summaries=[]
    for asof in ['2026-06-30','2026-09-30']:
        for s in selected:
            symbol=s['symbol']
            stem=f'{symbol}_holdings_{asof.replace("-","")}'
            path=HERE/'sources'/f'{stem}.pdf'
            pages=pdf_pages(path)
            (HERE/'sources'/f'{stem}_layout.txt').write_text('\n'.join(f'--- PAGE {i+1} ---\n{t}' for i,t in enumerate(pages)),encoding='utf8')
            rows=supplement_wrapped_rows(path,parse_holdings(pages,symbol,asof))
            source=bypath['sources/'+path.name]
            for row in rows:
                row.update(source_url=source['requested_url'],source_sha256=source['sha256'])
            holding_rows.extend(rows)
            stock_totals=re.findall(r'(?m)^\s*(?:其中[：:]\s*)?股票投资\s+([\d,]+\.\d{2})','\n'.join(pages))
            stock_total=D(stock_totals[-1].replace(',','')) if stock_totals else None
            sum_value=sum(D(r['market_value_cny']) for r in rows)
            gap=sum_value-stock_total if stock_total is not None and asof.endswith('06-30') else None
            summaries.append(dict(symbol=symbol,as_of=asof,disclosed_rows=len(rows),
                                  disclosed_weight_pct_nav=str(sum(D(r['weight_pct_nav']) for r in rows)),
                                  disclosed_market_value_cny=str(sum_value),reported_stock_total_cny=str(stock_total) if stock_total is not None else '',
                                  equity_table_minus_reported_total_cny=str(gap) if gap is not None else '',
                                  total_reconciliation_status=('matched' if gap==0 else 'unverified_source_total_discrepancy') if gap is not None else 'not_applicable_partial_disclosure',
                                  scope=rows[0]['disclosure_scope'],source_url=source['requested_url'],source_sha256=source['sha256']))
    write_csv('official_etf_holdings.csv',holding_rows)
    write_csv('holdings_coverage.csv',summaries)
    overlap=[]
    for asof in ['2026-06-30','2026-09-30']:
        for a,b in itertools.combinations([r['symbol'] for r in selected],2):
            ar=[r for r in holding_rows if r['symbol']==a and r['as_of']==asof]
            br=[r for r in holding_rows if r['symbol']==b and r['as_of']==asof]
            value,common=weighted_overlap(ar,br)
            overlap.append(dict(symbol_a=a,symbol_b=b,as_of=asof,shared_security_count=len(common),
                                overlap_pct_nav=str(value),shared_security_codes=';'.join(common),
                                measure='sum_min_disclosed_equity_weights_pct_NAV',
                                verification_level='disclosed_full_equity_table_rounded_aggregate_reconciliation_pending' if asof.endswith('06-30') else 'partial_top10_and_active_lower_bound_rounded',
                                is_full_current_portfolio_overlap='false',
                                normalization='none',rounding_note='published_0.01_pct_NAV_per_line;zero_does_not_prove_no_overlap'))
    write_csv('official_etf_overlap_pairs.csv',overlap)
    # Version evidence is document-specific; no filename dates treated as effective dates.
    evidence=[]
    for method in methods:
        code=method['index_code']
        candidates=[]
        for local,rec in bypath.items():
            if local.startswith(f'sources/{code}_methodology') and local.endswith('.pdf'):
                pages=pdf_pages(HERE/local)
                text='\n'.join(pages)
                date=re.search(r'(20\d{2})\s*年\s*(\d{1,2})\s*月',pages[0])
                version=re.search(r'版本号\s*(V[\d.]+)',pages[0])
                candidates.append((date.group(1)+'-'+date.group(2).zfill(2) if date else '',version.group(1) if version else '',local,rec,pages,text))
        candidates.sort(key=lambda r:(r[0],tuple(int(n) for n in r[1][1:].split('.')) if r[1] else (0,)),reverse=True)
        chosen=candidates[0] if candidates else None
        contains=chosen and code in re.sub(r'\s','',chosen[5])
        pages_with_code=[str(i+1) for i,t in enumerate(chosen[4]) if code in re.sub(r'\s','',t)] if chosen else []
        for etf in registry:
            if etf['tracked_index_code']!=code:
                continue
            evidence.append(dict(symbol=etf['symbol'],index_code=code,index_name_zh=method['index_name_zh'],
                                 document_level='official_pdf_body_version_and_code_confirmed' if contains else 'official_factsheet_only_methodology_unverified',
                                 document_month=chosen[0] if chosen else '',document_version=chosen[1] if chosen else '',
                                 methodology_url=chosen[3]['requested_url'] if chosen else '',
                                 methodology_sha256=chosen[3]['sha256'] if chosen else '',
                                 source_path=chosen[2] if chosen else '',index_code_pages=';'.join(pages_with_code),
                                 effective_date='',effective_date_status='unverified_no_dated_change_notice_retained',
                                 latest_as_of_20261102='unverified',
                                 latest_limit='current_detail_attachment_and_complete_revision_notice_history_not_verified',
                                 retained_candidate_versions=';'.join(f'{r[0]} {r[1]}' for r in candidates),
                                 factsheet_url=method['factsheet_evidence_url'],activation_status='inactive_research_only'))
    write_csv('methodology_versions_30.csv',evidence)
    pricebytes=fixed_input('data/china_candidate_prices.csv')
    prices=list(csv.DictReader(io.StringIO(pricebytes.decode('utf-8-sig'))))
    market=[]
    liquidity=[]
    for symbol in [r['symbol'] for r in selected]+['512700','512760']:
        old=sorted([r for r in prices if r['symbol']==symbol],key=lambda r:r['date'])[-60:]
        path=HERE/'sources'/f'{symbol}_sse_daily.json'
        official=validate_market(json.loads(path.read_text(encoding='utf8')),symbol)
        matched=0
        volume_matched=0
        price_matched=0
        amounts=[]
        vols=[]
        for r in old:
            day=official.get(r['date'])
            match=bool(day and D(str(day[5]))==D(r['volume']))
            price_match=bool(day and all(D(str(day[i]))==D(r[k]) for i,k in enumerate(['open','high','low','close'],1)))
            valid=bool(day and day[5]>0 and day[6]>0 and D(str(day[3]))<=D(str(day[6]))/D(str(day[5]))<=D(str(day[2])))
            if match and price_match and valid:
                matched+=1
            volume_matched+=int(match)
            price_matched+=int(price_match)
            if day and valid:
                amounts.append(D(str(day[6])))
                vols.append(D(str(day[5])))
            market.append(dict(symbol=symbol,date=r['date'],baseline_open=r['open'],baseline_high=r['high'],baseline_low=r['low'],baseline_close=r['close'],
                               official_open=str(day[1]) if day else '',official_high=str(day[2]) if day else '',official_low=str(day[3]) if day else '',official_close=str(day[4]) if day else '',
                               baseline_volume=r['volume'],
                               official_volume_shares=str(day[5]) if day else '',official_turnover_cny=str(day[6]) if day else '',
                               volume_matches=str(match).lower(),ohlc_matches=str(price_match).lower(),
                               amount_over_volume_within_daily_price_range=str(valid).lower(),
                               source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        liquidity.append(dict(symbol=symbol,window_start=old[0]['date'],window_end=old[-1]['date'],observations=60,
                              matched_official_days=matched,volume_matched_days=volume_matched,ohlc_matched_days=price_matched,
                              baseline_avg_volume=str(sum(D(r['volume']) for r in old)/60),
                              official_avg_volume_shares=str(sum(vols)/60) if len(vols)==60 else '',
                              official_avg_turnover_cny=str(sum(amounts)/60) if len(amounts)==60 else '',
                              official_min_daily_turnover_cny=str(min(amounts)) if len(amounts)==60 else '',
                              volume_unit_status='shares_confirmed_all_60_days' if volume_matched==60 else 'unverified_or_mismatch',
                              price_basis_status='ohlc_all_60_match' if price_matched==60 else 'ohlc_difference_cause_unverified',
                              spread_status='unverified_no_historical_quotes',market_depth_status='unverified',
                              liquidity_superiority_status='not_established',
                              source_url=next(x['requested_url'] for x in manifests if x.get('local_path')=='sources/'+path.name)))
    write_csv('official_market_reconciliation.csv',market)
    write_csv('official_liquidity_60d.csv',liquidity)
    meta=dict(baseline_commit=subprocess.check_output(['git','rev-parse','fda15a0'],cwd=ROOT,text=True).strip(),
              baseline_price_sha256=hashlib.sha256(pricebytes).hexdigest(),
              methods_pdf_body_etfs=sum(r['document_level']=='official_pdf_body_version_and_code_confirmed' for r in evidence),
              latest_methods_confirmed=0,methodology_effective_dates_confirmed=0,
              holdings_rows=len(holding_rows),overlap_pairs=len(overlap),
              official_market_daily_comparisons=len(market),fully_matched_funds=sum(r['matched_official_days']==60 for r in liquidity),
              fully_volume_matched_funds=sum(r['volume_matched_days']==60 for r in liquidity))
    (HERE/'analysis_summary.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(meta,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
