"""USD cross rates for local ETF returns using ECB fixings via Frankfurter."""
from datetime import timedelta

from dateutil.easter import easter
import numpy as np
import pandas as pd
import requests

FX_FILE = "china_market_fx.csv"
CURRENCIES = ("CNY", "HKD")
COLUMNS = ["date", "currency", "usd_per_unit"]


def fixing_date(day):
    """Carry back only when the ECB is closed (TARGET closing calendar)."""
    while True:
        sunday = easter(day.year)
        closed = ((day.month, day.day) in {(1, 1), (5, 1), (12, 25), (12, 26)}
                  or day in {sunday - timedelta(days=2), sunday + timedelta(days=1)})
        if day.weekday() < 5 and not closed:
            return day
        day -= timedelta(days=1)


def validate_quotes(quotes):
    quotes = quotes[COLUMNS].copy()
    quotes["date"] = pd.to_datetime(quotes.date, format="%Y-%m-%d", errors="raise")
    quotes["usd_per_unit"] = pd.to_numeric(quotes.usd_per_unit, errors="raise")
    if (quotes.date.isna().any() or quotes.duplicated(["currency", "date"]).any()
            or not quotes.currency.isin(CURRENCIES).all()
            or not (np.isfinite(quotes.usd_per_unit) & quotes.usd_per_unit.gt(0)).all()):
        raise ValueError("Invalid FX observations")
    return quotes


def fetch_quotes(start, end, currencies):
    response = requests.get("https://api.frankfurter.dev/v2/rates", timeout=20, params={
        "base": "USD", "quotes": ",".join(currencies), "providers": "ECB",
        "from": start.isoformat(), "to": end.isoformat(),
    })
    response.raise_for_status()
    quotes = validate_quotes(pd.DataFrame([
        (row["date"], row["quote"], 1 / float(row["rate"]))
        for row in response.json() if row["base"] == "USD"
    ], columns=COLUMNS))
    return quotes.loc[quotes.currency.isin(currencies)
                      & quotes.date.between(pd.Timestamp(start), pd.Timestamp(end))]
