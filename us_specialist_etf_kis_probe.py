"""One-shot read-only KIS history check for six US specialist ETF candidates.

Never publishes OHLCV, adds ETF universe entries, changes Stage, or infers a
fund's exchange/issuer identity from a price response. This probe intentionally
uses the existing NYS KIS quotation route for a first observation. Absence of
prices under NYS does not mean KIS does not support the fund elsewhere.
Default invocation makes no API calls; --execute is mandatory for live use.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json

import pandas as pd

from candidate_refresh_state import classify_failure, validate_prices
from kis_provider import KISError, KISOverseasPrices
from market_data import completed_bar_cutoff_date
from stage_engine import weekly_bars

ETF_SYMBOLS = ("IGV", "XBI", "IYR", "KBE", "KIE", "JETS")
PROBE_VENUE = "NYS"  # Existing KIS US ETF quote route, NOT listing-identity evidence.
SYSTEMIC = frozenset({"rate_limited", "authentication_failed", "temporary_server_error"})


def observe_history(client, now: datetime, max_pages: int = 4, pause_seconds: float = 2.0):
    """A bounded batch reusing the existing KIS client, token and shared rate queue.

    Only normalized metadata leaves this function. No network fallback, full
    history, issuer identity or operational approval is saved or emitted.
    """
    if now.tzinfo is None or not 1 <= max_pages <= 5 or not 2 <= pause_seconds <= 30:
        raise ValueError("Timezone-aware evaluation, pages 1..5, pause 2..30 required")
    cutoff = pd.Timestamp(completed_bar_cutoff_date(PROBE_VENUE, now_kst=now))
    details = []
    stopped = ""
    for symbol in ETF_SYMBOLS:
        try:
            raw = client.daily_bars(
                symbol, exchange=PROBE_VENUE, max_pages=max_pages,
                pause_seconds=pause_seconds,
            )
            if raw.empty:
                details.append(dict(symbol=symbol, queried_venue=PROBE_VENUE,
                                    status="nys_price_empty_support_unknown",
                                    daily_rows=0, completed_weeks=0,
                                    latest_session=None, kis_instrument_identity_verified=False,
                                    analysis_activated=False))
                continue
            # Existing quality guards fail closed on OHLCV conflicts and ticker
            # mismatches; avoid treating a partially returned candle as final.
            clean = validate_prices(raw, symbol)
            clean["date"] = pd.to_datetime(clean["date"], errors="coerce")
            if clean["date"].isna().any():
                raise ValueError("Invalid KIS session date")
            clean = clean[clean["date"].le(cutoff)].copy()
            if clean.empty:
                details.append(dict(symbol=symbol, queried_venue=PROBE_VENUE,
                                    status="no_completed_sessions",
                                    daily_rows=0, completed_weeks=0,
                                    latest_session=None, kis_instrument_identity_verified=False,
                                    analysis_activated=False))
                continue
            weekly = weekly_bars(clean, as_of_date=cutoff, min_bars=1)
            count = len(weekly) if weekly is not None else 0
            latest = clean["date"].max().normalize()
            # KIS session freshness is a preliminary research check, not a
            # market-calendar guarantee or issuer identity validation.
            business_days = len(pd.bdate_range(latest, cutoff)) - 1
            status = ("price_history_sufficient_identity_unverified"
                      if len(clean) >= 150 and count >= 35 and business_days <= 5
                      else "price_history_short_or_stale_review")
            details.append(dict(symbol=symbol, queried_venue=PROBE_VENUE, status=status,
                                daily_rows=int(len(clean)), completed_weeks=int(count),
                                latest_session=latest.date().isoformat(),
                                kis_instrument_identity_verified=False,
                                analysis_activated=False))
        except (KISError, ValueError, KeyError, TypeError) as exc:
            kind = classify_failure(exc)
            details.append(dict(symbol=symbol, queried_venue=PROBE_VENUE,
                                status="kis_probe_error_" + kind, daily_rows=0,
                                completed_weeks=0, latest_session=None,
                                kis_instrument_identity_verified=False,
                                analysis_activated=False))
            if kind in SYSTEMIC:
                stopped = kind
                break
    return dict(source="KIS live quotation, NYS route only; issuer/venue identity unverified",
                attempted=len(details), requested=len(ETF_SYMBOLS),
                counts=dict(Counter(x["status"] for x in details)),
                stopped_early_reason=stopped or None,
                details=details, source_prices_saved=False, universe_updated=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-pages", type=int, default=4)
    parser.add_argument("--pause-seconds", type=float, default=2.0)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps(dict(mode="offline_plan_no_network",
                              symbols=list(ETF_SYMBOLS), proposed_quote_venue=PROBE_VENUE,
                              automatic_venue_fallback=False,
                              kis_identity_verified=False, source_prices_saved=False)))
        return
    report = observe_history(KISOverseasPrices(), datetime.now(timezone.utc),
                             args.max_pages, args.pause_seconds)
    # Logs contain only symbol and price-history counts, never OHLCV or secrets.
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
