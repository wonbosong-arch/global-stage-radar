"""Manual Nasdaq CSV -> private, offline US review; never an activation payload.

Nasdaq is the sole native sector/industry source. ETF assignments are explicit
research proxies, not a GICS conversion. KIS supplies listing identity and prices.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import pandas as pd

from nasdaq_local_csv_review import clean, missing, venue, aliases_from, read_table
from stock_mapping import proposed_stock_mapping
from us_kis_evidence_readiness import assess_candidates
from us_sector_mapping_batch import BASELINE, EXPANSION, saved_baseline, evaluate_new_rows
from us_stage_connection_plan import MAPPING, OfflineStageReplay
from us_stage_mapping_expansion import INPUTS, fingerprint, baseline_input_match

ROOT = Path(__file__).resolve().parent
POLICY_VERSION = "nasdaq-native-11-proxies-v2"
# Exact native Sector + Industry allowlists. Unlisted pairs are review-only.
# A label alone cannot justify converting Nasdaq's taxonomy to an ETF taxonomy.
RULES = {
    "Finance": ("Financials", "XLF", """Accident &Health Insurance|Banks|Commercial Banks|Diversified Financial Services|Finance Companies|Finance/Investors Services|Finance: Consumer Services|Investment Bankers/Brokers/Service|Investment Managers|Life Insurance|Major Banks|Property-Casualty Insurers|Savings Institutions|Specialty Insurers"""),
    "Technology": ("Information Technology", "XLK", """Computer Manufacturing|Computer Software: Programming Data Processing|Computer peripheral equipment|Electronic Components|Retail: Computer Software & Peripheral Equipment|Semiconductors"""),
    "Health Care": ("Health Care", "XLV", """Medicinal Chemicals and Botanical Products|Biotechnology: Biological Products (No Diagnostic Substances)|Biotechnology: Commercial Physical & Biological Resarch|Biotechnology: Electromedical & Electrotherapeutic Apparatus|Biotechnology: In Vitro & In Vivo Diagnostic Substances|Biotechnology: Pharmaceutical Preparations|Hospital/Nursing Management|Managed Health Care|Medical Electronics|Medical Specialities|Medical/Dental Instruments|Medical/Nursing Services|Misc Health and Biotechnology Services|Ophthalmic Goods|Other Pharmaceuticals|Pharmaceuticals and Biotechnology|Precision Instruments"""),
    "Industrials": ("Industrials", "XLI", """Aerospace|Construction/Ag Equipment/Trucks|Diversified Commercial Services|Electrical Products|Engineering & Construction|Environmental Services|Fluid Controls|Industrial Machinery/Components|Industrial Specialties|Integrated Freight & Logistics|Marine Transportation|Metal Fabrications|Military/Government/Technical|Misc Corporate Leasing Services|Office Equipment/Supplies/Services|Ordnance And Accessories|Other Transportation|Pollution Control Equipment|Railroads|Trucking Freight/Courier Services|Water Sewer Pipeline Comm & Power Line Construction"""),
    "Consumer Discretionary": ("Consumer Discretionary", "XLY", """Apparel|Auto & Home Supply Stores|Auto Parts:O.E.M.|Automotive Aftermarket|Catalog/Specialty Distribution|Clothing/Shoe/Accessory Stores|Consumer Electronics/Appliances|Consumer Electronics/Video Chains|Home Furnishings|Homebuilding|Hotels/Resorts|Motor Vehicles|Other Specialty Stores|RETAIL: Building Materials|Recreational Games/Products/Toys|Rental/Leasing Companies|Restaurants|Retail-Auto Dealers and Gas Stations|Services-Misc. Amusement & Recreation|Shoe Manufacturing|Textiles|Tools/Hardware"""),
    "Consumer Staples": ("Consumer Staples", "XLP", """Beverages (Production/Distribution)|Farming/Seeds/Milling|Food Chains|Meat/Poultry/Fish|Packaged Foods|Retail-Drug Stores and Proprietary Stores|Specialty Foods"""),
    "Energy": ("Energy", "XLE", """Coal Mining|Integrated oil Companies|Oil & Gas Production|Oil Refining/Marketing|Oilfield Services/Equipment"""),
    "Utilities": ("Utilities", "XLU", """Electric Utilities: Central|Natural Gas Distribution|Power Generation|Water Supply"""),
    "Real Estate": ("Real Estate", "XLRE", """Building operators|Real Estate"""),
    "Basic Materials": ("Materials", "XLB", """Forest Products|Major Chemicals|Metal Mining|Other Metals and Minerals|Paper|Precious Metals"""),
    "Telecommunications": ("Communication Services", "XLC", "Cable & Other Pay Television Services"),
}
# Industry-specific exceptions remain rules over Nasdaq data, never ticker lists.
OVERRIDES = {
    ("Industrials", "Auto Manufacturing"): ("Consumer Discretionary", "XLY"),
    # Narrow product industries can cross Nasdaq's broad native sector buckets.
    # These remain exact pairs, with all identity and existing-proxy guards.
    **{("Industrials", industry): ("Materials", "XLB") for industry in (
        "Major Chemicals", "Agricultural Chemicals", "Specialty Chemicals",
        "Steel/Iron Ore", "Aluminum", "Precious Metals",
        "Mining & Quarrying of Nonmetallic Minerals (No Fuels)",
        "Containers/Packaging")},
    **{("Consumer Discretionary", industry): ("Materials", "XLB") for industry in (
        "Containers/Packaging", "Paints/Coatings", "Specialty Chemicals")},
    **{("Industrials", industry): ("Consumer Discretionary", "XLY") for industry in (
        "Garments and Clothing", "Home Furnishings", "Homebuilding")},
    ("Real Estate", "Homebuilding"): ("Consumer Discretionary", "XLY"),
    ("Consumer Discretionary", "Oil and Gas Field Machinery"): ("Energy", "XLE"),
    **{("Consumer Discretionary", industry): ("Consumer Staples", "XLP") for industry in (
        "Food Distributors", "Package Goods/Cosmetics")},
    ("Consumer Discretionary", "Department/Specialty Retail Stores"): ("Consumer Discretionary", "XLY"),
}
# REITs can include mortgage REITs; software/EDP can include media/gaming;
# telecom equipment can be hardware. These broad industries need review.


def proxy_for(row):
    sector, industry = clean(row.get("Sector")), clean(row.get("Industry"))
    if missing(sector, "Sector") or missing(industry, "Industry"):
        return None, "native_classification_missing"
    if (sector, industry) in OVERRIDES:
        return OVERRIDES[sector, industry], "explicit_industry_override"
    rule = RULES.get(sector)
    if rule and industry in rule[2].split("|"):
        return rule[:2], "explicit_sector_industry_rule"
    return None, "industry_proxy_review_required"


LEGAL = {"inc", "incorporated", "corp", "corporation", "co", "company", "plc", "ltd", "limited", "the"}
DESCRIPTORS = {"common", "ordinary", "stock", "stocks", "share", "shares", "capital", "subordinate", "voting", "non", "par", "value", "of", "each", "new", "reit"}


def name_tokens(value):
    ascii_name = unicodedata.normalize("NFKD", clean(value)).encode("ascii", "ignore").decode().lower()
    ascii_name = re.sub(r"\bclass\s+[a-z]\b", " ", ascii_name)
    ascii_name = ascii_name.replace("'", "").replace("\u2019", "")
    ascii_name = ascii_name.replace("&", " and ")
    return [t for t in re.findall(r"[a-z0-9]+", ascii_name) if t not in LEGAL | DESCRIPTORS and not t.isdigit()]


def name_basis(kis_names, csv_name):
    """Conservative exact token / bounded KIS truncation match; no fuzzy scores."""
    target = name_tokens(csv_name)
    if not target:
        return None
    for value in kis_names:
        source = name_tokens(value)
        if not source:
            continue
        if source == target:
            return "normalized_issuer_tokens"
        # KIS master names may be truncated; require >=2 tokens and >=10
        # distinctive characters, or a single long exact issuer token.
        if (len(source) <= len(target) and target[:len(source)] == source
                and sum(map(len, source)) >= 10 and (len(source) >= 2 or len(source[0]) >= 10)):
            return "bounded_kis_name_prefix"
    return None


def native_security_conflict(row, symbol, registry):
    name = clean(row.get("Name")).upper()
    # No stripping ^ / class suffixes or converting preferred/common/warrants.
    non_common = r"\b(?:PREFERRED|PREFERENCE|WARRANTS?|RIGHTS|DEBENTURES?|NOTES DUE|ETF|ETN|UNITS)\b"
    if "^" in symbol or re.search(non_common, name):
        return "source_non_common_security_signal"
    if (re.search(r"\b(?:ADR|ADS|AMERICAN DEPOSITARY)\b", name)
            and registry.get("depositary_ratio_status") != "verified"):
        return "source_adr_ratio_unconfirmed"
    source_class = re.search(r"\bCLASS\s+([A-Z])\b", name)
    kis_class = re.search(r"\bCLASS\s+([A-Z])\b", clean(registry.get("name")).upper())
    suffix = re.fullmatch(r"[A-Z0-9]+[./-]([A-Z])", symbol)
    expected = suffix.group(1) if suffix else kis_class.group(1) if kis_class else None
    if source_class and expected and source_class.group(1) != expected:
        return "source_share_class_conflict"
    return None


def mapping_packets(rows, columns, registry, master, universe, manifest):
    """Unique symbol join; absent source Exchange stays absent, KIS venue is used.

    Duplicates at either side and alias collisions never select a first row.
    KIS checks are necessary in addition to native issuer-name/type consistency.
    """
    required = {"Symbol", "Name", "Sector", "Industry", "Market Cap"}
    if not required.issubset(columns) or not rows:
        raise ValueError("Nonempty screener CSV requires Symbol/Name/Sector/Industry/Market Cap")
    registry = registry[registry.exchange.isin(["NAS", "NYS", "AMS"])].copy()
    registry["symbol"] = registry.symbol.map(lambda s: clean(s).upper())
    if registry.symbol.eq("").any() or registry.symbol.duplicated().any():
        raise ValueError("US registry requires unique nonempty symbols across venues")
    identities = {r["symbol"]: r for r in assess_candidates(registry, master, {})}
    aliases = aliases_from(manifest)
    keyed = defaultdict(list)
    for number, source in enumerate(rows, 2):
        symbol = clean(source.get("Symbol")).upper()
        # Alias requires the known KIS venue; source venue remains unclaimed.
        targets = {t for (s, _), t in aliases.items() if s == symbol}
        if len(targets) > 1:
            raise ValueError("Alias source has multiple targets")
        target = next(iter(targets)) if targets else symbol
        keyed[target].append((number, source, symbol))
    master_names = defaultdict(list)
    for r in master.to_dict("records"):
        master_names[clean(r.get("symbol")).upper()].append(clean(r.get("english_name")))
    packets = []
    for r in registry.to_dict("records"):
        symbol, v = r["symbol"], r["exchange"]
        proposed = proposed_stock_mapping(symbol, v, clean(r.get("discovery_dr_country_code")))
        existing = {k: proposed["proposed_" + k] for k in MAPPING}
        reasons, identity_reasons = [], []
        found = keyed.get(symbol, [])
        native, source_symbol, number, basis = {}, None, None, None
        if len(found) != 1:
            identity_reasons.append("symbol_absent" if not found else "duplicate_or_alias_collision")
        else:
            number, native, source_symbol = found[0]
            if source_symbol != symbol and aliases.get((source_symbol, v)) != symbol:
                identity_reasons.append("alias_venue_conflict")
            if "Exchange" in columns and venue(native.get("Exchange")) != v:
                identity_reasons.append("source_venue_conflict_or_unknown")
            basis = name_basis([r.get("name"), *master_names[symbol]], native.get("Name"))
            if not basis:
                identity_reasons.append("source_issuer_name_review_required")
            conflict = native_security_conflict(native, source_symbol, r)
            if conflict:
                identity_reasons.append(conflict)
        if identities[symbol]["identity_basis"] != "kis_master_consistent":
            identity_reasons.append("kis_identity_review_required")
        reasons.extend(identity_reasons)
        proxy, rule = proxy_for(native)
        mapping = None
        if not proxy:
            reasons.append(rule)
        else:
            sector, etf = proxy
            for sf, ef in (("sector", "sector_benchmark"), ("proposed_sector", "proposed_sector_benchmark")):
                if (clean(r.get(sf)) and clean(r.get(sf)) != sector) or (clean(r.get(ef)) and clean(r.get(ef)) != etf):
                    reasons.append("stored_proxy_conflict")
            if (existing["sector"] and existing["sector"] != sector) or (existing["sector_benchmark"] and existing["sector_benchmark"] != etf):
                reasons.append("curated_proxy_conflict")
            metadata = universe[universe.symbol.eq(etf)]
            if (len(metadata) != 1 or clean(metadata.iloc[0].get("sector")) != sector
                    or clean(metadata.iloc[0].get("asset_type")) != "sector_etf"
                    or clean(metadata.iloc[0].get("provider")) != "KIS"
                    or clean(metadata.iloc[0].get("active")).lower() != "true"):
                reasons.append("sector_etf_metadata_conflict")
            if not reasons:
                mapping = {**existing, "sector": sector, "sector_benchmark": etf}
        packets.append({"symbol": symbol, "venue": v, "kis_recorded_name": r.get("name"),
            "csv_row": number, "source_symbol": source_symbol, "source_name": native.get("Name"),
            "native_sector": native.get("Sector"), "native_industry": native.get("Industry"),
            "source_venue_verified": len(found) == 1 and "Exchange" in columns and venue(native.get("Exchange")) == v,
            "venue_basis": "KIS stored listing identity", "issuer_name_basis": basis,
            "identity_join_pass": not identity_reasons, "identity_join_reasons": identity_reasons,
            "native_classification_join_pass": not identity_reasons and all(not missing(native.get(f), f) for f in ("Sector", "Industry")),
            "proxy_rule": rule, "proposed_proxy": list(proxy) if proxy else None,
            "existing_proposal": existing, "batch_mapping": mapping,
            "mapping_class": "nasdaq_single_source_review" if mapping else "review_only_withheld",
            "mapping_reasons": sorted(set(reasons)), "operational_approval_granted": False})
    return packets


def check_local_manifest(manifest, digest, now):
    """Record user's supplied-file instruction, never fabricate a license/date."""
    provenance = (manifest.get("dataset_kind"), manifest.get("acquisition_method"))
    if (provenance not in {("user_supplied_nasdaq_csv", "user_manual_download"),
                           ("official_nasdaq_screener_csv", "official_ui_download")}
            or manifest.get("scope") != "private_noncommercial_offline"
            or not clean(manifest.get("user_instruction_reference"))
            or manifest.get("csv_sha256") != digest):
        raise ValueError("Hash-bound supplied-file provenance and private offline instruction required")
    if provenance[1] == "official_ui_download" and (
            not manifest.get("downloaded_at_utc") or
            manifest.get("download_control") != "Download CSV"):
        raise ValueError("Official UI acquisition requires download time and control evidence")
    if manifest.get("source_url") != "https://www.nasdaq.com/market-activity/stocks/screener":
        raise ValueError("Expected Nasdaq screener source")
    for key in ("source_as_of", "downloaded_at_utc"):
        value = manifest.get(key)
        if value is None:
            continue
        if not clean(manifest.get(key + "_reference")):
            raise ValueError("Dates require their own evidence reference")
        if key == "source_as_of":
            if date.fromisoformat(value) > now.date():
                raise ValueError("Future source date")
        else:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0 or stamp > now:
                raise ValueError("Download date requires nonfuture UTC")


def private_path(path, existing=True):
    resolved = path.resolve(strict=existing)
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("Private inputs/outputs must be outside source directory")
    if any((p / ".git").exists() for p in (resolved.parent, *resolved.parents)):
        raise ValueError("Private inputs/outputs must be outside every Git checkout")
    return resolved


def trend_inputs(replay, symbol):
    """Price-only diagnostics remain available when the sector proxy is held."""
    w = replay.weekly.get(symbol)
    result = {"valid_daily_rows": replay.daily.get(symbol, 0),
              "completed_weeks": len(w) if w is not None else 0,
              "latest_session": str(replay.latest[symbol].date()) if symbol in replay.latest else None,
              "as_of": str(replay.as_of.date()),
              "stage_label": None, "sector_proxy_used": False}
    if w is not None and len(w) >= 35:
        last = w.iloc[-1]
        if pd.notna(last.ma30) and pd.notna(last.slope4_pct):
            result.update(close=float(last.close), ma30=float(last.ma30), slope4_pct=float(last.slope4_pct),
                          above_ma30=bool(last.close > last.ma30))
    return result


def build_report(csv_path, manifest_path, data_dir, as_of, now=None):
    now = now or datetime.now(timezone.utc)
    date.fromisoformat(as_of)
    if date.fromisoformat(as_of) > now.date():
        raise ValueError("Future evaluation date")
    source = private_path(csv_path)
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(private_path(manifest_path).read_text(encoding="utf-8-sig"))
    check_local_manifest(manifest, digest, now)
    if manifest.get("source_as_of") and manifest["source_as_of"] > as_of:
        raise ValueError("Source classification date follows evaluation date")
    headers, columns, rows = read_table(raw)
    read = lambda n: pd.read_csv(data_dir / n, dtype=str, keep_default_na=False)
    registry, master, universe = read(INPUTS[0]), read(INPUTS[1]), read(INPUTS[3])
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    expansion = json.loads(EXPANSION.read_text(encoding="utf-8"))
    saved, historical_labels = saved_baseline(baseline, expansion)
    packets = mapping_packets(rows, columns, registry, master, universe, manifest)
    if not set(saved).issubset({p["symbol"] for p in packets}):
        raise ValueError("Saved baseline absent from registry")
    prices = pd.concat([read("daily_prices.csv"), read("candidate_daily_prices.csv")], ignore_index=True)
    observations = read(INPUTS[2]).to_dict("records")
    evaluated = evaluate_new_rows(packets, registry, master, observations, universe, prices, as_of, set(saved))
    # Compare all 85 on the SAME current snapshot/evaluation date, using their
    # saved mapping, independently of whether today's Nasdaq proxy agrees.
    saved_rows = {r["symbol"]: r for r in baseline["candidates"]}
    saved_rows.update({r["symbol"]: r for r in expansion["candidates"] if r["offline_review_eligible"]})
    original = []
    for p in packets:
        if p["symbol"] not in saved:
            continue
        s = saved_rows[p["symbol"]]
        mapping = {**p["existing_proposal"], **s.get("proposed_mapping", {}),
                   **{k: s[k] for k in MAPPING if k in s}}
        original.append({**p, "batch_mapping": mapping, "mapping_reasons": []})
    rerun85 = evaluate_new_rows(original, registry, master, observations, universe, prices, as_of, set())
    own_replay = OfflineStageReplay(prices[prices.symbol.isin([p["symbol"] for p in packets])], as_of)
    for p in evaluated:
        p["independent_price_trend"] = trend_inputs(own_replay, p["symbol"])
    eligible = [p for p in evaluated if p["offline_review_eligible"]]
    def counts(rr):
        return dict(Counter(p["review_only_stage_label"] for p in rr if p["offline_review_eligible"]))
    baseline_eligible = [p for p in rerun85 if p["offline_review_eligible"]]
    quality = {"rows": len(rows), "columns": columns,
        "duplicate_symbol_keys": sum(v > 1 for v in Counter(clean(r["Symbol"]).upper() for r in rows).values()),
        "missing": {f: sum(missing(r.get(f), f) for r in rows) for f in ("Symbol", "Name", "Sector", "Industry", "Market Cap")}}
    same_saved_snapshot = as_of == baseline["as_of"] and all(baseline_input_match(data_dir / n, baseline["input_files"][n]) != "different" for n in INPUTS)
    return {"schema_version": 1, "mode": "private_offline_review_only", "policy_version": POLICY_VERSION,
        "as_of": as_of, "evaluated_at_utc": now.isoformat(), "csv_sha256": digest,
        "csv_bytes": len(raw), "original_headers": headers, "quality": quality,
        "source_url": manifest["source_url"], "source_as_of": manifest.get("source_as_of"),
        "downloaded_at_utc": manifest.get("downloaded_at_utc"),
        "provenance": "hash-bound private analysis instruction; acquisition method retained in manifest",
        "acquisition_method": manifest["acquisition_method"],
        "source_exchange_column": "Exchange" in columns, "native_taxonomy_is_gics": False,
        "input_files": {n: fingerprint(data_dir / n) for n in INPUTS},
        "implementation_files": {n: fingerprint(ROOT / n) for n in ("nasdaq_single_source.py", "nasdaq_local_csv_review.py", "us_sector_mapping_batch.py", "stage_engine.py", "us_stage_connection_plan.py", "us_kis_evidence_readiness.py", "stock_mapping.py")},
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "historical_baseline": {"count": len(saved), "stage_counts": historical_labels,
            "same_snapshot": same_saved_snapshot, "labels_preserved": True},
        "same_date_baseline": {"count": len(rerun85), "eligible_count": len(baseline_eligible), "stage_counts": counts(rerun85), "rows": rerun85},
        "counts": {"candidates": len(packets), "unique_symbol_matches": sum(p["csv_row"] is not None for p in packets),
            "identity_join_pass": sum(p["identity_join_pass"] for p in packets),
            "native_classification_join_pass": sum(p["native_classification_join_pass"] for p in packets),
            "proxy_mapping_pass": sum(p["batch_mapping"] is not None for p in packets),
            "additional_eligible": len(eligible), "additional_stage_counts": counts(evaluated),
            "combined_same_date_stage_counts": dict(Counter(counts(rerun85)) + Counter(counts(evaluated))),
            "combined_same_date_eligible": len(baseline_eligible) + len(eligible)},
        "additional_blocker_counts": dict(Counter(reason for p in evaluated if p["symbol"] not in saved for reason in p["blocking_reasons"])),
        "candidates": evaluated, "operational_additions": 0, "network_requests": 0,
        "collection_performed": False, "monthly_refresh": "offline replay of " + manifest["acquisition_method"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path, required=True, help="Private JSON outside every Git checkout")
    args = parser.parse_args()
    try:
        output = private_path(args.output, existing=False)
        if output.exists() or output.resolve() in {args.csv.resolve(), args.manifest.resolve()}:
            raise ValueError("Output must be a new private file")
        report = build_report(args.csv, args.manifest, args.data_dir, args.as_of)
        # Exclusive create prevents an accidental overwrite on a concurrent run.
        with output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
    except (ValueError, OSError, KeyError, csv.Error) as exc:
        parser.error(str(exc))
    print(json.dumps({"output": str(output), "counts": report["counts"], "operational_additions": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
