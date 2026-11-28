# Global Stage Radar

Current cross-market policy: trust KIS API prices and KIS adjusted prices; independent
exchange reconciliation and adjustment-formula reconstruction are not Stage gates.
Keep basic quality, identity and provider-support checks. See
[전체 시장 제공자 신뢰 정책](docs/provider-trust-policy.md) and
[중국 ETF 개인 Stage 분석](docs/china-private-analysis.md).

A weekly Stage Analysis screening MVP built with Streamlit. It supports CSV input, clearly labeled synthetic demo data, and a KIS REST API mode for Korean-listed instruments plus US-listed stocks/ETFs. The default monitoring universe uses US-listed ETFs as proxies for global markets, sectors, and commodities where a direct KIS series is not available. The integration is an early pilot; verify symbol support, basic data quality, request limits and usage terms.

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
- **저장된 시장 데이터**: opens automatically in the private production dashboard and analyzes the monitoring universe using saved KIS stock and ETF prices and the separate BTC/ETH snapshot. The data status panel shows refresh details, coverage and errors.

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

See [KIS_SETUP.md](KIS_SETUP.md) for credential setup and pilot limitations. The app does not store credentials in the repository. The current integration fetches daily prices from KIS for supported US/KRX listings; BTC and ETH use a separate Coinbase Exchange public-candles adapter and a separate scheduled snapshot, never the KIS stock endpoint. See the canonical collection schedule below for current timing. International market and commodity coverage is represented by listed ETF proxies, not direct local-index or spot/futures series. Confirm Coinbase API terms and hosting/display rights before public live use. It does not automatically validate market capitalization, sector classifications, benchmark assignments, each ETF's availability at your broker, or public display rights. Start with a small symbol list to avoid request-limit issues. KRX support has unit tests but still needs live API verification.

## 정기 데이터 수집 일정

이 절은 정기 수집의 단일 기준 문서다. 통합 브랜치의 [Cloudflare Worker](automation/stage-radar-scheduler.mjs), [예약 검증](automation/check_scheduled_daily_prices.py), [워크플로](.github/workflows/)와 함께 관리한다. 시각은 한국시간(KST); Cron은 UTC다.

| KST | 요일 | 수집 대상 | Cloudflare Cron (UTC) |
| --- | --- | --- | --- |
| 07:00 | 월~토 | 미국 및 기존 운영 유니버스 (KIS). 운영 수집 단계가 종료되면 미국 연구 종목 전체 가격을 순차 수집한다. | `0 22 * * 0-5` |
| 오전 가격 수집 후 | 월 | KIS 주간 신규 종목 발굴 → Yahoo 시가총액 보완 | 07:00 워크플로에 포함 |
| 09:15 | 매일 | BTC·ETH 전일 UTC 완성 일봉 (Coinbase) | `15 0 * * *` |
| 16:30 | 월~금 | 일본 현지 운영·연구 ETF 및 기준 ETF 종가 (KIS) | `30 7 * * 1-5` |
| 18:30 | 월~금 | 중국 본토·홍콩 현지 ETF 종가 (KIS), 공표된 참고 환율 (Frankfurter ECB) | `30 9 * * 1-5` |

- Cloudflare `stage-radar-scheduler`가 정기 실행을 요청하고 GitHub Actions가 실행한다. 07:00 워크플로는 운영·연구 수집과 월요일 발굴 순서가 끝날 때까지 기존 공유 KIS 큐를 유지한다. 일본과 중국·홍콩도 같은 큐에서 대기한다. 기존 운영 유니버스의 일본 현지 ETF는 당일 오후에 갱신한다. 다음 운영 수집에서는 해당 종가가 저장된 종목을 건너뛴다.
- 예약 시각, 실제 API 시작 및 저장 완료를 구분한다. 일본과 중국·홍콩은 거래소별 세션을 확인하고 해당 거래일의 종가가 없는 종목을 보고한다. 중국·홍콩 환율은 FX 제공자가 공표한 최신분을 저장한다. 해당 종가 시점에 아직 공표되지 않은 당일 환율은 이후 수집에서 보완한다.
- 일부 저장 후 실패한 경우 Actions에서 실패한 작업을 재실행하거나 같은 `scheduled_at`을 전달한다. 수집기는 이미 완료된 종목·세션을 제외한다. 중국·홍콩은 비공개 저장본에서 누락분을 확인한다. 전체 집합을 다시 도는 수동 실행과 정상 예약을 구분한다.
- 배포 시 통합 SHA의 Worker와 위 네 Cron을 함께 반영한다. 기존 운영·연구 분리 Cron과 중국·홍콩 오전 보완 트리거의 제거를 확인한다. 실제 Worker 버전·Cron, 최초 예약별 Actions 실행, 최신 거래일 및 누락 건수를 검증한다.
- 수집 정책 변경 시 이 절, Worker, 관련 워크플로·예약 검증 및 테스트를 동일 PR에서 동기화한다. 다른 매뉴얼은 이 절을 참조한다. 중국 비공개 전달은 [전달 설계](docs/china-private-delivery.md)를 참조한다.

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
