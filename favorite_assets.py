"""Browser-scoped asset bookmarks; independent of Stage eligibility and providers."""
from __future__ import annotations
from datetime import datetime, timezone
import math
import re

import pandas as pd


def _text(value):
    if value is None or value is pd.NA or value is pd.NaT:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value)


def asset_id(row):
    symbol = _text(row.get("symbol", "")).strip().upper()
    exchange = _text(row.get("exchange", "")).strip().upper()
    # Demo/custom CSV instruments without a venue remain distinct from listed assets.
    venue = exchange if exchange not in {"", "NAN", "NONE"} else "UNSPECIFIED"
    return f"{venue}:{symbol}"


def asset_area(row):
    kind = _text(row.get("asset_type_norm")) or _text(row.get("asset_type", ""))
    kind = kind.lower()
    return "stocks" if kind == "stock" else "sectors" if kind == "sector_etf" else "markets_commodities"


def bookmark(row, added_at=None):
    result = {field: _text(row.get(field, ""))[:240] for field in
              ("symbol", "exchange", "name", "market", "sector", "last_daily_date", "last_date")}
    result.update(id=asset_id(row), area=asset_area(row),
                  asset_type_norm=_text(row.get("asset_type_norm")) or _text(row.get("asset_type", "")),
                  added_at=added_at or datetime.now(timezone.utc).isoformat())
    try:
        ret = float(row.get("ret26_pct"))
        result["ret26_pct"] = ret if math.isfinite(ret) else None
    except (TypeError, ValueError):
        result["ret26_pct"] = None
    return result


def decode_bookmarks(value):
    """Validate client storage without accepting HTML, secrets or executable fields."""
    if not isinstance(value, list) or len(value) > 5000:
        return []
    result, seen = [], set()
    for row in value:
        if not isinstance(row, dict):
            continue
        symbol = row.get("symbol", "")
        exchange = row.get("exchange", "")
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z0-9._/-]{1,40}", symbol):
            continue
        if not isinstance(exchange, str) or not re.fullmatch(r"[A-Za-z0-9._-]{0,40}", exchange):
            continue
        clean = bookmark(row, str(row.get("added_at", ""))[:50])
        if clean["id"] not in seen:
            seen.add(clean["id"])
            result.append(clean)
    return result


def merge_bookmarks(stored, current, removed=()):
    by_id = {row["id"]: row for row in decode_bookmarks(stored)}
    for row in decode_bookmarks(current):
        by_id[row["id"]] = row
    return [row for key, row in by_id.items() if key not in removed]


def watchlist_frame(records, catalog, area="전체", sort="26주 절대 수익률순"):
    current = {asset_id(row): row for _, row in catalog.iterrows()}
    ambiguous = {str(row["symbol"]) for _, row in catalog.iterrows()
                 if len({asset_id(r) for _, r in catalog[catalog.symbol.eq(row["symbol"])].iterrows()}) > 1}
    rows = []
    for saved in decode_bookmarks(records):
        row = dict(saved)
        live = current.get(saved["id"])
        if live is not None:
            row.update(live.to_dict())
        row["id"] = saved["id"]
        row["added_at"] = saved["added_at"]
        row["area"] = saved["area"]
        # Legacy OHLCV snapshots are keyed by symbol alone. Never display a
        # different listing's prices when two venues share that symbol.
        row["price_available"] = live is not None and str(row["symbol"]) not in ambiguous
        rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    areas = {"국가·원자재": "markets_commodities", "업종": "sectors", "종목": "stocks"}
    if area in areas:
        frame = frame[frame.area.eq(areas[area])]
    if sort == "이름순":
        frame = frame.sort_values("name", key=lambda values: values.str.casefold(), kind="stable")
    elif sort == "관심 등록순":
        frame = frame.sort_values("added_at", kind="stable")
    else:
        frame["ret26_pct"] = pd.to_numeric(frame["ret26_pct"], errors="coerce")
        frame = frame.sort_values("ret26_pct", ascending=False, na_position="last", kind="stable")
    return frame.reset_index(drop=True)
