# Global Stage Analysis Radar

A weekly Stage Analysis screening MVP built with Streamlit. It supports CSV input, clearly labeled synthetic demo data, and an initial KIS REST API mode for small US/Korea stock and ETF watchlists. The KIS mode is an early personal-research pilot; verify current API coverage, adjustment quality, request limits and usage terms before expanding it.

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
- **KIS API · 미국주식**: upload a small watchlist/universe CSV and fetch US or Korea daily bars through KIS. Add an `exchange` column (`NAS`, `NYS`, or `AMS`); missing values default to `NAS`. Configure `KIS_APP_KEY` and `KIS_APP_SECRET` in Streamlit secrets or environment variables.

CSV templates are in `data/`. Price history should include each stock and the benchmarks it references. Minimum history is 35 completed weekly bars; longer history is recommended. The universe template also shows optional global metadata columns such as country, currency, timezone, provider, and metadata provenance.

## Screening logic (initial, not validated as a trading strategy)

- Daily OHLCV is resampled to Friday-ending weekly bars.
- 30-week simple moving average (SMA) and its four-week percentage slope.
- Relative performance is calculated as the asset's 26-week return minus the benchmark's 26-week return, in percentage points. This is **not** a full Mansfield RS calculation.
- **Stocks** are Stage 2 candidates when close is above SMA30, the SMA slope is positive, and 26-week relative performance is positive versus both market and sector benchmarks.
- **ETFs and commodity series** are compared against the market benchmark; they do not need a sector-relative series.
- Stage 2A watch is an internal screening label, not an official Weinstein stage label.

Market capitalization is filtered only for stocks. Missing market cap is excluded from the stock screen. Input market cap must already be in USD; currency conversion and stale market-cap checks are not automated.

## KIS API pilot

See [KIS_SETUP.md](KIS_SETUP.md) for credential setup and pilot limitations. The app does not store credentials in the repository. The current integration fetches US/Korea prices only; it does not automatically validate market capitalization, sector classifications, benchmark assignments, or public display rights. Start with a small symbol list to avoid request-limit issues. KRX support has unit tests but still needs live API verification.

## Data rights and quality

- No live market data provider is configured.
- An API key or free quota does not automatically permit public display or redistribution.
- Read [DATA_PROVIDER_VALIDATION.md](DATA_PROVIDER_VALIDATION.md) before adding a source.
- Never commit API keys or the KIS-mode password to the repository. The hosted KIS mode requires an `APP_PASSWORD` secret before it can use KIS credentials; see [KIS_SETUP.md](KIS_SETUP.md).

## Tests

Pure Stage calculations are in `stage_engine.py`; universe validation is in `universe.py`; normalized OHLCV checks are in `market_data.py`. Tests are under `tests/`. GitHub Actions runs unit tests and Python syntax checks on relevant pushes and pull requests.

See [GLOBAL_EXPANSION_PLAN.md](GLOBAL_EXPANSION_PLAN.md) for the phased route to global markets and all target asset classes. Coverage depends on an approved data source, not only on the dashboard code.

## Deploy

Streamlit Community Cloud can deploy this repository and `app.py`; the current branch is suitable for a demo only. Follow the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). Live market data is not available until a provider is separately vetted and integrated.

This is a research screener, not investment advice. The rules are not backtested or proven profitable.
