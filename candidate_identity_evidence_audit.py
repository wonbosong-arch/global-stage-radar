"""Conservative metadata-evidence coverage audit for pending stock candidates.

This script reports which review fields are populated. It does not verify sources,
infer instrument identity, validate market capitalization, or activate candidates.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "data" / "stock_universe_candidates.csv"
DEFAULT_OUTPUT = ROOT / "data" / "candidate_identity_evidence_coverage.csv"


def build_report(candidates: pd.DataFrame) -> pd.DataFrame:
    frame = candidates.copy()
    for column in (
        "symbol", "name", "exchange", "country", "instrument_type",
        "identity_status", "identity_evidence_url", "identity_reviewed_at",
        "market_cap_status", "market_cap_source_url", "market_cap_asof",
        "market_cap_usd_b_secondary", "depositary_ratio_status",
        "provider_status", "activation_status",
    ):
        if column not in frame.columns:
            frame[column] = ""

    def present(series: pd.Series) -> pd.Series:
        return series.fillna("").astype(str).str.strip().ne("")

    frame["identity_source_url_present"] = present(frame["identity_evidence_url"])
    frame["identity_review_date_present"] = present(frame["identity_reviewed_at"])
    frame["listing_fields_present"] = (
        present(frame["symbol"]) & present(frame["name"]) &
        present(frame["exchange"]) & present(frame["country"]) &
        present(frame["instrument_type"])
    )
    frame["secondary_market_cap_source_present"] = present(frame["market_cap_source_url"])
    frame["secondary_market_cap_date_present"] = present(frame["market_cap_asof"])
    frame["secondary_market_cap_value_present"] = present(frame["market_cap_usd_b_secondary"])
    frame["market_cap_marked_verified"] = frame["market_cap_status"].astype(str).str.strip().eq("verified")
    frame["provider_marked_checked"] = ~frame["provider_status"].astype(str).str.strip().isin(["", "not_checked"])
    frame["still_pending"] = frame["activation_status"].astype(str).str.strip().eq("pending_review")

    frame["review_gaps"] = frame.apply(
        lambda row: ";".join(
            label for label, ok in (
                ("identity_source_url_missing", row["identity_source_url_present"]),
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
        "identity_status", "identity_source_url_present", "identity_review_date_present",
        "listing_fields_present", "market_cap_status", "secondary_market_cap_source_present",
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
