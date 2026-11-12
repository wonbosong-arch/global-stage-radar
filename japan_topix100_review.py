"""Offline, rights-gated JPX-listed-issues sector audit (no network or API use).

No JPX source or derived per-stock results may be written inside this repository.
The tool does not alter the market data, Stage engine, ETFs or dashboard.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import date
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[1]
OFFICIAL_SOURCE = "https://www.jpx.co.jp/english/markets/statistics-equities/misc/01.html"
TAXONOMY_SOURCE = "https://www.jpx.co.jp/english/markets/indices/factsheets/files/e_000_fac2_sector.pdf"
ETF_SOURCE = "https://nextfunds.jp/lineup/"
# Group order equals TOPIX-17 codes 1..17, confirmed against JPX taxonomy.
# Only public industry classification definitions are hard-coded, never stock records.
GROUPS = {
    1: ("FOODS", "0050 3050"),
    2: ("ENERGY RESOURCES", "1050 3300"),
    3: ("CONSTRUCTION & MATERIALS", "2050 3400 3550"),
    4: ("RAW MATERIALS & CHEMICALS", "3100 3150 3200"),
    5: ("PHARMACEUTICAL", "3250"),
    6: ("AUTOMOBILES & TRANSPORTATION EQUIPMENT", "3350 3700"),
    7: ("STEEL & NONFERROUS METALS", "3450 3500"),
    8: ("MACHINERY", "3600"),
    9: ("ELECTRIC APPLIANCES & PRECISION INSTRUMENTS", "3650 3750"),
    10: ("IT & SERVICES, OTHERS", "3800 5250 9050"),
    11: ("ELECTRIC POWER & GAS", "4050"),
    12: ("TRANSPORTATION & LOGISTICS", "5050 5100 5150 5200"),
    13: ("COMMERCIAL & WHOLESALE TRADE", "6050"),
    14: ("RETAIL TRADE", "6100"),
    15: ("BANKS", "7050"),
    16: ("FINANCIALS (EX BANKS)", "7100 7150 7200"),
    17: ("REAL ESTATE", "8050"),
}
SECTOR_TO_GROUP = {code: group for group, (_, codes) in GROUPS.items() for code in codes.split()}
assert len(SECTOR_TO_GROUP) == 33 and set(GROUPS) == set(range(1, 18))

COLUMNS = (
    "Effective Date", "Local Code", "Name (English)", "Section/Products",
    "33 Sector(Code)", "33 Sector(name)", "17 Sector(Code)", "17 Sector(name)",
    "Size Code (New Index Series)", "Size (New Index Series)",
)
OUTPUT_COLUMNS = (
    "local_code", "company_name", "exchange", "size_group", "sector33_code",
    "sector33_name", "sector17_code", "sector17_name", "sector_etf",
    "mapping_kind", "sector_crosswalk_status", "review_status", "review_reasons",
    "as_of", "source_url", "taxonomy_url", "etf_source_url",
)


def safe_outside_repo(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == REPO or REPO in resolved.parents:
        raise ValueError("private_jpx_files_must_be_outside_checkout")
    return resolved


def load_rows(path: Path) -> list[dict[str, str]]:
    """Read the official English CSV/XLSX schema without modifying input."""
    safe_outside_repo(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("invalid_input_file")
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None or not set(COLUMNS).issubset(reader.fieldnames):
                raise ValueError("missing_jpx_columns")
            return [{key: str(value or "").strip() for key, value in row.items()} for row in reader]
    if path.suffix.lower() != ".xlsx":
        raise ValueError("use_english_jpx_csv_or_xlsx")
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ValueError("openpyxl_required_for_xlsx") from None
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = workbook.active
        raw = ws.iter_rows(values_only=True)
        headers = [str(cell).strip() if cell is not None else "" for cell in next(raw)]
        if not set(COLUMNS).issubset(headers):
            raise ValueError("missing_jpx_columns")
        result = []
        for values in raw:
            record = {headers[i]: str(cell).strip() if cell is not None else ""
                      for i, cell in enumerate(values) if i < len(headers)}
            if record.get("Local Code"):
                result.append(record)
        return result
    finally:
        workbook.close()


def norm_code(value: str, *, width: int = 0) -> str:
    value = str(value).strip()
    if re.fullmatch(r"\d+(\.0)?", value):
        value = value.split(".")[0]
        if width:
            value = value.zfill(width)
    return value.upper()


def normalized_date(raw: str) -> str:
    raw = str(raw).strip().split(".")[0]
    if re.fullmatch(r"\d{8}", raw):
        year, month, day = int(raw[:4]), int(raw[4:6]), int(raw[6:8])
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        year, month, day = map(int, raw.split("-"))
    else:
        raise ValueError("invalid_effective_date")
    return date(year, month, day).isoformat()


def size_group(record: dict[str, str]) -> str:
    name = str(record.get("Size (New Index Series)", "")).upper()
    if re.search(r"CORE\s*30\b", name):
        return "Core30"
    if re.search(r"LARGE\s*70\b", name):
        return "Large70"
    return ""


def read_reference(path: Path | None) -> dict[str, str] | None:
    if path is None:
        return None
    safe_outside_repo(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"local_code", "company_name"}.issubset(reader.fieldnames or []):
            raise ValueError("invalid_reference_headers")
        mapping = {}
        for record in reader:
            code = norm_code(record["local_code"])
            name = (record["company_name"] or "").strip()
            if not code or code in mapping or not name:
                raise ValueError("invalid_reference_identity")
            mapping[code] = name
        return mapping


def review(rows: list[dict[str, str]], *, expected_date: str,
           identities: dict[str, str] | None = None,
           selection: str = "topix100", reference_url: str = "",
           reference_as_of: str = "", input_source_url: str = "") -> tuple[list[dict[str, str]], dict]:
    """Strict 100-index check, optional explicitly labelled non-index fallback."""
    if selection not in {"topix100", "prime100_fallback"}:
        raise ValueError("invalid_selection")
    expected_date = normalized_date(expected_date)
    if selection == "topix100":
        chosen = [row for row in rows if size_group(row)]
    else:
        chosen = sorted(
            [row for row in rows if "PRIME" in row.get("Section/Products", "").upper()
             and "DOMESTIC" in row.get("Section/Products", "").upper()
             and norm_code(row.get("33 Sector(Code)", ""), width=4) in SECTOR_TO_GROUP],
            key=lambda row: norm_code(row["Local Code"]),
        )[:100]
    groups = [size_group(row) for row in chosen]
    counts = {g: groups.count(g) for g in ("Core30", "Large70")}
    confirmed_index = (
        selection == "topix100" and len(chosen) == 100
        and counts == {"Core30": 30, "Large70": 70}
        and len({norm_code(row.get("Local Code", "")) for row in chosen}) == 100
    )
    observed_code_names: dict[str, str] = {}
    out = []
    for item in chosen:
        code = norm_code(item.get("Local Code", ""))
        name = item.get("Name (English)", "").strip()
        c33 = norm_code(item.get("33 Sector(Code)", ""), width=4)
        c17 = norm_code(item.get("17 Sector(Code)", ""))
        if c17.isdigit():
            c17 = str(int(c17))
        group = SECTOR_TO_GROUP.get(c33)
        reasons = []
        if not re.fullmatch(r"[0-9A-Z]{4}", code):
            reasons.append("invalid_or_missing_symbol")
        if not name or name in {"-", "N/A"}:
            reasons.append("missing_company_name")
        if name.startswith(("=", "+", "-", "@")):
            reasons.append("unsafe_spreadsheet_company_name")
        if code in observed_code_names:
            reasons.append("duplicate_symbol")
            if observed_code_names[code] != name:
                reasons.append("code_company_name_conflict")
        observed_code_names[code] = name
        if not item.get("33 Sector(name)") or item["33 Sector(name)"] == "-":
            reasons.append("missing_33_sector_name")
        if not item.get("17 Sector(name)") or item["17 Sector(name)"] == "-":
            reasons.append("missing_17_sector_name")
        if group is None:
            reasons.append("unknown_33_sector_code")
        elif c17 != str(group):
            reasons.append("33_to_17_mismatch")
        try:
            as_of = normalized_date(item.get("Effective Date", ""))
            if as_of != expected_date:
                reasons.append("source_date_mismatch")
        except (ValueError, OverflowError):
            as_of = ""
            reasons.append("missing_or_invalid_source_date")
        if input_source_url not in {
            OFFICIAL_SOURCE,
            "https://www.jpx.co.jp/english/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_e.xlsx",
        }:
            reasons.append("official_input_provenance_missing")
        if identities is None:
            reasons.append("independent_identity_check_missing")
        elif code not in identities:
            reasons.append("independent_identity_not_found")
        elif identities[code] != name:
            reasons.append("company_name_code_mismatch")
        if identities is not None:
            if not reference_url.startswith("https://"):
                reasons.append("identity_reference_source_missing")
            try:
                if normalized_date(reference_as_of) != expected_date:
                    reasons.append("identity_reference_date_mismatch")
            except (ValueError, OverflowError):
                reasons.append("identity_reference_date_missing")
        if selection == "topix100" and not confirmed_index:
            reasons.append("unconfirmed_topix100_constituents")
        if selection == "prime100_fallback":
            reasons.append("fallback_not_topix100")
        sector_ok = bool(group and "33_to_17_mismatch" not in reasons
                         and "missing_33_sector_name" not in reasons
                         and "missing_17_sector_name" not in reasons
                         and "source_date_mismatch" not in reasons
                         and "missing_or_invalid_source_date" not in reasons)
        out.append({
            "local_code": code, "company_name": ("'" + name if name.startswith(("=", "+", "-", "@")) else name),
            "exchange": "TSE", "size_group": size_group(item) if selection == "topix100" else "NOT_TOPIX100",
            "sector33_code": c33, "sector33_name": item.get("33 Sector(name)", ""),
            "sector17_code": c17, "sector17_name": item.get("17 Sector(name)", ""),
            "sector_etf": str(1616 + group) if sector_ok else "",
            "mapping_kind": "index_sector_proxy_not_confirmed_etf_holding",
            "sector_crosswalk_status": "confirmed" if sector_ok else "review_required",
            "review_status": "verified" if not reasons else "review_required",
            "review_reasons": "|".join(sorted(set(reasons))),
            "as_of": as_of, "source_url": OFFICIAL_SOURCE,
            "taxonomy_url": TAXONOMY_SOURCE, "etf_source_url": ETF_SOURCE,
        })
    summary = {
        "selection": selection,
        "sample_label": "TOPIX Core30+Large70" if confirmed_index else "UNCONFIRMED_INDEX_OR_FALLBACK",
        "expected_as_of": expected_date,
        "input_rows": len(rows),
        "selected_rows": len(out),
        "core30": counts["Core30"], "large70": counts["Large70"],
        "topix100_confirmed": confirmed_index,
        "sector_crosswalk_confirmed": sum(x["sector_crosswalk_status"] == "confirmed" for x in out),
        "verified": sum(x["review_status"] == "verified" for x in out),
        "review_required": sum(x["review_status"] == "review_required" for x in out),
        "classification_mismatch": sum("33_to_17_mismatch" in x["review_reasons"] for x in out),
        "identity_mismatch": sum("company_name_code_mismatch" in x["review_reasons"] or
                                 "code_company_name_conflict" in x["review_reasons"] for x in out),
        "exchange_trading_holdings_verified": 0,
        "operationally_active": 0,
        "source_url": input_source_url or "not_supplied",
        "source_provenance": "user_declared_not_cryptographically_authenticated",
        "identity_reference_url": reference_url or "not_supplied",
        "identity_reference_as_of": reference_as_of or "not_supplied",
        "disclaimer": "Private review only; index sector association is not ETF actual holdings.",
    }
    return out, summary


def write_private(output: Path, details: list[dict], summary: dict) -> None:
    destination = safe_outside_repo(output)
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / "japan_topix_sector_review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(details)
    (destination / "japan_topix_sector_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jpx-file", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--as-of", required=True, help="Official source effective date, e.g. 2026-10-31")
    ap.add_argument("--source-url", default="", help="Official URL of the authorized input file")
    ap.add_argument("--reference", type=Path, help="Independently validated code,name CSV")
    ap.add_argument("--reference-url", default="", help="Official independent identity reference URL")
    ap.add_argument("--reference-as-of", default="", help="Independent reference effective date")
    ap.add_argument("--selection", choices=("topix100", "prime100_fallback"), default="topix100")
    ap.add_argument("--authorized-use", action="store_true",
                    help="Affirm you hold rights for processing this JPX dataset")
    args = ap.parse_args(argv)
    if not args.authorized_use:
        ap.error("JPX commercial data processing requires confirmed usage rights; no file read")
    try:
        records = load_rows(args.jpx_file)
        reference = read_reference(args.reference)
        details, summary = review(records, expected_date=args.as_of,
                                  identities=reference, selection=args.selection,
                                  reference_url=args.reference_url,
                                  reference_as_of=args.reference_as_of,
                                  input_source_url=args.source_url)
        summary["input_sha256"] = hashlib.sha256(args.jpx_file.read_bytes()).hexdigest()
        write_private(args.out, details, summary)
    except (ValueError, OSError) as e:
        print("review_failed: " + str(e), file=sys.stderr)
        return 2
    print(json.dumps({k: summary[k] for k in ("selected_rows", "topix100_confirmed",
          "sector_crosswalk_confirmed", "verified", "review_required")}, ensure_ascii=False))
    return 0 if summary["topix100_confirmed"] and summary["review_required"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
