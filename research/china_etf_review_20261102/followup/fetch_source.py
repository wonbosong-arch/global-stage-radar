"""Fetch an explicitly selected public source with Windows CA trust and provenance."""
import sys
import json
import ssl
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import requests
from pypdf import PdfReader
from collect_official_documents import HERE

def fetch(key, url):
    ca = HERE / 'fetch_ca.pem'
    ca.write_text(''.join(ssl.DER_cert_to_PEM_cert(c) for store in ['ROOT', 'CA']
                         for c, e, t in ssl.enum_certificates(store) if e == 'x509_asn'), encoding='ascii')
    try:
        r = requests.get(url, verify=str(ca), timeout=40,
                         headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.sse.com.cn/'})
        ext = 'pdf' if r.content.startswith(b'%PDF') else 'html'
        target = HERE / 'sources' / f'{key}.{ext}'
        target.write_bytes(r.content)
        if ext == 'pdf':
            text = '\n'.join(f'--- PAGE {i+1} ---\n{p.extract_text()}' for i, p in enumerate(PdfReader(target).pages))
            target.with_suffix('.txt').write_text(text, encoding='utf-8')
        record = dict(key=key, requested_url=url, final_url=r.url, http_status=r.status_code,
                      retrieved_at_utc=datetime.now(timezone.utc).isoformat(), sha256=hashlib.sha256(r.content).hexdigest(),
                      bytes=len(r.content), local_path=f'sources/{target.name}',
                      content_type=r.headers.get('Content-Type', ''))
    except Exception as e:
        record = dict(key=key, requested_url=url, error=str(e), retrieved_at_utc=datetime.now(timezone.utc).isoformat())
    finally:
        ca.unlink(missing_ok=True)
    path = HERE / 'supplemental_manifest.json'
    records = json.loads(path.read_text(encoding='utf8')) if path.exists() else []
    records.append(record)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(record, ensure_ascii=False))

if __name__ == '__main__':
    fetch(sys.argv[1], sys.argv[2])
