# KIS API setup — private US/Korea stock and ETF pilot

## 1. Keep credentials private

Never paste your App Key or App Secret into ChatGPT, an issue, a commit, or a public file.

### Local run
Create `.streamlit/secrets.toml` in your local project folder (do not commit it):

```toml
KIS_APP_KEY = "paste-your-app-key-locally"
KIS_APP_SECRET = "paste-your-app-secret-locally"
APP_PASSWORD = "choose-a-long-unique-password-locally"
```

If you prefer environment variables, set `KIS_APP_KEY` and `KIS_APP_SECRET` in your shell.

### Streamlit Community Cloud
Open the deployed app's **Settings → Secrets** and add the same TOML entries, including a strong unique `APP_PASSWORD`. The hosted URL may be accessible to anyone who knows it; the app now requires this password before using the KIS credentials. Never share the password in ChatGPT or commit it to GitHub. Do not put secrets in repository files.

## 2. Use the built-in monitoring universe or upload your own

In the sidebar choose **KIS API · 미국·한국**. The app loads `data/monitoring_universe.csv` automatically; press **KIS에서 가격 조회**. You may upload a custom CSV to replace the default list. The starter universe includes US-listed market ETFs for selected countries/regions, US sector ETFs, commodity ETFs, and a small KRX ETF sample. It is a starting point, not a complete or broker-verified universe.

Required columns:
- `symbol`: US ticker, e.g. AAPL
- `name`, `market`, `sector`, `asset_type`
- `market_cap_usd`: current estimate in USD; blank values are excluded from the stock screen
- `market_benchmark`, `sector_benchmark`: tickers that also need to be present as rows in the CSV
- `exchange`: KIS market code — `NAS` (Nasdaq), `NYS` (NYSE), or `AMS` (NYSE American). If omitted, the app assumes `NAS`; check each symbol's exchange before use.

All benchmark symbols must also be in the uploaded CSV so the app can fetch their price histories. The included template is an illustrative starter list, not a maintained market universe. Its sector labels and market caps are examples and should be checked before relying on results.

## 3. Pilot limitations

- This is an early integration of KIS US overseas and Korea domestic daily-price endpoints, not a validated global data platform. The Korea adapter has mocked unit tests but has not yet been verified against the live API.
- When a direct local-market index or commodity spot/futures series is unavailable, the starter universe uses a US-listed ETF as a proxy. ETF prices can differ from the underlying index/commodity because of fees, currency effects, futures roll, tracking error, and market hours.
- Start with 3–10 symbols and benchmarks. KIS Korea currently supports six-digit KRX symbols only. Larger universes may hit API rate limits and take time to load.
- The app fetches price history only. It does not automatically retrieve or verify market cap, sector classification, delisted tickers, historical membership, or benchmark mappings.
- The app requests the adjusted-price option exposed by the KIS daily-price API; independently verify corporate-action behavior and the returned history before using signals.
- The Stage 2 labels are screening heuristics, not validated trading signals.
- API access does not itself prove a right to publicly display or redistribute market data. Confirm KIS's current terms for the intended private/hosted use. Do not make the live-data app public until those rights and data coverage are confirmed.
- Paper-trading credentials/hosts may not provide the same quote data as the live API. The current app uses the live host for market-data queries.

## Official references

- [KIS Developers API documentation](https://apiportal.koreainvestment.com/docs)
- [KIS API service introduction](https://apiportal.koreainvestment.com/intro)
- [KIS official sample code repository](https://github.com/koreainvestment/open-trading-api)

## US market-cap ranking request discrepancy (2026-10-28)

The [official sample](https://github.com/koreainvestment/open-trading-api/blob/d8c7f7936793f85dc1e9c364ba5dc66832353f8c/examples_llm/overseas_stock/market_cap/market_cap.py)
for `HHDFS76350100` omits `CURR_GB`. Actual saved live observations disagree:

- At commit `0c8c9ce`, the request includes `CURR_GB="0"`. Its stored
  `data/candidate_collection_status.json` records successful NAS/NYS/AMS
  responses with `output1.curr="USD"`, 100 unique rows per exchange and no
  market errors. Page 2 repeats those rows and is explicitly marked stalled.
- At commit `928bc43`, the request omits that field. All three US exchanges
  fail with `OPSQ2001: ERROR INPUT FIELD NOT FOUND [CURR_GB]`; diagnostics
  confirm the sent parameter names exclude it.

The collector therefore retains the empirically accepted single-character `0`
selector. This fixes the observed request-schema regression; it does not prove
complete ranking pagination, market-cap units, instrument identity or activation
eligibility. Keep the repeated-page guard and review gates. A fresh live run is
required to confirm current server behavior after any request change.
