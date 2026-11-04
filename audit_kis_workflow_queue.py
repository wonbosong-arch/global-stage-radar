"""Offline, read-only preflight for this repository's literal KIS queue blocks.

This deliberately supports only top-level, literal concurrency mappings; it is
not a YAML validator. Unknown shapes fail closed. No API, credentials or writes.
"""
import argparse
import difflib
import json
import re
from pathlib import Path

GROUP = "daily-closing-price-snapshot"
MEMBERS = frozenset({"candidate_collection.yml", "candidate_prices_manual.yml",
                     "china_candidate_prices.yml", "daily_prices.yml",
                     "japan_candidate_prices.yml"})


def concurrency(text):
    blocks = re.findall(r"(?m)^concurrency:\s*\n((?:(?:[ \t]+[^\n]*|)\n)*)", text)
    if len(blocks) != 1:
        raise ValueError("expected one literal top-level concurrency mapping")
    fields = {}
    for line in blocks[0].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"  ([a-z-]+):\s*([A-Za-z0-9_-]+)\s*(?:#.*)?", line)
        if not match or match[1] in fields:
            raise ValueError("unsupported or duplicate concurrency field")
        fields[match[1]] = match[2]
    if set(fields) - {"group", "cancel-in-progress", "queue"}:
        raise ValueError("unknown concurrency field")
    return fields


def audit(workflows):
    issues = []
    for name in sorted(MEMBERS):
        if name not in workflows:
            issues.append(f"{name}: missing shared KIS workflow")
            continue
        try:
            policy = concurrency(workflows[name])
            if policy.get("group") != GROUP:
                issues.append(f"{name}: shared KIS serialization lost")
            if policy.get("cancel-in-progress") != "false":
                issues.append(f"{name}: in-progress KIS batch is not protected")
            if policy.get("queue") != "max":
                issues.append(f"{name}: pending replacement risk (queue is not max)")
        except ValueError as exc:
            issues.append(f"{name}: {exc}")
    for name, text in workflows.items():
        if name not in MEMBERS and re.search(r"(?m)^  group: " + GROUP + r"\s*$", text):
            issues.append(f"{name}: unreviewed shared-group member")
    china = workflows.get("china_candidate_prices.yml", "")
    crons = re.findall(r'cron:\s*[\"\x27]([^\"\x27]+)[\"\x27]', china)
    if crons != ["0 22 * * 0-5"]:
        issues.append("china_candidate_prices.yml: 07:00 KST schedule changed")
    return issues


def proposed_text(text):
    """Return a candidate only; caller must never overwrite a workflow."""
    policy = concurrency(text)
    if policy.get("group") != GROUP or policy.get("cancel-in-progress") != "false":
        raise ValueError("review changed serialization before proposing queue policy")
    if policy.get("queue") == "max":
        return text
    if "queue" in policy:
        raise ValueError("review explicit queue policy first")
    return text.replace("  group: " + GROUP + "\n",
                        "  group: " + GROUP + "\n  queue: max\n", 1)


def proposal(workflows):
    return "".join("".join(difflib.unified_diff(
        workflows[name].splitlines(keepends=True),
        proposed_text(workflows[name]).splitlines(keepends=True),
        fromfile=f"a/.github/workflows/{name}", tofile=f"b/.github/workflows/{name}"))
        for name in sorted(MEMBERS))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-dir", type=Path, default=Path(".github/workflows"))
    parser.add_argument("--proposal", action="store_true", help="print unapplied diff only")
    args = parser.parse_args()
    workflows = {p.name: p.read_text(encoding="utf-8") for p in args.workflow_dir.iterdir()
                 if p.suffix in {".yml", ".yaml"}}
    if args.proposal:
        print(proposal(workflows), end="")
        return 0
    issues = audit(workflows)
    print(json.dumps({"issues": issues}, indent=2))
    return int(bool(issues))


if __name__ == "__main__":
    raise SystemExit(main())
