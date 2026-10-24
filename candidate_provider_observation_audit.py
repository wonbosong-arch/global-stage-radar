"""Convert the latest candidate KIS price-response observations into a cautious audit table."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DEFAULT_STATUS = ROOT / "data" / "candidate_daily_prices_status.json"
DEFAULT_OUTPUT = ROOT / "data" / "candidate_provider_observation_audit.csv"


def build_report(status: dict) -> pd.DataFrame:
    rows = []
    observations = status.get("provider_observations", [])
    for item in observations:
        requested = str(item.get("requested_exchange", "")).strip().upper()
        returned = str(item.get("response_exchange", "")).strip().upper()
        rows.append({
            "symbol": str(item.get("symbol", "")).strip().upper(),
            "requested_exchange": requested,
            "response_exchange": returned,
            "exchange_fallback_used": bool(requested and returned and requested != returned),
            "response_rows": item.get("response_rows", 0),
            "latest_response_date": item.get("latest_response_date", ""),
            "observation_scope": item.get("observation_scope", "price_response_only_not_identity_verification"),
            "provider_support_status": "not_verified",
            "instrument_identity_status": "not_verified",
            "activation_recommendation": "keep_pending_review",
        })
    columns = [
        "symbol", "requested_exchange", "response_exchange", "exchange_fallback_used",
        "response_rows", "latest_response_date", "observation_scope",
        "provider_support_status", "instrument_identity_status", "activation_recommendation",
    ]
    return pd.DataFrame(rows, columns=columns).sort_values("symbol").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.status.exists():
        status = json.loads(args.status.read_text(encoding="utf-8"))
    else:
        status = {}
    report = build_report(status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"rows={len(report)}")
    print(f"exchange_fallbacks={int(report['exchange_fallback_used'].sum()) if not report.empty else 0}")
    print("provider_support_status=not_verified; instrument_identity_status=not_verified")
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
