"""Reviewed end of trading for specific KIS US stock identities."""
from datetime import date
from typing import NamedTuple


class ListingEnd(NamedTuple):
    name: str
    effective: date
    status: str
    source_url: str
    successor: str = ""


LISTING_ENDS = {
    ("NYS", "ACA"): ListingEnd(
        "ARCOSA INC", date(2026, 10, 23), "listing_ended",
        "https://www.sec.gov/Archives/edgar/data/876661/000087666126000858/ruleprovisionnotice.htm",
    ),
    ("NYS", "ACVA"): ListingEnd(
        "ACV AUCTIONS INC", date(2026, 10, 16), "listing_ended",
        "https://www.sec.gov/Archives/edgar/data/876661/000087666126000841/ruleprovisionnotice.htm",
    ),
    ("NYS", "ATKR"): ListingEnd(
        "ATKORE INC", date(2026, 10, 19), "listing_ended",
        "https://www.sec.gov/Archives/edgar/data/1666138/000166613826000041/atkr-20261019.htm",
    ),
    ("NAS", "PSKY"): ListingEnd(
        "PARAMOUNT SKYDANCE CORP", date(2026, 10, 6), "listing_transferred",
        "https://ir.paramount.com/static-files/7794ee1d-aac9-40d1-8d9b-9716b2cab799",
        "NYS:SKYD",
    ),
    ("NAS", "WBD"): ListingEnd(
        "WARNER BROS DISCOVERY INC", date(2026, 10, 6), "listing_ended",
        "https://www.sec.gov/Archives/edgar/data/1437107/000119312526415055/d200872d8k.htm",
    ),
}


def reviewed_listing_end(symbol, exchange, name, asset_type, session_date):
    """Match the reviewed stock identity; a reused ticker alone is insufficient."""
    event = LISTING_ENDS.get((str(exchange).strip().upper(), str(symbol).strip().upper()))
    if (event and str(asset_type).strip().lower() == "stock"
            and str(name).strip().upper() == event.name and session_date >= event.effective):
        return event
    return None
