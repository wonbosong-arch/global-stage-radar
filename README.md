# Global Stage Analysis Radar

A weekly Stage Analysis screening MVP built with Streamlit. The project currently supports CSV input and synthetic demo data. It intentionally does **not** fetch live prices yet: provider coverage, adjustment quality, licensing and redistribution permissions must be verified first.

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

Download example CSV templates from `data/`. Price history should include each stock and its market/sector benchmark. Minimum history is 35 weekly bars; longer history is recommended.

## Screening logic (initial, not validated as a trading strategy)

- Weekly bars resampled to Friday.
- 30-week simple moving average (SMA).
- Four-week change in the 30-week SMA.
- Market and sector relative performance based on the difference between stock and benchmark 26-week returns.
- Stage 2 candidate: close above SMA30, positive four-week SMA slope, and positive 26-week relative performance vs both market and sector.
- Stage 2A watch is an internal label for screening, not an official Weinstein stage label.

Market capitalization is filtered only for stocks. Missing market cap is excluded from the stock screen. The input market cap must already be in USD; currency conversion and stale market-cap checks are not yet automated.

## Important data caveats

- This project does not currently have a live market data provider configured.
- Do not assume that an API key or a free quota permits public display or redistribution.
- Before adding a provider, verify its official terms, free-tier limits, historical depth, adjustment methodology, global symbol coverage, market-cap and sector fields, and whether public web display is allowed.
- This is a research screener, not investment advice. The rules are not backtested or proven profitable.

## Deploy

A basic Streamlit Community Cloud deployment can point at this repository and `app.py`. Live data is not available until a provider is separately vetted and integrated.
