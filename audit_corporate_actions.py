"""Live, read-only KIS split-adjustment sanity audit.

This checks price continuity across two known stock splits using the adapters'
documented adjusted-price request flags. It is not an independent price-source
reconciliation and does not test dividend-adjusted total returns.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

import pandas as pd

from kis_provider import KISOverseasPrices
from kis_domestic_provider import KISDomesticPrices


def split_continuity_report(
    frame: pd.DataFrame,
    split_date: str,
    symbol: str,
    event_name: str,
    ratio_min: float = 0.5,
    ratio_max: float = 2.0,
) -> dict[str, Any]:
    """Compare nearest available close before and on/after a split date."""
    if frame is None or frame.empty or not {"date", "close"}.issubset(frame.columns):
        return {"symbol": symbol, "event": event_name, "status": "FAIL", "reason": "empty or invalid price frame"}
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.normalize()
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    data = data.dropna(subset=["date", "close"]).sort_values("date")
    event = pd.Timestamp(split_date)
    before = data.loc[data["date"] < event].tail(1)
    after = data.loc[data["date"] >= event].head(1)
    if before.empty or after.empty:
        return {
            "symbol": symbol, "event": event_name, "split_date": split_date,
            "status": "FAIL", "reason": "no close on both sides of event",
            "rows_returned": int(len(data)),
        }
    pre = float(before.iloc[0]["close"])
    post = float(after.iloc[0]["close"])
    ratio = post / pre if pre else float("nan")
    passed = pd.notna(ratio) and ratio_min <= ratio <= ratio_max
    return {
        "symbol": symbol,
        "event": event_name,
        "split_date": split_date,
        "status": "PASS" if passed else "FAIL",
        "pre_event_date": before.iloc[0]["date"].strftime("%Y-%m-%d"),
        "pre_event_close": pre,
        "post_event_date": after.iloc[0]["date"].strftime("%Y-%m-%d"),
        "post_event_close": post,
        "post_pre_close_ratio": round(ratio, 6) if pd.notna(ratio) else None,
        "accepted_ratio_range": [ratio_min, ratio_max],
        "rows_returned": int(len(data)),
        "note": "Continuity sanity check only; not independent-source validation.",
    }


def main() -> int:
    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")
    if not app_key or not app_secret:
        print("FAIL: KIS_APP_KEY and KIS_APP_SECRET are required.", file=sys.stderr)
        return 2

    reports: list[dict[str, Any]] = []
    try:
        overseas = KISOverseasPrices(app_key=app_key, app_secret=app_secret, paper=False)
        # NVIDIA's 10-for-1 split became effective 2024-06-10.
        nvda = overseas.daily_bars("NVDA", exchange="NAS", end_date="20240612", max_pages=3)
        reports.append(split_continuity_report(nvda, "2024-06-10", "NVDA", "10-for-1 split"))

        domestic = KISDomesticPrices(app_key=app_key, app_secret=app_secret, paper=False)
        # Samsung Electronics' 50-for-1 split became effective 2018-05-04.
        samsung = domestic.domestic_daily_bars("005930", exchange="KRX", end_date="20180508", max_pages=3)
        reports.append(split_continuity_report(samsung, "2018-05-04", "005930", "50-for-1 split"))
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:500]}, ensure_ascii=False))
        return 1

    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0 if all(report.get("status") == "PASS" for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
