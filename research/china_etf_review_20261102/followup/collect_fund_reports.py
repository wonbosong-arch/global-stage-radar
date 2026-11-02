"""One-off official SSE disclosure discovery; no collection schedule changes."""
import concurrent.futures
import csv
import json
import ssl
from urllib.parse import urlencode
from collect_official_documents import HERE, ROOT, acquire

def reports(symbol):
    import requests
    import hashlib
    from datetime import datetime, timezone
    params = dict(isPagination='true', sqlId='COMMON_PL_JJXX_JJGG_NEW_L',
                  SECURITY_CODE=symbol, START_DATE='2026-08-01', END_DATE='2026-11-02',
                  **{'pageHelp.pageSize': 100, 'pageHelp.pageNo': 1}, type='inParams', DATE_DESC=1)
    url = 'https://query.sse.com.cn/commonQuery.do?' + urlencode(params)
    result = []
    try:
        r = requests.get(url, verify=str(HERE / 'windows_ca.pem'), timeout=35,
                         headers={'Referer': 'https://www.sse.com.cn/', 'User-Agent': 'Mozilla/5.0'})
        target = HERE / 'sources' / f'{symbol}_disclosure_index.json'
        target.write_bytes(r.content)
        result.append(dict(key=symbol, kind='disclosure_index', requested_url=url,
                           http_status=r.status_code, sha256=hashlib.sha256(r.content).hexdigest(),
                           local_path='sources/'+target.name, retrieved_at_utc=datetime.now(timezone.utc).isoformat()))
        for row in r.json().get('result', []):
            if '提示性公告' not in row['TITLE'] and '2026' in row['TITLE'] and ('中期报告' in row['TITLE'] or ('季度报告' in row['TITLE'] and ('3' in row['TITLE'] or '三' in row['TITLE']))):
                kind = 'holdings_20260630' if '中期报告' in row['TITLE'] else 'holdings_20260930'
                rec = acquire((symbol, kind, 'https://www.sse.com.cn' + row['URL']))
                rec.update(disclosure_title=row['TITLE'], disclosure_date=row['SSEDATE'])
                result.append(rec)
    except Exception as e:
        result.append(dict(key=symbol, kind='disclosure_failure', error=str(e), requested_url=url))
    return result

if __name__ == '__main__':
    ca = HERE / 'windows_ca.pem'
    ca.write_text(''.join(ssl.DER_cert_to_PEM_cert(c) for store in ['ROOT', 'CA']
                         for c, e, t in ssl.enum_certificates(store) if e == 'x509_asn'), encoding='ascii')
    selected = list(csv.DictReader((ROOT / 'research/china_sector_representative_12_selection.csv').open(encoding='utf-8-sig')))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = [r for group in pool.map(reports, [x['symbol'] for x in selected]) for r in group]
    (HERE / 'fund_report_manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf8')
    ca.unlink(missing_ok=True)
    print(json.dumps({'records': len(records), 'pdfs': sum(x.get('acquisition_status','').startswith('pdf_body') for x in records)}))
