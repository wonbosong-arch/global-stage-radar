"""One-off read-only SSE dayk acquisition with explicit field order."""
import csv
import hashlib
import json
import ssl
import concurrent.futures
from datetime import datetime, timezone
from urllib.parse import urlencode
import requests
from collect_official_documents import HERE, ROOT

def acquire_market(symbol):
    url = 'https://yunhq.sse.com.cn:32042/v1/sh1/dayk/' + symbol + '?' + urlencode(dict(
        begin=-110, end=-1, period='day', select='date,open,high,low,close,volume,amount'))
    record = dict(symbol=symbol, requested_url=url, retrieved_at_utc=datetime.now(timezone.utc).isoformat())
    try:
        r = requests.get(url, verify=str(HERE/'market_ca.pem'), timeout=30,
                         headers={'Referer':'https://etf.sse.com.cn/', 'User-Agent':'Mozilla/5.0'})
        file = HERE/'sources'/f'{symbol}_sse_daily.json'
        file.write_bytes(r.content)
        record.update(http_status=r.status_code, sha256=hashlib.sha256(r.content).hexdigest(),
                      local_path='sources/'+file.name, bytes=len(r.content))
    except Exception as e:
        record['error'] = str(e)
    return record

if __name__ == '__main__':
    ca = HERE/'market_ca.pem'
    ca.write_text(''.join(ssl.DER_cert_to_PEM_cert(c) for store in ['ROOT','CA']
                         for c,e,t in ssl.enum_certificates(store) if e=='x509_asn'),encoding='ascii')
    selected = list(csv.DictReader((ROOT/'research/china_sector_representative_12_selection.csv').open(encoding='utf-8-sig')))
    symbols = [r['symbol'] for r in selected] + ['512700','512760']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(acquire_market,symbols))
    (HERE/'market_manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
    ca.unlink()
    print('Official market responses:',len(records))
