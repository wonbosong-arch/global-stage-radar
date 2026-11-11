"""One EXAONE codegen call: repair private file-path boundary in TOPIX100 validator.

No generated code is executed alongside the EXAONE API secret.
"""
import argparse
import ast
from datetime import datetime, timezone
from http.client import HTTPSConnection, HTTPException
import json
import os
from pathlib import Path
import re
import sys
from time import perf_counter

HOST = "api.exaone.ai"
MODEL = "k-exaone_v2.5"
TASK = "topix100_private_path_boundary_fix"
TARGET_SHA = "377c3e4f48a824882ff9d0325fa48cc6653fdd3c"


def source_excerpt(path):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assignments = [n for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "REPO"
                           for t in n.targets)]
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == "safe_outside_repo"]
    if len(assignments) != 1 or len(functions) != 1:
        raise ValueError("target_source_shape_changed")
    return (ast.get_source_segment(source, assignments[0]),
            ast.get_source_segment(source, functions[0]))


def payload(target):
    assignment, function = source_excerpt(target)
    prompt = (
        "You are K-EXAONE, writing a REAL tiny correction to an existing Python "
        "validator of TOPIX Core30 + Large70 (100 Japanese stocks). "
        "There is a bug: paths in normal private sibling research directories "
        "are erroneously rejected because REPO points to a parent workspace. "
        "Do not recreate the validator. Respond with exactly ONE JSON object "
        "with exactly two keys 'repo_assignment' and 'replacement_function', "
        "each containing a Python source-code string. No markdown or extra keys. "
        "'repo_assignment' must be a single module-level assignment to REPO "
        "representing the resolved directory containing this .py module. "
        "'replacement_function' must be a single synchronous function "
        "safe_outside_repo(path: Path) -> Path, with one path argument, no "
        "extra top-level declarations or imports; rely on existing pathlib.Path. "
        "The function must return the resolved Path for an outside location, "
        "including a sibling directly adjacent to the checkout. For the repository "
        "root, children inside the repository, and any symlink resolving into "
        "the repository, raise ValueError with exact code "
        "'private_jpx_files_must_be_outside_checkout'. "
        "No network, shells, dynamic execution, file writes, extra data, or stubs. "
        "Keep the function below 20 lines. All verification uses synthetic paths."
    )
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps({
                "task": TASK, "target_sha": TARGET_SHA,
                "original_repo_assignment": assignment,
                "original_function": function,
                "cases": ["repo root forbidden", "repo descendant forbidden",
                          "symlink into repo forbidden", "sibling allowed",
                          "external private directory allowed"],
            }, ensure_ascii=False)},
        ],
        "reasoning_effort": "low",
        "max_tokens": 4096,
        "stream": False,
    }
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def validate_candidate(content):
    if not isinstance(content, str) or not 0 < len(content.encode("utf-8")) < 12000:
        raise ValueError("invalid_candidate_content")
    source = content.strip()
    fence = chr(96) * 3
    if source.startswith(fence):
        match = re.fullmatch(
            re.escape(fence) + r"(?:json)?[ \t]*\n([\s\S]*?)\n"
            + re.escape(fence) + r"[ \t]*", source
        )
        if not match:
            raise ValueError("invalid_candidate_json")
        source = match.group(1).strip()
    try:
        obj = json.loads(source)
    except (ValueError, TypeError):
        raise ValueError("invalid_candidate_json") from None
    if (not isinstance(obj, dict) or
            set(obj) != {"repo_assignment", "replacement_function"} or
            any(not isinstance(v, str) or not 0 < len(v) <= 3000
                for v in obj.values())):
        raise ValueError("invalid_candidate_shape")
    try:
        a = ast.parse(obj["repo_assignment"])
        f = ast.parse(obj["replacement_function"])
    except (SyntaxError, ValueError):
        raise ValueError("invalid_candidate_python") from None
    if (len(a.body) != 1 or not isinstance(a.body[0], ast.Assign)
            or len(a.body[0].targets) != 1
            or not isinstance(a.body[0].targets[0], ast.Name)
            or a.body[0].targets[0].id != "REPO"):
        raise ValueError("invalid_repo_assignment")
    if (len(f.body) != 1 or not isinstance(f.body[0], ast.FunctionDef)
            or f.body[0].name != "safe_outside_repo"
            or len(f.body[0].args.args) != 1
            or f.body[0].args.args[0].arg != "path"
            or f.body[0].decorator_list):
        raise ValueError("invalid_replacement_function")
    # Keep the module-level assignment strictly limited to computing the
    # current module directory; never permit a side-effecting assignment.
    for n in ast.walk(a):
        if isinstance(n, ast.Name) and n.id not in {"REPO", "Path", "__file__"}:
            raise ValueError("invalid_repo_assignment")
        if isinstance(n, ast.Attribute) and n.attr not in {"parent", "resolve"}:
            raise ValueError("invalid_repo_assignment")
        if isinstance(n, ast.Call):
            fn = n.func
            if not ((isinstance(fn, ast.Name) and fn.id == "Path")
                    or (isinstance(fn, ast.Attribute) and fn.attr == "resolve")):
                raise ValueError("invalid_repo_assignment")
    for n in ast.walk(f):
        if isinstance(n, ast.Attribute) and n.attr in {
            "unlink", "write_text", "write_bytes", "open", "mkdir", "rmdir",
            "rename", "replace", "system", "popen", "spawn", "chmod", "chown",
        }:
            raise ValueError("invalid_candidate_construct")
    for n in ast.walk(f):
        if isinstance(n, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal,
                          ast.AsyncFunctionDef, ast.Lambda, ast.Yield, ast.Await)):
            raise ValueError("invalid_candidate_construct")
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {
            "eval", "exec", "compile", "open", "__import__", "getattr",
            "setattr", "delattr", "globals", "locals", "breakpoint", "input",
        }:
            raise ValueError("invalid_candidate_construct")
    return obj


def safe_usage(obj):
    obj = obj if isinstance(obj, dict) else {}
    return {key: obj[key] if type(obj.get(key)) is int
            and 0 <= obj[key] <= 1000000 else "미확인"
            for key in ("prompt_tokens", "completion_tokens", "total_tokens",
                        "reasoning_tokens")}


RATE_HEADERS = (
    "x-second-rate-limit",
    "x-second-rate-limit-remaining",
    "x-minute-rate-limit",
    "x-minute-rate-limit-remaining",
    "x-day-rate-limit",
    "x-day-rate-limit-remaining",
    "retry-after",
    "retry-after-ms",
)


def safe_rate_headers(response):
    """Only record numeric limit/retry headers; never record headers wholesale."""
    values = {}
    for name in RATE_HEADERS:
        raw = response.getheader(name)
        if isinstance(raw, str):
            raw = raw.strip()
        values[name] = (
            raw if isinstance(raw, str)
            and re.fullmatch(r"[0-9]{1,12}(?:\.[0-9]{1,3})?", raw)
            else "미확인"
        )
    return values


def generate(key, request):
    if not re.fullmatch(r"[!-~]{8,512}", key):
        raise ValueError("missing_or_invalid_api_key")
    conn = HTTPSConnection(HOST, timeout=90)
    started = perf_counter()
    try:
        conn.request("POST", "/v1/chat/completions", body=request, headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        })
        with conn.getresponse() as response:
            status = response.status
            rates = safe_rate_headers(response)
            raw = response.read(32769)
    except (TimeoutError, OSError, HTTPException):
        raise ValueError("exaone_transport_failure") from None
    finally:
        conn.close()
    duration = round(perf_counter() - started, 3)
    if status != 200:
        if status == 429:
            print("exaone_rate_limited: " + json.dumps({
                "http_status": 429,
                "elapsed_seconds": duration,
                "rate_limits": rates,
                "automatic_retries": 0,
            }, ensure_ascii=False), file=sys.stderr)
        raise ValueError("exaone_http_" + str(status))
    if len(raw) > 32768:
        raise ValueError("exaone_response_too_large")
    try:
        envelope = json.loads(raw.decode("utf-8"))
        choices = envelope["choices"]
        choice = choices[0] if isinstance(choices, list) and len(choices) == 1 else None
        if not isinstance(choice, dict):
            raise ValueError("exaone_invalid_choice")
        finish = choice.get("finish_reason")
        usage = safe_usage(envelope.get("usage"))
        print("exaone_candidate_metadata: " + json.dumps({
            "finish_reason": finish if finish in {"stop", "length"} else "other",
            "elapsed_seconds": duration, "usage": usage,
            "rate_limits": rates,
        }, ensure_ascii=False), file=sys.stderr)
        if finish == "length":
            raise ValueError("exaone_output_truncated")
        if finish != "stop":
            raise ValueError("exaone_incomplete_response")
        msg = choice["message"]
        if (msg.get("role") != "assistant" or msg.get("refusal")
                or msg.get("tool_calls")):
            raise ValueError("exaone_invalid_message")
        candidate = validate_candidate(msg["content"])
    except (ValueError, KeyError, TypeError, UnicodeError, AttributeError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(("exaone_", "invalid_")):
            raise
        raise ValueError("exaone_invalid_envelope") from None
    if key in json.dumps(candidate, ensure_ascii=False):
        raise ValueError("model_echoed_secret")
    return {"task": TASK, "target_sha": TARGET_SHA,
            "status": "untrusted_code_candidate_not_executed_in_secret_job",
            "candidate": candidate,
            "metrics": {"api_requests": 1, "elapsed_seconds": duration,
                        "usage": usage, "rate_limits": rates},
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "jpx_rows_used": 0}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    request = payload(args.target)
    if not args.live:
        assert json.loads(request)["model"] == MODEL
        print("Offline EXAONE bugfix prompt valid; API calls 0")
        return 0
    if not args.out:
        parser.error("--live requires --out")
    try:
        output = generate(os.getenv("EXAONE_API_KEY", ""), request)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2)
                            + "\n", encoding="utf-8")
    except (ValueError, OSError) as ex:
        label = str(ex)
        if not re.fullmatch(
            r"(?:exaone_[a-z_0-9]+|invalid_[a-z_0-9]+|missing_or_invalid_api_key|model_echoed_secret|target_source_shape_changed)",
            label,
        ):
            label = "pilot_failed"
        print("exaone_japan_fix_failed: " + label, file=sys.stderr)
        return 1
    print("Untrusted EXAONE code candidate saved without executing it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
