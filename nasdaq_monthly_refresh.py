"""Official screener button -> private quality-gated generations -> offline KIS replay.

No direct/hidden API, credentials, stealth, proxy rotation, public data publishing,
KIS network calls or operational activation. The optional browser is isolated.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlsplit
import uuid

from nasdaq_local_csv_review import aliases_from, clean, missing, read_table
from nasdaq_single_source import build_report, check_local_manifest, private_path

SOURCE = "https://www.nasdaq.com/market-activity/stocks/screener"
FIELDS = ["Symbol", "Name", "Last Sale", "Net Change", "% Change", "Market Cap",
          "Country", "IPO Year", "Volume", "Sector", "Industry"]
MAX_BYTES = 10_000_000
FAILURE_STAGES = frozenset({
    "private_state_setup", "input_provenance", "collector_start", "browser_launch",
    "browser_context", "page_navigation", "access_check", "table_wait",
    "csv_download", "csv_read", "validation_replay_publish",
})
# Only these literals may leave the browser exception boundary. Never emit a
# message, arbitrary exception class, URL, request metadata or traceback.
SAFE_ERROR_TYPES = frozenset({
    "Error", "TimeoutError", "TargetClosedError", "RuntimeError", "ValueError",
    "OSError", "FileNotFoundError", "FileExistsError", "PermissionError",
    "ImportError", "ModuleNotFoundError", "DownloadStopped",
})
NETWORK_CODES = {
    "ERR_NAME_NOT_RESOLVED": "dns_failure",
    "ERR_NAME_RESOLUTION_FAILED": "dns_failure",
    "ERR_CONNECTION_REFUSED": "tcp_failure",
    "ERR_CONNECTION_RESET": "tcp_failure",
    "ERR_CONNECTION_CLOSED": "tcp_failure",
    "ERR_CONNECTION_FAILED": "tcp_failure",
    "ERR_ADDRESS_UNREACHABLE": "tcp_failure",
    "ERR_INTERNET_DISCONNECTED": "network_unreachable",
    "ERR_PROXY_CONNECTION_FAILED": "proxy_connection_failure",
    "ERR_TUNNEL_CONNECTION_FAILED": "proxy_connection_failure",
    "ERR_CERT_AUTHORITY_INVALID": "tls_failure",
    "ERR_CERT_COMMON_NAME_INVALID": "tls_failure",
    "ERR_CERT_DATE_INVALID": "tls_failure",
    "ERR_CERT_INVALID": "tls_failure",
    "ERR_SSL_PROTOCOL_ERROR": "tls_failure",
    "ERR_SSL_VERSION_OR_CIPHER_MISMATCH": "tls_failure",
    "ERR_CONNECTION_TIMED_OUT": "network_timeout",
    "ERR_TIMED_OUT": "network_timeout",
    "ERR_ABORTED": "navigation_aborted",
    "ERR_EMPTY_RESPONSE": "empty_response",
    "ERR_HTTP2_PROTOCOL_ERROR": "http_protocol_failure",
    "ERR_HTTP_RESPONSE_CODE_FAILURE": "http_response_failure",
    "ERR_NETWORK_CHANGED": "network_changed",
    "ERR_BLOCKED_BY_CLIENT": "client_blocked",
    "ERR_BLOCKED_BY_RESPONSE": "response_blocked",
}


class DownloadStopped(ValueError):
    """Access denial/challenge: never retry or change identity."""

    def __init__(self, message, *, http_status=None):
        super().__init__(message)
        self.http_status = http_status


@contextmanager
def failure_stage(stage):
    """Attach a fixed phase label, without retaining browser messages in output."""
    try:
        yield
    except Exception as exc:
        if getattr(exc, "nasdaq_failure_stage", None) not in FAILURE_STAGES:
            exc.nasdaq_failure_stage = stage
        raise


def failure_details(exc):
    stage = getattr(exc, "nasdaq_failure_stage", None)
    result = dict(failure_stage=stage if stage in FAILURE_STAGES else "unclassified",
                  failure_code="access_stopped" if isinstance(exc, DownloadStopped)
                  else "timeout" if type(exc).__name__ == "TimeoutError" else "operation_failed")
    status = getattr(exc, "http_status", None)
    if isinstance(exc, DownloadStopped) and type(status) is int and 400 <= status <= 599:
        result["http_status"] = status
    if stage == "page_navigation" and not isinstance(exc, DownloadStopped):
        # Match only the exception prefix; a token embedded in a sensitive URL
        # or body must never be mistaken for the browser's reported error.
        message = str(exc)[:256]
        prefix = message.splitlines()[0] if message else ""
        match = re.match(r"^(?:Page\.goto: )?net::(ERR_[A-Z0-9_]+)(?=\s|$)", prefix)
        if match:
            code = match.group(1)
            result["failure_code"] = NETWORK_CODES.get(code, "network_error_unknown")
            if code in NETWORK_CODES:
                result["browser_error_code"] = code
        elif type(exc).__name__ == "TargetClosedError" or prefix.startswith(
                "Page.goto: Target page, context or browser has been closed"):
            result["failure_code"] = "browser_closed"
    status = getattr(exc, "nasdaq_navigation_http_status", None)
    if type(status) is int and 100 <= status <= 599:
        result["navigation_http_status"] = status
    return result


def safe_error_type(exc):
    name = type(exc).__name__
    return name if name in SAFE_ERROR_TYPES else "Exception"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def quality(raw, manifest, previous=None, min_rows=5000):
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("CSV size gate")
    headers, columns, rows = read_table(raw)
    if headers != FIELDS or columns != FIELDS:
        raise ValueError("Expected exact 11-field official CSV schema")
    if not min_rows <= len(rows) <= 20000:
        raise ValueError("CSV row-count gate")
    symbols = [clean(r["Symbol"]).upper() for r in rows]
    if any(not s for s in symbols) or len(set(symbols)) != len(symbols):
        raise ValueError("Blank or duplicate symbol")
    if any(missing(r["Name"], "Name") for r in rows):
        raise ValueError("Blank issuer name")
    # Reuse explicit, venue-aware alias validation. Never guess an alias.
    aliases = aliases_from(manifest)
    notation = defaultdict(set)
    for symbol in symbols:
        key = re.sub(r"[.-]", "/", symbol) if re.fullmatch(r"[A-Z0-9]+[./-][A-Z]", symbol) else symbol
        notation[key].add(symbol)
    if any(len(v) > 1 for v in notation.values()):
        raise ValueError("Same-class notation collision")
    for v in {v for _, v in aliases}:
        targets = [aliases.get((s, v), s) for s in symbols]
        if len(targets) != len(set(targets)):
            raise ValueError("Alias collision")
    absent = {f: sum(missing(r[f], f) for r in rows) for f in FIELDS}
    for field in ("Sector", "Industry"):
        if absent[field] / len(rows) > 0.20:
            raise ValueError("Native classification coverage gate")
    complete = sum(not missing(r["Sector"], "Sector") and not missing(r["Industry"], "Industry") for r in rows)
    if complete / len(rows) < .80:
        raise ValueError("Complete native classification coverage gate")
    for row in rows:
        for f in ("Last Sale", "Net Change", "% Change", "Market Cap", "Volume", "IPO Year"):
            if missing(row[f], f):
                continue
            try:
                number = float(row[f].replace(",", "").removeprefix("$").removesuffix("%"))
            except ValueError as exc:
                raise ValueError("Numeric field gate: " + f) from exc
            if not math.isfinite(number) or (f in ("Last Sale", "Market Cap", "Volume", "IPO Year") and number < 0):
                raise ValueError("Numeric field gate: " + f)
    result = dict(rows=len(rows), columns=columns, unique_symbols=len(set(symbols)),
                  missing=absent, native_classification_complete=complete,
                  explicit_aliases=len(aliases), csv_sha256=digest(raw), csv_bytes=len(raw),
                  source_exchange_column=False)
    if previous:
        if len(rows) < previous["rows"] * .85:
            raise ValueError("Row-count drop exceeds 15 percent")
        for f in ("Sector", "Industry"):
            if absent[f] / len(rows) > previous["missing"][f] / previous["rows"] + .05:
                raise ValueError("Classification missing rate increased over 5 points")
    return result


def official_manifest(raw, downloaded_at, instruction):
    return dict(dataset_kind="official_nasdaq_screener_csv", acquisition_method="official_ui_download",
                scope="private_noncommercial_offline", user_instruction_reference=instruction,
                csv_sha256=digest(raw), source_url=SOURCE, download_control="Download CSV",
                downloaded_at_utc=downloaded_at, downloaded_at_utc_reference="official UI download completed",
                source_as_of=None)


def acquire_button(page, destination, timeout=45000):
    """Only the visible official control; one click, without endpoint replay."""
    denied = []
    navigation_status = []
    def response_seen(response):
        host = urlsplit(response.url).hostname or ""
        if (host == "nasdaq.com" or host.endswith(".nasdaq.com")):
            request = response.request
            if (request.is_navigation_request() is True and request.frame == page.main_frame
                    and type(response.status) is int and 100 <= response.status <= 599):
                navigation_status.append(response.status)
        if (host == "nasdaq.com" or host.endswith(".nasdaq.com")) and response.status in (401, 403, 429):
            denied.append(response.status)
    def guard():
        text = page.locator("body").inner_text(timeout=timeout).lower()
        if denied or any(t in text for t in ("verify you are human", "access denied", "unusual traffic", "complete the captcha")):
            raise DownloadStopped("Official site access denial/challenge; no retry",
                                  http_status=denied[0] if denied else None)
    page.on("response", response_seen)
    try:
        with failure_stage("page_navigation"):
            response = page.goto(SOURCE, wait_until="domcontentloaded", timeout=timeout)
        with failure_stage("access_check"):
            if response is not None and response.status >= 400:
                raise DownloadStopped("Official page HTTP " + str(response.status), http_status=response.status)
            guard()
        # A loaded nonempty table avoids silently downloading an empty page.
        with failure_stage("table_wait"):
            page.get_by_role("cell").filter(has=page.get_by_role("link")).first.wait_for(timeout=timeout)
        with failure_stage("access_check"):
            guard()
        with failure_stage("csv_download"):
            with page.expect_download(timeout=timeout) as pending:
                page.get_by_role("button", name="Download CSV", exact=True).click(timeout=timeout)
            download = pending.value
            guard()
            if not re.fullmatch(r"nasdaq_screener_\d+\.csv", download.suggested_filename):
                raise ValueError("Unexpected official download filename")
            download.save_as(str(destination))
            if download.failure():
                raise ValueError("Official CSV download failed")
    except Exception as exc:
        if navigation_status:
            exc.nasdaq_navigation_http_status = navigation_status[-1]
        if denied:
            stopped = DownloadStopped("Official site HTTP " + str(denied[0]) + "; no retry", http_status=denied[0])
            stopped.nasdaq_failure_stage = getattr(exc, "nasdaq_failure_stage", "access_check")
            if navigation_status:
                stopped.nasdaq_navigation_http_status = navigation_status[-1]
            raise stopped from exc
        if isinstance(exc, DownloadStopped):
            raise
        # A broken page must not replace the original browser failure with a
        # secondary body-read error. A visible access challenge still stops.
        try:
            with failure_stage("access_check"):
                guard()
        except DownloadStopped as stopped:
            if navigation_status:
                stopped.nasdaq_navigation_http_status = navigation_status[-1]
            raise
        except Exception:
            pass
        raise


def collect(destination, instruction, attempts=2, sleep=time.sleep):
    """At most two timeout attempts; denial and malformed data are terminal."""
    if attempts not in (1, 2):
        raise ValueError("At most two attempts")
    from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout
    for attempt in range(attempts):
        try:
            with failure_stage("collector_start"), sync_playwright() as pw:
                with failure_stage("browser_launch"):
                    browser = pw.chromium.launch(headless=True, args=["--disable-http2"])
                try:
                    with failure_stage("browser_context"):
                        context = browser.new_context(accept_downloads=True)
                        page = context.new_page()
                    acquire_button(page, destination)
                finally:
                    browser.close()
            with failure_stage("csv_read"):
                raw = destination.read_bytes()
            return official_manifest(raw, datetime.now(timezone.utc).isoformat(), instruction)
        except DownloadStopped:
            raise
        except BrowserTimeout:
            if attempt + 1 == attempts:
                raise
            sleep(30)


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def load_current(root, now=None, min_rows=5000):
    """Verify pointer, immutable generation and replay hashes before fallback."""
    now = now or datetime.now(timezone.utc)
    root = private_path(root)
    pointer = json.loads((root / "current.json").read_text(encoding="utf-8"))
    generation = pointer["generation"]
    if not re.fullmatch(r"[a-f0-9]{32}", generation):
        raise ValueError("Invalid generation pointer")
    folder = private_path(root / "generations" / generation)
    if not folder.is_relative_to(root):
        raise ValueError("Generation escapes private root")
    for name in ("screener.csv", "manifest.json", "quality.json", "replay.json"):
        file = private_path(folder / name)
        if not file.is_relative_to(folder) or digest(file.read_bytes()) != pointer["hashes"][name]:
            raise ValueError("Last-good integrity failure")
    raw = (folder / "screener.csv").read_bytes()
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    check_local_manifest(manifest, digest(raw), now)
    measured = quality(raw, manifest, min_rows=min_rows)
    if measured != json.loads((folder / "quality.json").read_text(encoding="utf-8")):
        raise ValueError("Last-good quality mismatch")
    stamp = manifest.get("downloaded_at_utc")
    age = (now - datetime.fromisoformat(stamp.replace("Z", "+00:00"))).days if stamp else None
    return dict(folder=folder, quality=measured, manifest=manifest,
                download_age_days=age, source_as_of=manifest.get("source_as_of"),
                stale_or_unknown=age is None or age > 45,
                replay=json.loads((folder / "replay.json").read_text(encoding="utf-8")))


def refresh(root, csv_path, manifest, data_dir, as_of, now=None, min_rows=5000, replay=build_report):
    """Publish current pointer only after full validation/replay. Caller serializes writers."""
    now = now or datetime.now(timezone.utc)
    root = private_path(root, existing=False)
    root.mkdir(parents=True, exist_ok=True)
    # Fail concurrent writers instead of racing last-good replacement.
    with (root / ".refresh.lock").open("x"):
        pass
    try:
        previous = load_current(root, now, min_rows) if (root / "current.json").exists() else None
        raw = private_path(csv_path).read_bytes()
        check_local_manifest(manifest, digest(raw), now)
        measured = quality(raw, manifest, previous["quality"] if previous else None, min_rows)
        folder = root / "generations" / uuid.uuid4().hex
        folder.mkdir(parents=True)
        (folder / "screener.csv").write_bytes(raw)
        write_json(folder / "manifest.json", manifest)
        report = replay(folder / "screener.csv", folder / "manifest.json", data_dir, as_of, now=now)
        if report["operational_additions"] != 0 or report["csv_sha256"] != digest(raw):
            raise ValueError("Offline replay integrity gate")
        write_json(folder / "quality.json", measured)
        write_json(folder / "replay.json", report)
        names = ("screener.csv", "manifest.json", "quality.json", "replay.json")
        pointer = dict(generation=folder.name, hashes={n: digest((folder / n).read_bytes()) for n in names})
        pending = root / (uuid.uuid4().hex + ".pending.json")
        write_json(pending, pointer)
        os.replace(pending, root / "current.json")
        return load_current(root, now, min_rows)
    finally:
        (root / ".refresh.lock").unlink(missing_ok=True)


def summary(current):
    return dict(quality=current["quality"], stage_counts=current["replay"]["counts"],
                acquisition_method=current["manifest"]["acquisition_method"],
                source_as_of=current["source_as_of"], download_age_days=current["download_age_days"],
                stale_or_unknown=current["stale_or_unknown"], source_date_unknown=current["source_as_of"] is None,
                operational_additions=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--download", action="store_true")
    mode.add_argument("--csv", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--instruction-reference")
    parser.add_argument("--attempts", type=int, choices=(1, 2), default=2)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--summary", type=Path, help="Aggregate-only JSON outside Git")
    args = parser.parse_args()
    root = None
    exit_code = 0
    try:
        with failure_stage("private_state_setup"):
            root = private_path(args.state_dir, existing=False)
            root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temp:
            if args.download:
                if not args.instruction_reference:
                    raise ValueError("Download requires user instruction reference")
                source = Path(temp) / "download.csv"
                manifest = collect(source, args.instruction_reference, attempts=args.attempts)
            else:
                if not args.manifest:
                    raise ValueError("CSV import requires original hash-bound provenance")
                source = args.csv
                with failure_stage("input_provenance"):
                    manifest = json.loads(private_path(args.manifest).read_text(encoding="utf-8-sig"))
            with failure_stage("validation_replay_publish"):
                current = refresh(root, source, manifest, args.data_dir, args.as_of)
        result = dict(status="refreshed", **summary(current))
    except Exception as exc:
        # No exception string, private paths or response body in public logs.
        result = dict(status="failed", error_type=safe_error_type(exc), operational_additions=0,
                      last_good_available=False, **failure_details(exc))
        try:
            if root is None:
                raise ValueError("Private state unavailable")
            result.update(status="fallback", **summary(load_current(root)))
            result["last_good_available"] = True
        except Exception:
            pass
        exit_code = 2
    if args.summary:
        try:
            write_json(private_path(args.summary, existing=False), result)
        except Exception:
            # Even an invalid/unwritable summary path must not leak a traceback.
            result["aggregate_summary_error"] = "write_failed"
            exit_code = 2
    print(json.dumps(result))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
