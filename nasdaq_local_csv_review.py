"""Inspect an authorized, manually supplied local CSV; stdout only, no collection.

Native sector observations are not GICS/ETF mappings or Stage eligibility.
The expected columns below are an intake contract, not a verified Nasdaq schema.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re

from us_sector_mapping_batch import BASELINE, EXPANSION, saved_baseline

ROOT = Path(__file__).resolve().parent
BATCH = ROOT / "docs/evidence/us-sector-mapping-batch-20261105.json"
FIELDS = ("Symbol", "Name", "Exchange", "Sector", "Industry", "Market Cap")
VENUES = {"NASDAQ": "NAS", "NAS": "NAS", "NYSE": "NYS", "NYS": "NYS",
          "AMEX": "AMS", "AMS": "AMS", "NYSE AMERICAN": "AMS"}
EMPTY = {"", "n/a", "na", "null", "none", "nan", "--", "-", "unknown"}


def clean(value):
    return str(value or "").strip()


def missing(value, field):
    # NA is a possible ticker, never a universal missing-value token.
    return not clean(value) if field in ("Symbol", "Name") else clean(value).lower() in EMPTY


def venue(value):
    return VENUES.get(clean(value).upper())


def positive_cap(value):
    try:
        number = float(clean(value).replace(",", "").removeprefix("$"))
        return math.isfinite(number) and number > 0
    except ValueError:
        return False


def outside_git(path):
    path = path.resolve(strict=True)
    if any((p / ".git").exists() for p in (path.parent, *path.parents)):
        raise ValueError("External CSV must be outside every Git checkout")
    return path


def check_permission(manifest, now):
    """Require an explicit user declaration; this cannot authenticate a license."""
    if (manifest.get("permission_status") != "confirmed_by_user"
            or not clean(manifest.get("permission_reference"))
            or any(manifest.get(k) is not True for k in
                   ("manual_download_allowed", "local_storage_allowed", "offline_analysis_allowed"))):
        raise ValueError("Documented download/storage/offline-analysis permission required")
    if manifest.get("source_url") != "https://www.nasdaq.com/market-activity/stocks/screener":
        raise ValueError("Expected official screener source URL")
    if manifest.get("acquisition_method") != "user_manual_download":
        raise ValueError("Only user manual-download provenance is supported")
    stamp = datetime.fromisoformat(clean(manifest.get("downloaded_at_utc")).replace("Z", "+00:00"))
    if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0 or stamp > now:
        raise ValueError("Download time must be explicit UTC and not future")
    effective = manifest.get("source_as_of")
    if effective is not None and date.fromisoformat(effective) > stamp.date():
        raise ValueError("Source as-of must not follow download date")
    if effective is not None and not clean(manifest.get("source_as_of_reference")):
        raise ValueError("Source as-of needs its own evidence, not the download timestamp")
    return stamp


def read_table(raw):
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    headers = next(reader, [])
    canonical = {re.sub(r"\s+", "", f).lower(): f for f in FIELDS}
    names = [canonical.get(re.sub(r"\s+", "", h).lower(), h.strip()) for h in headers]
    if not names or len(set(names)) != len(names) or "" in names:
        raise ValueError("Missing, blank or duplicate CSV headers")
    rows = []
    for values in reader:
        if not values:
            continue
        if len(values) != len(names):
            raise ValueError("CSV row width differs from header")
        rows.append(dict(zip(names, map(clean, values))))
    return headers, names, rows


def aliases_from(manifest):
    aliases = {}
    for entry in manifest.get("symbol_aliases", []):
        source, target = (clean(entry.get(k)).upper() for k in ("source_symbol", "kis_symbol"))
        v = venue(entry.get("venue"))
        # Explicit notation-only aliases preserve each class. No punctuation stripping,
        # ticker-change guesses, preferred/common conversion or cross-class collapse.
        norm = lambda s: s.replace(".", "/").replace("-", "/")
        if (not v or not re.fullmatch(r"[A-Z0-9]+[./-][A-Z]", source)
                or not re.fullmatch(r"[A-Z0-9]+[./-][A-Z]", target)
                or norm(source) != norm(target) or source == target
                or not clean(entry.get("evidence_reference")) or (source, v) in aliases):
            raise ValueError("Alias needs unique same-class notation and explicit evidence")
        aliases[source, v] = target
    return aliases


def inspect_rows(rows, columns, registry, groups, manifest):
    aliases = aliases_from(manifest)
    export_venue = venue(manifest.get("export_exchange"))
    if manifest.get("export_exchange") and (not export_venue or
            not clean(manifest.get("export_exchange_reference"))):
        raise ValueError("Exchange-filter attribution requires evidence")
    keyed = defaultdict(list)
    unsupported = 0
    for number, row in enumerate(rows, 2):
        v = venue(row.get("Exchange")) if "Exchange" in columns else export_venue
        if not v:
            unsupported += 1
            continue
        symbol = clean(row.get("Symbol")).upper()
        target = aliases.get((symbol, v), symbol)
        keyed[target, v].append((number, row, "explicit_notation_alias" if target != symbol else "exact"))
    keys = [(clean(r["symbol"]).upper(), venue(r["exchange"])) for r in registry]
    if any(not s or not v for s, v in keys) or len(set(keys)) != len(keys):
        raise ValueError("KIS US registry requires unique nonempty ticker+venue pairs")
    if any(not set(symbols).issubset({s for s, _ in keys}) for symbols in groups.values()):
        raise ValueError("Saved cohort missing from current KIS registry")
    matches = []
    schema_ok = all(f in columns for f in FIELDS if f != "Exchange")
    for r, key in zip(registry, keys):
        found = keyed.get(key, [])
        usable = len(found) == 1 and schema_ok
        number, source, basis = found[0] if len(found) == 1 else (None, {}, None)
        present = usable and not missing(source.get("Sector"), "Sector")
        matches.append({"symbol": key[0], "venue": key[1],
            "status": "matched" if usable else "duplicate_or_alias_collision" if len(found) > 1
                      else "schema_incomplete" if found else "unmatched",
            "match_basis": basis, "csv_row": number, "sector_present": present,
            "dated_sector_observation": present and manifest.get("source_as_of") is not None,
            "industry_present": usable and not missing(source.get("Industry"), "Industry"),
            "name_equal": usable and clean(source.get("Name")).casefold() == clean(r.get("name")).casefold()})
    def summary(selected):
        return {"candidates": len(selected), "matched": sum(r["status"] == "matched" for r in selected),
            "with_sector": sum(r["sector_present"] for r in selected),
            "with_dated_sector_observation": sum(r["dated_sector_observation"] for r in selected),
            "with_industry": sum(r["industry_present"] for r in selected),
            "statuses": dict(Counter(r["status"] for r in selected))}
    return {"quality": {"rows": len(rows), "columns": columns,
        "missing_columns": [f for f in FIELDS if f not in columns],
        "fields": {f: {"present": f in columns,
            "missing": sum(missing(r.get(f), f) for r in rows),
            "missing_rate": sum(missing(r.get(f), f) for r in rows) / len(rows) if rows else None}
            for f in FIELDS},
        "rows_without_supported_venue": unsupported,
        "venue_attribution": "csv_column" if "Exchange" in columns else "documented_export_filter" if export_venue else "unavailable",
        "listing_rows_by_venue": dict(Counter(k[1] for k, values in keyed.items() for _ in values)),
        "duplicate_or_alias_collision_keys": sum(len(v) > 1 for v in keyed.values()),
        "market_cap_invalid_or_nonpositive": sum(not missing(r.get("Market Cap"), "Market Cap")
            and not positive_cap(r["Market Cap"]) for r in rows),
        "native_sector_counts": dict(Counter(r.get("Sector", "") for r in rows if not missing(r.get("Sector"), "Sector")))},
        "groups": {"all_us": summary(matches), **{g: summary([r for r in matches if r["symbol"] in symbols]) for g, symbols in groups.items()}},
        "candidates": matches}


def build_report(csv_path, manifest_path, data_dir=ROOT / "data", synthetic=False, now=None):
    now = now or datetime.now(timezone.utc)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    check_permission(manifest, now)  # Before opening any external CSV.
    if manifest.get("dataset_kind") != ("synthetic" if synthetic else "nasdaq_manual_csv"):
        raise ValueError("Dataset kind and explicit synthetic mode must agree")
    path = csv_path.resolve(strict=True) if synthetic else outside_git(csv_path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if manifest.get("csv_sha256") != digest:
        raise ValueError("Permission/provenance manifest must bind this exact CSV hash")
    headers, columns, rows = read_table(raw)
    with (data_dir / "stock_universe_candidates.csv").open(encoding="utf-8-sig", newline="") as stream:
        registry = [r for r in csv.DictReader(stream) if r["exchange"] in ("NAS", "NYS", "AMS")]
    baseline, _ = saved_baseline(json.loads(BASELINE.read_text(encoding="utf-8")),
                                 json.loads(EXPANSION.read_text(encoding="utf-8")))
    batch = json.loads(BATCH.read_text(encoding="utf-8"))
    groups = {"saved_baseline": set(baseline),
              "saved_conditional": set(batch["proposal_only_otherwise_ready_symbols"])}
    result = inspect_rows(rows, columns, registry, groups, manifest)
    return {"schema_version": 1, "mode": "synthetic" if synthetic else "authorized_local_file_review",
        "network_requests": 0, "downloads_performed": 0,
        "real_files_reviewed": 0 if synthetic else 1,
        "csv_sha256": digest, "csv_bytes": len(raw), "original_headers": headers,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "permission": "user-declared; not independently authenticated; no redistribution grant inferred",
        "downloaded_at_utc": manifest["downloaded_at_utc"], "source_as_of": manifest.get("source_as_of"),
        "source_as_of_reference": manifest.get("source_as_of_reference"),
        "source_url": manifest["source_url"], "evaluated_at_utc": now.isoformat(),
        "cohorts": "saved PR215 membership, not a current price/Stage readiness replay",
        "registry_sha256": hashlib.sha256((data_dir / "stock_universe_candidates.csv").read_bytes()).hexdigest(),
        "saved_batch_sha256": hashlib.sha256(BATCH.read_bytes()).hexdigest(),
        "cohort_files_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASELINE, EXPANSION)},
        **result, "sector_etf_mappings_validated": 0, "new_stage_eligible": 0,
        "stage_labels_recomputed": 0, "operational_additions": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    try:
        report = build_report(args.csv, args.manifest, args.data_dir, args.synthetic)
    except (ValueError, OSError, csv.Error, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
