# Global Stage Radar

A weekly Stage Analysis screening MVP built with Streamlit. It supports CSV input, clearly labeled synthetic demo data, and a KIS REST API mode for Korean-listed instruments plus US-listed stocks/ETFs. The default monitoring universe uses US-listed ETFs as proxies for global markets, sectors, and commodities where a direct KIS series is not available. The integration is an early pilot; verify symbol support, adjustment quality, request limits and usage terms.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Modes

- **가상 데모**: synthetic prices only; never use as real market information.
- **CSV 업로드**: upload daily OHLCV data and a matching symbol universe file.
- **KIS API · 미국·한국**: uses `data/monitoring_universe.csv` by default, or accepts a custom universe CSV. Fetches KRX-listed Korean instruments and US-listed stocks/ETFs through KIS. US-listed ETFs can represent exposures to Canada, Europe, the United Kingdom, Germany, France, Switzerland, Japan, South Korea, Taiwan, Hong Kong, India, China, Singapore, Indonesia, South Africa, Brazil, Australia, Mexico, US sectors, and commodities. The starter roster includes a global-market benchmark (ACWI), global sector ETF proxies alongside US-sector ETFs, Korean sector ETFs, commodity proxies for platinum, corn, wheat, and soybeans, plus BTC and ETH. Country-sector coverage outside the US and Korea remains proxy-based where local sector series are not available; global-sector ETFs are not presented as country-specific sectors. Proxy availability and price-history completeness are reported separately from roster membership. Use `NAS`, `NYS`, or `AMS` for US listings, `KRX` for Korean listings, and `CRYPTO` for BTC/ETH. Configure `KIS_APP_KEY` and `KIS_APP_SECRET` in Streamlit secrets or environment variables.

CSV templates are in `data/`. Price history should include each stock and the benchmarks it references. Minimum history is 35 completed weekly bars; longer history is recommended. The universe template also shows optional global metadata columns such as country, currency, timezone, provider, and metadata provenance.

## Screening logic (initial, not validated as a trading strategy)

- Exchange-listed assets use Friday-ending weekly bars; BTC/ETH use Sunday-ending weekly bars because crypto trades 24/7. The current incomplete week is excluded.
- 30-week simple moving average (SMA) and its four-week percentage slope.
- Relative performance is calculated as the asset's 26-week return minus the benchmark's 26-week return, in percentage points. This is **not** a full Mansfield RS calculation.
- **Stocks** are Stage 2 candidates when close is above SMA30, the SMA slope is positive, and 26-week relative performance is positive versus both market and sector benchmarks.
- **ETFs, commodity ETFs, commodity spot/futures series, and crypto assets** do not need a sector-relative series. BTC is trend-screened against its own 30-week trend; ETH relative performance is measured against BTC. Commodity ETFs and commodity price series are distinct instrument types.
- Stage 2A watch is an internal screening label, not an official Weinstein stage label.

Market capitalization is a stock-only filter; ETFs and other market/sector proxy instruments are exempt. A stock is excluded by the $1B threshold only when its market cap is verified to be below $1B USD. Missing or unverified market cap is a pending-review state, not an automatic pass or exclusion. Candidate discovery does not activate stocks automatically: identity, provider support, market cap, benchmark/sector mapping, and activation require review. For KRX candidates, USD conversion remains unresolved unless a current USD_KRW_RATE is configured.

### Market-cap source policy

Yahoo Finance is useful as a **manual secondary cross-check**, but it is not the default automated market-cap feed for this public dashboard. Yahoo's own Finance help says displayed data is for informational purposes and must not be redistributed; the community `yfinance` package is unofficial and its documentation says the Yahoo Finance API is intended for personal use. Do not scrape Yahoo market caps into the public repository or republish those values in the app unless the applicable Yahoo terms or a separate data licence explicitly permits that use.

Use this order for the $1B stock filter:
1. **Primary / broker source:** KIS market-cap data where supported, subject to confirming public-display rights and the field's meaning.
2. **Exchange or issuer source:** preferred for country-specific gaps and resolving instrument/share-class questions.
3. **Licensed secondary provider:** use when its licence permits storage and public display.
4. **Yahoo Finance:** manual plausibility check only, recorded as an unverified observation if used during review; never enough by itself to verify market cap, auto-exclude a stock, or activate a candidate.

The threshold remains conservative: exclude a stock only when its USD market cap is verified below $1B. If sources disagree, the observation is stale, an ADR/share-class basis is unclear, or the cap is missing, keep the candidate pending. ETFs and market/sector proxies remain exempt from the stock-only threshold.


## KIS API pilot

See [KIS_SETUP.md](KIS_SETUP.md) for credential setup and pilot limitations. The app does not store credentials in the repository. The current integration fetches daily prices from KIS for supported US/KRX listings; BTC and ETH use a separate Coinbase Exchange public-candles adapter and a separate scheduled snapshot, never the KIS stock endpoint. The crypto refresh runs at 09:15 KST Tuesday-Saturday so the prior UTC daily candle is complete; this differs from the 07:00 KST KIS snapshot schedule (Monday-Saturday; Sunday skipped). International market and commodity coverage is represented by listed ETF proxies, not direct local-index or spot/futures series. Confirm Coinbase API terms and hosting/display rights before public live use. It does not automatically validate market capitalization, sector classifications, benchmark assignments, each ETF's availability at your broker, or public display rights. Start with a small symbol list to avoid request-limit issues. KRX support has unit tests but still needs live API verification.

## Data rights and quality

- KIS US/Korea adapters are implemented for small-watchlist private research, but no provider is approved for public live display yet.
- An API key or free quota does not automatically permit public display or redistribution.
- Read [DATA_PROVIDER_VALIDATION.md](DATA_PROVIDER_VALIDATION.md) before adding a source.
- Never commit API keys or the KIS-mode password to the repository. The hosted KIS mode requires an `APP_PASSWORD` secret before it can use KIS credentials; see [KIS_SETUP.md](KIS_SETUP.md).

## Tests

Pure Stage calculations are in `stage_engine.py`; universe validation is in `universe.py`; normalized OHLCV checks are in `market_data.py`. Tests are under `tests/`. GitHub Actions runs unit tests and Python syntax checks on relevant pushes and pull requests.

See [GLOBAL_EXPANSION_PLAN.md](GLOBAL_EXPANSION_PLAN.md) for the phased route to global markets and all target asset classes. [data/sector_coverage_matrix.csv](data/sector_coverage_matrix.csv) records which markets currently have local sector ETFs in the roster and which only have global-sector fallback proxies. [data/country_sector_proxy_candidates.csv](data/country_sector_proxy_candidates.csv) tracks evidence-backed country-sector ETF candidates and provider blockers. Coverage depends on an approved data source, not only on the dashboard code.

## Deploy

Streamlit Community Cloud can deploy this repository and `app.py`; the current branch is suitable for a demo only. Follow the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). Public live market data should remain disabled until provider rights, data quality, and deployment access controls are confirmed.

This is a research screener, not investment advice. The rules are not backtested or proven profitable.
