"""Read-only EXAONE research pilot: JPX sector-index and stock-classification sources.

Fixed, externally checked evidence is supplied to the model. This is NOT live
JPX scraping, licensed data access, or autonomous browsing. One API request max.
Outputs remain review-only and are never activated or committed automatically.
"""
import argparse
from datetime import datetime, timezone
from http.client import HTTPException, HTTPSConnection
import json
import os
from pathlib import Path
import re
import sys
from time import perf_counter

HOST = "api.exaone.ai"
ENDPOINT = "/v1/chat/completions"
MODEL = "k-exaone_v2.5"
MAX_RESPONSE = 65536
HTTP_TIMEOUT_SECONDS = 90  # Already observed: previous call exceeded this limit.
TOPICS = ("sector_index_values", "index_history", "listed_stock_classification", "licensed_reuse")
EVIDENCE = (
    {
        "id": "JPX-A",
        "url": "https://www.jpx.co.jp/english/markets/indices/realvalues/",
        "observation": "Official JPX page lists TOPIX Sector Indices (33 sectors) and TOPIX-17 Series in real-time index displays, and a Historical Data link marked past 5 business days. HTML text does not establish that a downloadable full daily time series is free.",
    },
    {
        "id": "JPX-B",
        "url": "https://www.jpx.co.jp/english/markets/indices/factsheets/files/e_000_fac2_sector.pdf",
        "observation": "JPX factsheet dated 2025-08-29: 33 sectors are defined by SICC; TOPIX-17 combines these 33 sectors into 17 index groups. This is methodology/classification metadata, not index value histories or constituent holdings.",
    },
    {
        "id": "JPX-C",
        "url": "https://www.jpx.co.jp/english/markets/statistics-equities/misc/01.html",
        "observation": "Official List of TSE-listed Issues is a previous-month-end Excel updated around the third business day. Its security-master schema includes Local Code, English company name, market/section, 33/17 sector code and sector name, TOPIX size bucket. The latest published file must be independently read and checked to confirm Core30+Large70 constituents.",
    },
    {
        "id": "JPX-D",
        "url": "https://jpx-jquants.com/en/spec/eq-master",
        "observation": "JPX J-Quants Listed Issue Master specification includes Code, CoNameEn, S17, S17Nm, S33, S33Nm, ScaleCat, Mkt; use and scope depend on account plan and terms; no API login or trial access is provided in this task.",
    },
    {
        "id": "JPX-E",
        "url": "https://www.jpx.co.jp/english/markets/paid-info-equities/historical/index.html",
        "observation": "JPX describes paid index historical OHLC/other data through J-Quants DataCube and separate API/product tiers, with corporate-use/redistribution differences. No purchased feed or account exists in this task.",
    },
    {
        "id": "JPX-F",
        "url": "https://www.jpx.co.jp/english/term-of-use/",
        "observation": "JPX terms prohibit commercial collection/secondary use absent permission or paid authorization, and require separate licensing for third-party dissemination of index values. Do not copy/upload index values or issuer-level source data.",
    },
)
VALID_EVIDENCE = {item["id"] for item in EVIDENCE}
ACCESS = {"public_web_current", "public_methodology", "public_monthly_master", "account_or_paid", "permission_required", "unknown"}
STATUS = {"supported_by_supplied_evidence", "needs_verification"}
SAFE_STR = re.compile(r"^[^\x00-\x08\x0b\x0c\x0e-\x1f]{1,260}$")


def payload():
    instructions = (
        "You are K-EXAONE 2.5 performing a narrowly scoped official-source availability audit "
        "for research on 100 Japanese stocks (TOPIX Core30 30 + Large70 70). "
        "You have NO browser, NO live JPX data, and NO official source-file access. "
        "Only reason from the supplied official-site evidence notes, and distinguish "
        "website index values, historic index OHLC, stock 33/17 sector classification, "
        "and licensing. Do not invent index prices, individual stock codes, company names, "
        "verified source files, TOPIX constituent membership or permissions. "
        "Answer ONE JSON object only, without markdown, with exactly keys "
        "task, findings, next_actions. task must equal 'japan_sector_source_audit'. "
        "findings must be an array of 4 objects, exactly one for each topic "
        "sector_index_values, index_history, listed_stock_classification, licensed_reuse. "
        "Each object has exactly keys topic, access, status, evidence_ids, conclusion, gap. "
        "access is one of public_web_current, public_methodology, public_monthly_master, "
        "account_or_paid, permission_required, unknown. "
        "status is supported_by_supplied_evidence or needs_verification. "
        "evidence_ids must contain 1-4 distinct source IDs from JPX-A through JPX-F; "
        "conclusion and gap are nonempty Korean phrases less than 260 characters. "
        "next_actions is an array of 2-4 short Korean strings describing verification "
        "work only, not unauthorized downloads or operational activation. "
        "Keep each conclusion and gap under 80 Korean characters; do not add long explanations. "
        "This is a SOURCE REVIEW artifact, never a declaration that 100 stocks are validated."
    )
    request = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps({"objective": "2026-10 month-end TOPIX Core30+Large70, official index and industry-data availability", "evidence": EVIDENCE}, ensure_ascii=False)},
        ],
        "reasoning_effort": "low",
        "max_tokens": 4096,
        "stream": False,
    }
    return json.dumps(request, ensure_ascii=False).encode("utf-8")


def validate_report(content):
    if not isinstance(content, str) or len(content.encode("utf-8")) > 16000:
        raise ValueError("invalid_model_content")
    source = content.strip()
    # Permit a single JSON code fence but never free text around the JSON.
    fenced = re.fullmatch(r"```(?:json)?[ \t]*\n([\s\S]*?)\n```[ \t]*", source)
    if fenced:
        source = fenced.group(1).strip()
    try:
        data = json.loads(source)
    except (TypeError, ValueError, RecursionError):
        raise ValueError("invalid_model_json") from None
    if not isinstance(data, dict) or set(data) != {"task", "findings", "next_actions"} or data["task"] != "japan_sector_source_audit":
        raise ValueError("invalid_report_shape")
    findings = data["findings"]
    if not isinstance(findings, list) or len(findings) != len(TOPICS):
        raise ValueError("invalid_findings_count")
    seen = set()
    for item in findings:
        if not isinstance(item, dict) or set(item) != {"topic", "access", "status", "evidence_ids", "conclusion", "gap"}:
            raise ValueError("invalid_finding")
        if item["topic"] not in TOPICS or item["topic"] in seen:
            raise ValueError("duplicate_or_invalid_topic")
        seen.add(item["topic"])
        if item["access"] not in ACCESS or item["status"] not in STATUS:
            raise ValueError("invalid_finding_status")
        refs = item["evidence_ids"]
        if not isinstance(refs, list) or not 1 <= len(refs) <= 4 or len(set(map(str, refs))) != len(refs) or not set(refs) <= VALID_EVIDENCE:
            raise ValueError("invalid_evidence_ids")
        if any(not isinstance(item[key], str) or not SAFE_STR.fullmatch(item[key]) for key in ("conclusion", "gap")):
            raise ValueError("invalid_summary_text")
    actions = data["next_actions"]
    if not isinstance(actions, list) or not 2 <= len(actions) <= 4 or any(not isinstance(a, str) or not SAFE_STR.fullmatch(a) for a in actions):
        raise ValueError("invalid_actions")
    return data


def safe_usage(raw):
    if not isinstance(raw, dict):
        return {key: "미확인" for key in ("prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens")}
    detail = raw.get("completion_tokens_details") or {}
    if not isinstance(detail, dict):
        detail = {}
    vals = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        v = raw.get(key)
        vals[key] = v if type(v) is int and 0 <= v <= 1000000 else "미확인"
    # EXAONE documents top-level usage.reasoning_tokens; nested details are optional.
    v = raw.get("reasoning_tokens")
    if type(v) is not int or not 0 <= v <= 1000000:
        v = detail.get("reasoning_tokens")
    vals["reasoning_tokens"] = v if type(v) is int and 0 <= v <= 1000000 else "미확인"
    return vals


def one_request(api_key, data):
    if not re.fullmatch(r"[!-~]{8,512}", api_key):
        raise ValueError("missing_or_invalid_api_key")
    connection = HTTPSConnection(HOST, timeout=HTTP_TIMEOUT_SECONDS)
    start = perf_counter()
    phase = "send"
    try:
        connection.request("POST", ENDPOINT, body=data, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        })
        phase = "await_headers"
        with connection.getresponse() as response:
            phase = "read_body"
            status = response.status
            limits = {}
            for key in ("x-ratelimit-limit-requests", "x-ratelimit-remaining-requests", "x-ratelimit-reset-requests", "retry-after"):
                text = response.getheader(key)
                limits[key] = text if isinstance(text, str) and re.fullmatch(r"[0-9]{1,12}(?:ms|s|m|h)?", text) else "미확인"
            body = response.read(MAX_RESPONSE + 1)
    except TimeoutError:
        elapsed = round(perf_counter() - start, 2)
        raise ValueError(f"exaone_timeout_{phase}_after_{elapsed}s") from None
    except ConnectionError:
        raise ValueError("exaone_connection_error") from None
    except (OSError, HTTPException):
        raise ValueError("exaone_transport_error") from None
    finally:
        connection.close()
    elapsed = round(perf_counter() - start, 3)
    if status != 200:
        raise ValueError("exaone_http_" + str(status))
    if len(body) > MAX_RESPONSE:
        raise ValueError("exaone_response_too_large")
    try:
        envelope = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("exaone_invalid_envelope_json") from None
    if not isinstance(envelope, dict):
        raise ValueError("exaone_invalid_envelope_type")

    choices = envelope.get("choices")
    choice = choices[0] if isinstance(choices, list) and len(choices) == 1 else None
    reason = choice.get("finish_reason") if isinstance(choice, dict) else None
    message = choice.get("message") if isinstance(choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None

    # EXAONE returns usage.reasoning_tokens at the top level. Diagnostics contain
    # no model content, reasoning text, tokens, credentials or arbitrary headers.
    reported_reason = reason if reason in ("stop", "length", "content_filter", "tool_calls") else "other_or_missing"
    diagnostic = {
        "finish_reason": reported_reason,
        "elapsed_seconds": elapsed,
        "content_bytes": min(len(content.encode("utf-8")), MAX_RESPONSE) if isinstance(content, str) else 0,
        "usage": safe_usage(envelope.get("usage")),
        "rate_limit_headers": limits,
    }
    print("exaone_response_metadata: " + json.dumps(diagnostic, ensure_ascii=False), file=sys.stderr)
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choice, dict):
        raise ValueError("exaone_invalid_choices")
    if reason == "length":
        raise ValueError("exaone_output_truncated")
    if reason != "stop":
        raise ValueError("exaone_incomplete_finish_reason")
    if (not isinstance(message, dict) or message.get("role") != "assistant"
            or message.get("refusal") or message.get("tool_calls")):
        raise ValueError("exaone_invalid_assistant_message")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("exaone_empty_final_content")
    try:
        report = validate_report(content)
    except (ValueError, TypeError, AttributeError, RecursionError) as error:
        reason_code = str(error)
        allowed = {
            "invalid_model_content", "invalid_model_json", "invalid_report_shape",
            "invalid_findings_count", "invalid_finding", "duplicate_or_invalid_topic",
            "invalid_finding_status", "invalid_evidence_ids", "invalid_summary_text",
            "invalid_actions",
        }
        reason_code = reason_code if reason_code in allowed else "invalid_report_unknown"
        raise ValueError("exaone_report_" + reason_code) from None
    if api_key in json.dumps(report, ensure_ascii=False):
        raise ValueError("model_echoed_secret")
    return report, {"api_requests": 1, "api_success": 1, "api_failures": 0, "elapsed_seconds": elapsed,
                    "usage": safe_usage(envelope.get("usage")), "rate_limit_headers": limits}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Explicitly authorize a single API request")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    request = payload()
    if not args.live:
        check = json.loads(request.decode("utf-8"))
        assert check["model"] == MODEL and len(check["messages"]) == 2
        print("Offline contract check passed; EXAONE requests: 0.")
        return 0
    if not args.out:
        parser.error("live run requires --out")
    try:
        report, metrics = one_request(os.getenv("EXAONE_API_KEY", ""), request)
        result = {
            "task": "japan_sector_source_audit",
            "source_review_status": "unverified_model_report_for_human_review",
            "topix100_company_records_verified": 0,
            "actual_index_values_downloaded": 0,
            "source_evidence": [{"id": item["id"], "official_url": item["url"]} for item in EVIDENCE],
            "model_report": report,
            "model_usage": metrics,
            "executed_at_utc": datetime.now(timezone.utc).isoformat(),
            "license_gate": "no_jpx_source_data_or_index_history_fetched",
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("EXAONE one-request source audit created. No JPX dataset downloaded.")
        return 0
    except (ValueError, OSError) as error:
        # Only known error codes; never disclose response bodies, headers or credentials.
        print("pilot_failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
