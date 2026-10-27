"""Conservative metadata-evidence coverage audit for pending stock candidates.

This script reports which review fields are populated. It does not verify sources,
infer instrument identity, validate market capitalization, or activate candidates.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from collect_stock_candidates import extract_adr_ratio_from_listing_name

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "data" / "stock_universe_candidates.csv"
DEFAULT_OUTPUT = ROOT / "data" / "candidate_identity_evidence_coverage.csv"
DEFAULT_RATIO_SOURCE_REGISTRY = ROOT / "data" / "adr_ratio_primary_source_registry.csv"
DEFAULT_ISSUER_EVIDENCE = ROOT / "data" / "issuer_country_evidence_review.csv"


def build_report(candidates: pd.DataFrame, ratio_sources: pd.DataFrame | None = None) -> pd.DataFrame:
    frame = candidates.copy()
    for column in (
        "symbol", "name", "exchange", "country", "instrument_type",
        "identity_status", "identity_evidence_url", "identity_reviewed_at",
        "market_cap_status", "market_cap_source_url", "market_cap_asof",
        "market_cap_usd_b_secondary", "depositary_ratio_status",
        "depositary_ratio_observed", "depositary_ratio_basis", "depositary_ratio_evidence_text",
        "depositary_ratio_source_url", "depositary_ratio_verified_at", "depositary_ratio_source_class",
        "provider_status", "activation_status",
    ):
        if column not in frame.columns:
            frame[column] = ""

    def present(series: pd.Series) -> pd.Series:
        return series.fillna("").astype(str).str.strip().ne("")

    # Apply explicitly curated issuer-primary-source ratio evidence separately from
    # broader identity, market-cap, provider, and activation verification.
    if ratio_sources is None:
        ratio_sources = (
            pd.read_csv(DEFAULT_RATIO_SOURCE_REGISTRY, dtype=str, keep_default_na=False)
            if DEFAULT_RATIO_SOURCE_REGISTRY.exists()
            else pd.DataFrame()
        )
    if not ratio_sources.empty and "symbol" in ratio_sources.columns:
        registry = ratio_sources.copy()
        registry["symbol"] = registry["symbol"].astype(str).str.strip().str.upper()
        if "status" in registry.columns:
            registry = registry[registry["status"].astype(str).str.strip().eq("official_source_confirmed")]
        registry = registry.drop_duplicates("symbol", keep="last").set_index("symbol")
        frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
        for column in (
            "depositary_ratio_observed", "depositary_ratio_basis",
            "depositary_ratio_source_url", "depositary_ratio_source_class",
            "depositary_ratio_evidence_text", "depositary_ratio_verified_at",
        ):
            source_column = {
                "depositary_ratio_verified_at": "reviewed_at",
            }.get(column, column)
            if source_column not in registry.columns:
                continue
            mapped = frame["symbol"].map(registry[source_column])
            has_source_value = mapped.fillna("").astype(str).str.strip().ne("")
            frame.loc[has_source_value, column] = mapped[has_source_value]
        source_confirmed = frame["symbol"].isin(registry.index) & frame["instrument_type"].astype(str).str.strip().eq("adr_candidate")
        frame.loc[source_confirmed, "depositary_ratio_status"] = "verified"

    # Recover a ratio explicitly stated in a listing label for the report only.
    # This is not an official source and must never count as ratio verification.
    parsed = frame["name"].map(extract_adr_ratio_from_listing_name)
    parsed_ratio = parsed.map(lambda item: item[0])
    parsed_basis = parsed.map(lambda item: item[1])
    is_adr = frame["instrument_type"].astype(str).str.strip().eq("adr_candidate")
    ratio_missing = ~present(frame["depositary_ratio_observed"])
    use_parsed = is_adr & ratio_missing & parsed_ratio.ne("")
    frame.loc[use_parsed, "depositary_ratio_observed"] = parsed_ratio[use_parsed]
    frame.loc[use_parsed, "depositary_ratio_basis"] = parsed_basis[use_parsed]
    frame.loc[use_parsed, "depositary_ratio_evidence_text"] = frame.loc[use_parsed, "name"]
    ratio_status_missing = ~present(frame["depositary_ratio_status"])
    frame.loc[use_parsed & ratio_status_missing, "depositary_ratio_status"] = (
        "listing_description_only_pending_primary_source"
    )

    frame["identity_source_url_present"] = present(frame["identity_evidence_url"])

    def source_class(value: object) -> str:
        url = str(value or "").strip()
        if not url:
            return "missing"
        host = urlparse(url).hostname
        if not host:
            return "invalid_or_unparsed_url"
        host = host.lower().removeprefix("www.")
        if host == "sec.gov" or host.endswith(".sec.gov"):
            return "regulatory_filing"
        if host in {"nasdaq.com", "nyse.com", "nyseamerican.com", "nysearca.com"} or host.endswith(".nasdaq.com") or host.endswith(".nyse.com"):
            return "exchange_domain"
        if host in {"stockanalysis.com", "stocktitan.net", "companiesmarketcap.com", "macrotrends.net"}:
            return "secondary_market_data"
        return "other_domain_requires_manual_classification"

    frame["identity_evidence_source_class"] = frame["identity_evidence_url"].map(source_class)
    frame["market_cap_source_class"] = frame["market_cap_source_url"].map(source_class)
    frame["identity_review_date_present"] = present(frame["identity_reviewed_at"])
    frame["listing_fields_present"] = (
        present(frame["symbol"]) & present(frame["name"]) &
        present(frame["exchange"]) & present(frame["country"]) &
        present(frame["instrument_type"])
    )
    frame["secondary_market_cap_source_present"] = present(frame["market_cap_source_url"])
    frame["secondary_market_cap_date_present"] = present(frame["market_cap_asof"])
    frame["secondary_market_cap_value_present"] = present(frame["market_cap_usd_b_secondary"])
    frame["identity_marked_verified"] = frame["identity_status"].astype(str).str.strip().eq("verified")
    frame["depositary_ratio_required"] = frame["instrument_type"].astype(str).str.strip().eq("adr_candidate")
    frame["depositary_ratio_verified"] = frame["depositary_ratio_status"].astype(str).str.strip().eq("verified")
    frame["market_cap_marked_verified"] = frame["market_cap_status"].astype(str).str.strip().eq("verified")
    frame["provider_marked_checked"] = ~frame["provider_status"].astype(str).str.strip().isin(["", "not_checked"])
    frame["still_pending"] = frame["activation_status"].astype(str).str.strip().eq("pending_review")

    frame["review_gaps"] = frame.apply(
        lambda row: ";".join(
            label for label, ok in (
                ("identity_source_url_missing", row["identity_source_url_present"]),
                ("identity_not_verified", row["identity_marked_verified"]),
                ("adr_ratio_not_verified", (not row["depositary_ratio_required"]) or row["depositary_ratio_verified"]),
                ("identity_review_date_missing", row["identity_review_date_present"]),
                ("listing_metadata_missing", row["listing_fields_present"]),
                ("market_cap_source_missing", row["secondary_market_cap_source_present"]),
                ("market_cap_asof_missing", row["secondary_market_cap_date_present"]),
                ("secondary_market_cap_value_missing", row["secondary_market_cap_value_present"]),
                ("market_cap_not_verified", row["market_cap_marked_verified"]),
                ("provider_not_checked", row["provider_marked_checked"]),
                ("not_pending_review", row["still_pending"]),
            ) if not ok
        ),
        axis=1,
    )
    columns = [
        "symbol", "name", "exchange", "country", "instrument_type",
        "identity_status", "identity_marked_verified", "identity_source_url_present", "identity_evidence_source_class", "identity_review_date_present",
        "depositary_ratio_required", "depositary_ratio_verified",
        "depositary_ratio_observed", "depositary_ratio_basis", "depositary_ratio_evidence_text",
        "depositary_ratio_source_url", "depositary_ratio_verified_at", "depositary_ratio_source_class",
        "listing_fields_present", "market_cap_status", "secondary_market_cap_source_present", "market_cap_source_class",
        "secondary_market_cap_date_present", "secondary_market_cap_value_present",
        "market_cap_marked_verified", "provider_status", "provider_marked_checked",
        "activation_status", "still_pending", "review_gaps",
    ]
    return frame[columns].sort_values(["still_pending", "symbol"], ascending=[False, True])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    candidates = pd.read_csv(args.input, dtype=str, keep_default_na=False)
    report = build_report(candidates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"rows={len(report)}")
    print(f"identity_source_url_present={int(report['identity_source_url_present'].sum())}/{len(report)}")
    print(f"identity_review_date_present={int(report['identity_review_date_present'].sum())}/{len(report)}")
    print(f"market_cap_marked_verified={int(report['market_cap_marked_verified'].sum())}/{len(report)}")
    print(f"provider_marked_checked={int(report['provider_marked_checked'].sum())}/{len(report)}")
    print(f"still_pending={int(report['still_pending'].sum())}/{len(report)}")
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
