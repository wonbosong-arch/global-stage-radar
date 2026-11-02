"""Manual research acquisition only; never imported by scheduled collectors.

Preserves response hashes, URLs and page text. HTTP success is not verification.
Uses Windows trusted CAs without disabling TLS verification.
"""
import concurrent.futures
import csv
import hashlib
import io
import json
from pathlib import Path
import ssl
from datetime import datetime, timezone

import requests
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = 'https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/'


def acquire(item):
    key, kind, url = item
    record = dict(key=key, kind=kind, requested_url=url,
                  retrieved_at_utc=datetime.now(timezone.utc).isoformat())
    try:
        response = requests.get(url, timeout=35, verify=str(HERE / 'windows_ca.pem'),
                                headers={'User-Agent': 'Mozilla/5.0'})
        record.update(http_status=response.status_code, final_url=response.url,
                      content_type=response.headers.get('Content-Type', ''),
                      last_modified=response.headers.get('Last-Modified', ''),
                      sha256=hashlib.sha256(response.content).hexdigest(), bytes=len(response.content))
        if response.status_code == 200 and response.content.startswith(b'%PDF'):
            stem = f'{key}_{kind}'
            (HERE / 'sources' / f'{stem}.pdf').write_bytes(response.content)
            reader = PdfReader(io.BytesIO(response.content))
            pages = [page.extract_text() or '' for page in reader.pages]
            (HERE / 'sources' / f'{stem}.txt').write_text(
                '\n'.join(f'--- PAGE {i+1} ---\n{text}' for i, text in enumerate(pages)), encoding='utf-8')
            record.update(acquisition_status='pdf_body_saved_not_yet_reviewed', pages=len(pages),
                          local_path=f'sources/{stem}.pdf')
        else:
            record['acquisition_status'] = 'unavailable_or_not_pdf'
    except Exception as exc:
        record.update(acquisition_status='access_failed', error=f'{type(exc).__name__}: {exc}')
    return record


def main():
    HERE.mkdir(exist_ok=True)
    (HERE / 'sources').mkdir(exist_ok=True)
    ca = HERE / 'windows_ca.pem'
    ca.write_text(''.join(ssl.DER_cert_to_PEM_cert(cert)
                         for store in ['ROOT', 'CA']
                         for cert, encoding, trust in ssl.enum_certificates(store)
                         if encoding == 'x509_asn'), encoding='ascii')
    rows = list(csv.DictReader((ROOT / 'research/china_index_official_methodology_evidence.csv').open(encoding='utf-8-sig')))
    tasks = []
    for row in rows:
        code = row['index_code']
        if row['methodology_evidence_url']:
            tasks.append((code, 'methodology_prior', row['methodology_evidence_url']))
        # Candidate paths are discovery attempts, never official links until body reviewed.
        tasks.append((code, 'methodology_candidate', BASE + code + '_Index_Methodology_cn.pdf'))
        tasks.append((code, 'factsheet', row['factsheet_evidence_url']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(acquire, tasks))
    (HERE / 'acquisition_manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    ca.unlink()
    print(json.dumps({'attempts': len(records), 'pdf_saved': sum('local_path' in x for x in records)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
