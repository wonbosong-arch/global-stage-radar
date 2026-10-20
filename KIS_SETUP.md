# KIS API setup — private US-stock pilot

## 1. Keep credentials private

Never paste your App Key or App Secret into ChatGPT, an issue, a commit, or a public file.

### Local run
Create `.streamlit/secrets.toml` in your local project folder (do not commit it):

```toml
KIS_APP_KEY = "paste-your-app-key-locally"
KIS_APP_SECRET = "paste-your-app-secret-locally"
```

If you prefer environment variables, set `KIS_APP_KEY` and `KIS_APP_SECRET` in your shell.

### Streamlit Community Cloud
Open the deployed app's **Settings → Secrets** and add the same TOML entries. Do not put secrets in GitHub repository files. The public source code should contain no credentials.

## 2. Use a small US watchlist first

In the sidebar choose **KIS API · 미국주식**, upload a CSV based on `data/universe_template.csv`, and press **KIS에서 가격 조회**.

Required columns:
- `symbol`: US ticker, e.g. AAPL
- `name`, `market`, `sector`, `asset_type`
- `market_cap_usd`: current estimate in USD; blank values are excluded from the stock screen
- `market_benchmark`, `sector_benchmark`: tickers that also need to be present as rows in the CSV
- `exchange`: KIS market code — `NAS` (Nasdaq), `NYS` (NYSE), or `AMS` (NYSE American). If omitted, the app assumes `NAS`; check each symbol's exchange before use.

All benchmark symbols must also be in the uploaded CSV so the app can fetch their price histories. The included template is an illustrative starter list, not a maintained market universe. Its sector labels and market caps are examples and should be checked before relying on results.

## 3. Pilot limitations

- This is an early integration of the KIS overseas daily-price endpoint, not a validated global data platform.
- Start with 3–10 symbols and benchmarks. Larger universes may hit API rate limits and take time to load.
- The app fetches price history only. It does not automatically retrieve or verify market cap, sector classification, delisted tickers, historical membership, or benchmark mappings.
- The app requests the adjusted-price option exposed by the KIS daily-price API; independently verify corporate-action behavior and the returned history before using signals.
- The Stage 2 labels are screening heuristics, not validated trading signals.
- API access does not itself prove a right to publicly display or redistribute market data. Confirm KIS's current terms for the intended private/hosted use. Do not make the live-data app public until those rights and data coverage are confirmed.
- Paper-trading credentials/hosts may not provide the same quote data as the live API. The current app uses the live host for market-data queries.

## Official references

- [KIS Developers API documentation](https://apiportal.koreainvestment.com/docs)
- [KIS API service introduction](https://apiportal.koreainvestment.com/intro)
- [KIS official sample code repository](https://github.com/koreainvestment/open-trading-api)
