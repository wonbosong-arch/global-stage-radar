"""One-shot read-only KIS history check for six US specialist ETF candidates.

Never publishes OHLCV, adds ETF universe entries, changes Stage, or infers a
fund's exchange/issuer identity from a price response. This probe first used the NYS KIS quotation route. An explicit AMS second
observation checks only five independently documented NYSE Arca-listed funds.
A price response never proves the listing exchange or the fund's identity.
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
# Official exchange evidence: SPDR (XBI/KBE/KIE), iShares (IYR), SEC (JETS).
# IGV is listed on Cboe BZX, so must NOT be inferred to trade on NYSE Arca.
# These are independent listing facts, NOT a claim that KIS maps Arca to AMS.
# https://www.sec.gov/Archives/edgar/data/1064642/000119312526432200/d147434dex99ei3.htm
# https://www.ishares.com/us/products/239520/IYR
# https://www.sec.gov/Archives/edgar/data/1540305/000089418926013955/jetssummary.htm
# https://www.cboe.com/us/equities/listings/listed_products/symbols/IGV/
ARCA_ETF_SYMBOLS = ("XBI", "IYR", "KBE", "KIE", "JETS")
PROBE_VENUE = "NYS"  # Existing KIS US ETF quote route, NOT listing-identity evidence.
SYSTEMIC = frozenset({"rate_limited", "authentication_failed", "temporary_server_error"})


def observe_history(client, now: datetime, max_pages: int = 4, pause_seconds: float = 2.0,
                    *, venue: str = PROBE_VENUE, symbols=None):
    """A bounded batch reusing the existing KIS client, token and shared rate queue.

    Only normalized metadata leaves this function. No network fallback, full
    history, issuer identity or operational approval is saved or emitted.
    """
    if now.tzinfo is None or not 1 <= max_pages <= 5 or not 2 <= pause_seconds <= 30:
        raise ValueError("Timezone-aware evaluation, pages 1..5, pause 2..30 required")
    if venue not in {"NYS", "AMS"}:
        raise ValueError("Only the explicitly scoped NYS and AMS KIS routes are supported")
    # The CLI retains its fixed cohorts. Read-only workflows may pass their
    # independently identified symbols with an explicit quotation venue.
    if symbols is None:
        symbols = ETF_SYMBOLS if venue == "NYS" else ARCA_ETF_SYMBOLS
    cutoff = pd.Timestamp(completed_bar_cutoff_date(venue, now_kst=now))
    details = []
    stopped = ""
    for symbol in symbols:
        try:
            raw = client.daily_bars(
                symbol, exchange=venue, max_pages=max_pages,
                pause_seconds=pause_seconds,
            )
            if raw.empty:
                details.append(dict(symbol=symbol, queried_venue=venue,
                                    status=f"{venue.lower()}_price_empty_support_unknown",
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
                details.append(dict(symbol=symbol, queried_venue=venue,
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
            details.append(dict(symbol=symbol, queried_venue=venue, status=status,
                                daily_rows=int(len(clean)), completed_weeks=int(count),
                                latest_session=latest.date().isoformat(),
                                kis_instrument_identity_verified=False,
                                analysis_activated=False))
        except (KISError, ValueError, KeyError, TypeError) as exc:
            kind = classify_failure(exc)
            details.append(dict(symbol=symbol, queried_venue=venue,
                                status="kis_probe_error_" + kind, daily_rows=0,
                                completed_weeks=0, latest_session=None,
                                kis_instrument_identity_verified=False,
                                analysis_activated=False))
            if kind in SYSTEMIC:
                stopped = kind
                break
    return dict(source=f"KIS live quotation, {venue} route only; issuer/venue identity unverified",
                attempted=len(details), requested=len(symbols),
                counts=dict(Counter(x["status"] for x in details)),
                stopped_early_reason=stopped or None,
                details=details, source_prices_saved=False, universe_updated=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-pages", type=int, default=4)
    parser.add_argument("--pause-seconds", type=float, default=2.0)
    parser.add_argument("--venue", choices=("NYS", "AMS"), default=PROBE_VENUE)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps(dict(mode="offline_plan_no_network",
                              symbols=list(ETF_SYMBOLS if args.venue == "NYS" else ARCA_ETF_SYMBOLS),
                              proposed_quote_venue=args.venue,
                              automatic_venue_fallback=False,
                              kis_identity_verified=False, source_prices_saved=False)))
        return
    report = observe_history(KISOverseasPrices(), datetime.now(timezone.utc),
                             args.max_pages, args.pause_seconds, venue=args.venue)
    # Logs contain only symbol and price-history counts, never OHLCV or secrets.
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
