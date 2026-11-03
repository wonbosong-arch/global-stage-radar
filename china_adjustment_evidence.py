"""Offline evidence sufficiency diagnostics; no Stage authorization or price output."""
import argparse
import hashlib
import json
import os
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from china_history_audit import external_path

EVENT_WORDS = ('分红', '收益分配', '拆分', '折算', '合并')


def document_content_check(body):
    """HTTP success and a retained hash do not establish specification content."""
    text = body.decode('utf-8', errors='replace')
    error = ('http-equiv' in text.lower() and 'refresh' in text.lower()) or 'error2.jsp' in text
    return dict(bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                error_redirect=error,
                modp_mentioned=not error and 'MODP' in text.upper(),
                provider_algorithm_confirmed=False)


def notice_coverage(body, receipt, *, symbol, interval_start, interval_end):
    """Validate the retained first page within its explicit filter, never globally.

    A zero title match is bounded negative evidence, including with complete
    pagination. It cannot prove absence in other categories or issuer reports.
    """
    start, end = date.fromisoformat(interval_start), date.fromisoformat(interval_end)
    if start > end:
        raise ValueError('Invalid coverage interval')
    url = urlsplit(receipt.get('url', ''))
    query = parse_qs(url.query)
    required = dict(sqlId='COMMON_PL_JJXX_JJGG_NEW_L', SECURITY_CODE=symbol,
                    isPagination='true', **{'pageHelp.pageNo': '1'})
    if (url.scheme != 'https' or url.netloc != 'query.sse.com.cn'
            or url.path != '/commonQuery.do' or receipt.get('status') != 200
            or receipt.get('sha256') != hashlib.sha256(body).hexdigest()
            or any(query.get(k) != [v] for k, v in required.items())):
        raise ValueError('Invalid notice provenance')
    try:
        if any(len(query.get(k, [])) != 1 for k in
               ('START_DATE', 'END_DATE', 'BULLETIN_TYPE', 'pageHelp.pageSize')):
            raise ValueError('Ambiguous query filters')
        qstart = date.fromisoformat(query['START_DATE'][0])
        qend = date.fromisoformat(query['END_DATE'][0])
        category = query['BULLETIN_TYPE'][0]
        page_size = int(query['pageHelp.pageSize'][0])
        payload = json.loads(body)
        rows, page = payload['result'], payload['pageHelp']
        total = page['total']
        if (qstart > qend or not category or not isinstance(rows, list)
                or type(total) is not int or total < 0
                or page.get('pageNo') != 1 or page.get('pageSize') != page_size
                or page_size < 1 or len(rows) > page_size or len(rows) > total
                or payload.get('actionErrors') or payload.get('fieldErrors')):
            raise ValueError('Invalid notice page')
        seen = set()
        for row in rows:
            published = date.fromisoformat(row['SSEDATE'])
            key = row['URL']
            if (row['SECURITY_CODE'] != symbol or not qstart <= published <= qend
                    or not isinstance(row['TITLE'], str) or not row['TITLE'].strip()
                    or not key.startswith('/disclosure/fund/announcement/') or key in seen):
                raise ValueError('Invalid notice identity/date/duplicate')
            seen.add(key)
    except (KeyError, TypeError, IndexError, json.JSONDecodeError) as exc:
        raise ValueError('Malformed notice evidence') from exc
    complete = len(rows) == total
    matches = sum(any(word in row['TITLE'] for word in EVENT_WORDS) for row in rows)
    return dict(symbol=symbol, category=category, query_start=qstart.isoformat(),
                query_end=qend.isoformat(), total=total, returned=len(rows),
                pagination_complete=complete, interval_covered=qstart <= start <= end <= qend,
                event_title_matches=matches,
                bounded_negative=complete and matches == 0 and qstart <= start <= end <= qend,
                event_inventory_complete=False, adjusted_history_verified=False,
                stage_ready=False)


def evidence_gate(raw_audit):
    """Keep 35-week raw length separate from unverified adjustment evidence.

    No caller-provided verification booleans are accepted. There is no verified
    provider algorithm, historical paired archive or complete event inventory
    in the current repository. Future authorization needs a reviewed validator.
    """
    return dict(symbol=raw_audit['symbol'],
                raw_35_week_prerequisite=raw_audit.get('reconciliation_valid') is True
                and raw_audit.get('completed_weeks', 0) >= 35
                and raw_audit.get('prior_comparison_ready') is True,
                adjustment_evidence_gate=False,
                missing_evidence=['provider_adjustment_algorithm_and_rounding',
                                  'historical_same_snapshot_modp_0_1_requests_and_responses',
                                  'whole_interval_corporate_action_inventory',
                                  'previous_stage_and_benchmark_policy'],
                review_blocked=raw_audit['symbol'] == '512400',
                stage_ready=False, operational_eligible=False)


def audit_retained(root, event_report):
    """Reuse #199's audit result and hash-check retained notice/document bytes."""
    root = external_path(root)
    source = Path(__file__).parent / 'research/china_corporate_action_provenance.json'
    provenance = json.loads(source.read_text(encoding='utf-8'))
    indexed = {q['symbol']: q for q in provenance['queries']}
    reports = []
    for item in event_report['symbols']:
        symbol = item['symbol']
        raw = item['raw_audit']
        saved = indexed[symbol]
        body = external_path(root / 'corporate_action_evidence' / f'{symbol}-fund05.json').read_bytes()
        receipt = json.loads(external_path(
            root / 'corporate_action_evidence' / f'{symbol}-receipt.json').read_bytes())
        if any(receipt.get(k) != saved.get(k) for k in ('url', 'sha256', 'status', 'retrieved_at_utc')):
            raise ValueError('Notice receipt differs from retained provenance')
        coverage = notice_coverage(body, receipt, symbol=symbol,
                                   interval_start=raw['observed_start'], interval_end=raw['observed_end'])
        reports.append(dict(gates=evidence_gate(raw), notices=coverage))
    documents = []
    checks = json.loads((Path(__file__).parent / 'research/china_kis_document_checks.json')
                        .read_text(encoding='utf-8'))
    for item in checks['retained_portal_responses'] + checks['official_samples']:
        key = hashlib.sha256(item['url'].encode()).hexdigest()
        body = external_path(root / 'corporate_action_evidence' / f'{key}.bin').read_bytes()
        if hashlib.sha256(body).hexdigest() != item['sha256']:
            raise ValueError('Document changed after retention')
        documents.append(dict(url=item['url'], **document_content_check(body)))
    return dict(symbols=reports, retained_kis_documents=documents, network_requests=0,
                stage_possible=0, stage_withheld=len(reports))


def main():
    from china_corporate_action_audit import audit_private
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of-date', required=True)
    args = parser.parse_args()
    root = os.environ.get('CHINA_PRIVATE_SNAPSHOT_DIR')
    if not root:
        parser.error('CHINA_PRIVATE_SNAPSHOT_DIR required')
    print(json.dumps(audit_retained(root, audit_private(root, as_of_date=args.as_of_date)), indent=2))


if __name__ == '__main__':
    main()
