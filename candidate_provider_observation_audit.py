"""Convert candidate KIS price-response observations into a cautious audit table."""
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
        try:
            response_rows = max(0, int(item.get("response_rows", 0) or 0))
        except (TypeError, ValueError, OverflowError):
            response_rows = 0
        rows.append({
            "symbol": str(item.get("symbol", "")).strip().upper(),
            "requested_exchange": requested,
            "response_exchange": returned,
            "exchange_fallback_used": bool(requested and returned and requested != returned),
            "response_rows": response_rows,
            "latest_response_date": item.get("latest_response_date", ""),
            "observation_scope": item.get("observation_scope", "price_response_only_not_identity_verification"),
            # A successful price response is positive operational evidence, but it does
            # not prove official instrument mapping or durable provider support.
            "provider_support_status": (
                "price_response_observed_formal_support_unverified"
                if response_rows > 0 else "no_price_response_observed"
            ),
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
    if not report.empty:
        print("provider_support_status_counts=" + json.dumps(report["provider_support_status"].value_counts().to_dict(), sort_keys=True))
    print("instrument_identity_status=not_verified; activation_recommendation=keep_pending_review")
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
