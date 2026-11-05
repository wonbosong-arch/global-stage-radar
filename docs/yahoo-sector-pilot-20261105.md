# Yahoo 업종 100종목 파일럿 — 실측 자료 미확보, 검토 경로 구현

기준 `data-validation-mvp` / `cac6c702603b0e4c967a3cc1cc5eba34564716ed`.
Codex에서 구현했다. PR #215 병합과 동일 SHA의 자동 Python CI 성공을
실시간 GitHub 조회로 확인했다. 열린 PR에서 중복되는 미국 Yahoo 업종 작업은
발견되지 않았고 관련 Codex 채팅은 idle/notLoaded였다. 기존 중국 연구 checkout의
미커밋 변경은 보존하고 독립 브랜치와 worktree를 사용했다.

## 실제 결과

| 구분 | 결과 |
| --- | --- |
| 미국 등록 후보 | 2,148 |
| PR215 비업종 요건 재검사 통과 조건부 후보 | 135 |
| 재현 가능한 파일럿 표본 | 100, 전부 위 135개에서 선택 |
| 실제 Yahoo 종목 조회 시도 / 성공 | 0 / 0 |
| 종목 조회 성공률 / 지연 / 지속 가능 호출속도 | 측정 불가, 0% 성공률로 해석하지 않음 |
| 사용 가능한 저장 Yahoo Sector/Industry | 0 |
| 파일럿 업종 확보 / 매핑 검토 가능 / Stage 검토 가능 | 0 / 0 / 0 |
| 135개 중 업종 확보 / 매핑 검토 가능 / Stage 검토 가능 | 0 / 0 / 0 |
| 신규 실제 검토용 분석 범위 | +0, 기존 저장 85개 멤버십 보존 |
| 운영 승인·활성화·배포 | 0 |

135는 저장된 제안 ETF 기준으로 KIS 신원·시총 $1B 화면 조건·완료 35주·유효 일봉
150개·신선도·벤치마크와 기존 Stage/RS 계산 요건을 만족하는 집합이다. Yahoo 업종으로
135개를 확인했다는 뜻이 아니다. Yahoo로 다른 ETF가 제안되면 다시 계산하며,
충돌은 보류한다. 시총은 기존 `cap_provenance`의 screening estimate/출처 상태를
그대로 기록하고 verified로 올리지 않는다. 기존 85개의 현재 Stage label을 재계산하거나
새 스냅샷과 과거 Stage2 수를 합산하지 않았다.

## 중단 근거와 안정성 한계

공개 업종 페이지 [Yahoo sectors](https://finance.yahoo.com/sectors/) 직접 열기는
429 Too Many Requests였다. 종목 프로필 호출이나 재시도, 로그인, cookie/crumb
취득, 차단 우회는 하지 않았다. 이 결과는 **공개 페이지 접근 제한**이며
135개 종목 API 실패나 종목별 속도제한 실측으로 확대 해석할 수 없다.

[Yahoo 공식 약관](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html)의
공식 도메인 검색 발췌는 사전 명시적 허가 없는 자동 수집 제한을 나타낸다.
약관 본문과 Finance 추가 약관 직접 조회는 도구 오류 999로 실패해 최신 전문을
검증하지 못했다. 따라서 이 환경에서 허용된 자동 조회 범위가 확립됐다고 볼 수 없어
이번 작업은 종목 수집 전에 멈췄다. 무료·비인증·공개 페이지라는 사실만으로 수집 허가를
추정하지 않는다. 이는 작업 범위의 보수적 판단이며 법률 판단이나 승인 요청이 아니다.

감사기록 `evidence/yahoo-sector-access-audit-20261105.json`은 출처 URL, 확인 뒤
기록한 UTC 시각, 오류, 재시도 0, 시간·Retry-After 미노출을 구분한다. 실제 조회가
없으므로 성공률, 결측률, 공급자 분류 정확도, 호출 지연·적정 속도는 **아직 미측정**이다.
비공식 응답 형식 변경·인증 요구·429·분류 체계 차이·자료 노후화와 재배포 권한이 병목이다.
실측 profile 원문·유료 라이선스·상용 안정성은 확보하지 않았다.

기존 `yahoo_market_cap_supplement.py`의 `yfinance.Ticker.get_info()` 경로는 확인만
했다. 해당 함수는 자동 부가 호출이 발생할 수 있어 이번 작업에서는 호출하지 않았다.
티커 변환 `yahoo_ticker_symbol`은 그대로 재사용한다. `yahoo_large_cap_candidate_review.csv`의
sector/sector_benchmark는 `yahoo_master_cap_batch.build_large_cap_candidate_review_queue`
내 `proposed_stock_mapping`에서 유래한 제안이다. Yahoo profile 관측으로 승격하지 않는다.
나머지 저장 Yahoo CSV에도 사용 가능한 원천 Sector/Industry 관측은 없다.

## 표본과 대응표

표본은 제안 업종 × KIS 거래소 층별 round-robin이며 고정 문자열 seed와 SHA256
정렬을 사용한다. 입력 행 순서, Python hash seed와 무관하다. BRK/A·BRK/B를 먼저
포함해 기존 slash→hyphen 변환을 검사한다. 실제 관측 업종으로 표본을 고른 것은 아니다.
희소 층을 전부 포함하는 균형 표본으로, 미국 전체 2,148개의 통계적 대표 표본은 아니다.

- NAS 54 / NYS 43 / AMS 3.
- Financials 14 / Health Care 14 / Industrials 14 / Information Technology 12 /
  Communication Services 9 / Consumer Discretionary 9 / Energy 8 / Semiconductors 8 /
  Consumer Staples 7 / Materials 2 / Real Estate 2 / Utilities 1.
- 11개 대분류 외 기존 Semiconductors 전문 프록시 층을 별도 보존한다.

| Yahoo Sector (정확한 명칭만) | 검토용 업종 | ETF |
| --- | --- | --- |
| Technology | Information Technology | XLK |
| Financial Services | Financials | XLF |
| Communication Services | Communication Services | XLC |
| Consumer Cyclical | Consumer Discretionary | XLY |
| Consumer Defensive | Consumer Staples | XLP |
| Healthcare | Health Care | XLV |
| Industrials | Industrials | XLI |
| Energy | Energy | XLE |
| Basic Materials | Materials | XLB |
| Real Estate | Real Estate | XLRE |
| Utilities | Utilities | XLU |

위 표는 연구용 어휘 대응이다. ETF 편입·GICS 동일성 확인이 아니다. Industry를 보고
SOXX로 강제 배정하지 않으며 기존 반도체 제안과 Technology→XLK 차이도 review_required다.
알 수 없는 명칭·빈 Industry·중복 관측·기존 매핑 충돌·ETF metadata 불일치·요청 티커/거래소
연결 오류·날짜 미상/미래/기준일 종료 시점 7일 초과 관측을 격리한다. Yahoo는 KIS 증권
유형·신원·거래소 또는 ADR 비율을 승인하는 자료로 사용하지 않는다.

## 구현과 재현

`yahoo_sector_pilot.py`는 **네트워크 기능 없는** 독립 CLI다. 허용된 저장 관측 JSON을
명시적으로 제공할 수 있다. 기본은 관측 없음이다. 입력 schema는 합성 fixture를 참고한다.
`data_origin`은 cache/fixture 중 하나이고, fixture 계산 수는 실제 확대 수에서 제외된다.
수집시각은 timezone을 포함한 fetched_at_utc이며 분류의 공식 시행일로 간주하지 않는다.
requested_kis_exchange는 조회 대상의 연결 키이며 Yahoo가 거래소 신원을 증명했다는 뜻이 아니다.

```powershell
python us_sector_mapping_batch.py --as-of 2026-11-05 > ../yahoo-sector-base-replay-20261105.json
python yahoo_sector_pilot.py --as-of 2026-11-05 --batch-replay ../yahoo-sector-base-replay-20261105.json > ../yahoo-sector-pilot-replay.json
python -m pytest -q tests/test_yahoo_sector_pilot.py tests/test_us_sector_mapping_batch.py tests/test_yahoo_market_cap_supplement.py
```

`--batch-replay`를 생략하면 PR215 기존 모듈을 직접 실행한다. 저장 replay는 현재 입력과
구현 파일 hash·기준일 일치를 검사한다(LF/CRLF 동등성 허용). 저장 증거에 원본 가격을
복사하지 않고 파일 hash, 표본, 대상별 미확보/충돌 사유와 감사 필드만 포함한다.
과거 135 목록을 무조건 하드코딩하지 않고 실제 batch replay에서 조건부 대상을 도출한다.

새 관측이 들어오면 `stock_mapping.py`의 기존 제안과 대조한 뒤
`us_sector_mapping_batch.evaluate_new_rows`와 기존 KIS/cap/weekly/RS/Stage 엔진을
재사용한다. data/, registry, approved, active, Stage 엔진, 운영 UI, workflow/cron은
수정하지 않는다. KIS live, Actions 수동 실행/재실행, S3/AWS/Secrets/비용은 사용하지 않는다.

## 검증과 다음 병목

합성 fixture는 실제 Yahoo 응답이 아니다. 다중 종목 엔진 계산, $1B 경계, KIS 증권 유형·
거래소·ADR·가격 신선도·이력·벤치마크 gate, 명칭/기존 매핑 충돌, 오류/429·시각·중복·
미지원 분류, 고정 표본, 원본 및 승인 상태 불변, fixture 비집계, 네트워크 미호출을 검증한다.
CI 및 최종 SHA 결과는 Draft PR 본문에 기록한다.

다음 단계는 허용 범위가 명시된 원천 Sector/Industry 저장 관측 또는 정식으로 허용된
공급 경로 확보다. 그러기 전에는 100개 조회 성공률·135개 매핑 일치율이나 실제 확대를
주장할 수 없다. 자료가 확보되면 동일 manifest를 사용해 cache/실측을 구분하고,
반도체 등 충돌은 보류한 채 새로운 ETF로 비업종 요건을 재평가한다.
