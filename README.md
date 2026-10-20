# Global Stage Analysis Radar

A weekly Stage Analysis screening MVP built with Streamlit. It supports CSV input and clearly labeled synthetic demo data. It intentionally does **not** fetch live prices yet: provider coverage, adjustment quality, licensing and redistribution permissions must be verified first.

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

CSV templates are in `data/`. Price history should include each stock and the benchmarks it references. Minimum history is 35 weekly bars; longer history is recommended.

## Screening logic (initial, not validated as a trading strategy)

- Daily OHLCV is resampled to Friday-ending weekly bars.
- 30-week simple moving average (SMA) and its four-week percentage slope.
- Relative performance is calculated as the asset's 26-week return minus the benchmark's 26-week return, in percentage points. This is **not** a full Mansfield RS calculation.
- **Stocks** are Stage 2 candidates when close is above SMA30, the SMA slope is positive, and 26-week relative performance is positive versus both market and sector benchmarks.
- **ETFs and commodity series** are compared against the market benchmark; they do not need a sector-relative series.
- Stage 2A watch is an internal screening label, not an official Weinstein stage label.

Market capitalization is filtered only for stocks. Missing market cap is excluded from the stock screen. Input market cap must already be in USD; currency conversion and stale market-cap checks are not automated.

## Data rights and quality

- No live market data provider is configured.
- An API key or free quota does not automatically permit public display or redistribution.
- Read [DATA_PROVIDER_VALIDATION.md](DATA_PROVIDER_VALIDATION.md) before adding a source.
- Never commit API keys to the repository. Use hosting secrets only after a provider is approved.

## Tests

Pure calculation helpers are in `stage_engine.py`; unit tests are in `tests/test_stage_engine.py`. GitHub Actions runs the tests and Python syntax checks on relevant pushes and pull requests.

## Deploy

Streamlit Community Cloud can deploy this repository and `app.py`; the current branch is suitable for a demo only. Follow the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). Live market data is not available until a provider is separately vetted and integrated.

This is a research screener, not investment advice. The rules are not backtested or proven profitable.
