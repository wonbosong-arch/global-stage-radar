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

## 2. Use saved market data

The private production dashboard opens the saved daily close snapshot automatically. In a local run, choose **저장된 시장 데이터** in the sidebar. **데이터 관리** shows the last refresh, per-symbol freshness, errors and candidate coverage. To analyze your own data locally, choose **CSV 업로드** and supply both a daily OHLCV file and a universe file, including the benchmark symbols and their price histories.

## 3. Data coverage

For current scheduled collection times and execution rules, use the [canonical schedule](README.md#정기-데이터-수집-일정), not historical setup instructions.

- Scheduled KIS collection covers supported US and KRX listings. International markets and commodities use listed ETF proxies where direct series are unavailable. ETF prices can differ from the underlying market because of fees, currency effects, futures roll, tracking error and market hours.
- Stage 2 labels are screening heuristics. API access does not grant public display or redistribution rights.

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
