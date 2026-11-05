# 미국 업종 데이터: 무료 범위 검증과 오프라인 어댑터

2026-11-05 확인. 실제 FMP 종목 요청 **0**, Sector/Industry 확보 **0**,
새로 분석 가능한 종목 **0**. 저장 baseline **85 → 85**다. 조건부 135개는
저장 가격과 기존 제안 기준 비업종 요건을 만족하는 집합이며, 확보된 업종
관측이나 새 분석 가능 수가 아니다. 합성 5개는 실제 확대 수에 포함하지 않는다.

## 기준과 작업 분리

기준 `data-validation-mvp`: `cac6c702603b0e4c967a3cc1cc5eba34564716ed`
(#215 병합). GitHub에서 최신 ref와 열린 PR을 확인했다. 기준 push
[Python CI](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41970200149)는
성공이다. 관련 다른 Codex 작업은 idle이었다. #216은
`7d5a1c8bdbdaf751f1d9f0b1db0b22c8ad957212`의 미병합 Draft이며 그대로 유지한다.
해당 브랜치의 코드·fixture를 가져오지 않았다. 작업 브랜치는
`feat/fmp-sector-adapter-20261105`, 독립 worktree를 사용했다.

## FMP 공식 문서에서 확인한 범위

| 항목 | 2026-11-05 공식 문서 확인 결과 |
|---|---|
| Basic | 무료, 250 calls/day, 최근 30일 누적 대역폭 500MB |
| `GET /stable/profile?symbol=...` | Company Profile Data의 Basic 대상은 미국 거래소; Sector/Industry 필드 제공 |
| `GET /stable/profile-cik?cik=...` | 요금표상 Profile by CIK Basic Full Access; 이번 어댑터/실측 대상 아님 |
| `GET /stable/profile-bulk?part=0` | Basic·Starter·Premium 제외, Ultimate에 포함. 무료 벌크 아님 |
| 구형 `/api/v3` | 현행 무료 접근 대안으로 가정하거나 시도하지 않음 |
| 호출 권한 | 문서 등재와 계정별 실제 응답은 별개; 이번 세션에서는 미검증 |

출처: [공식 요금표](https://site.financialmodelingprep.com/pricing-plans),
[Profile](https://site.financialmodelingprep.com/developer/docs/stable/profile-symbol),
[Profile Bulk](https://site.financialmodelingprep.com/developer/docs/stable/profile-bulk),
[분류 목록 API 설명](https://site.financialmodelingprep.com/developer/docs/stable/available-sectors).
Bulk 문서의 일반적인 무료 시작 홍보 문구를 해당 endpoint의 무료 권한으로
해석하지 않았다. Profile 문서의 `Limited Access` 표시도 계정 실측을 대신하지 않는다.

[약관](https://site.financialmodelingprep.com/terms-of-service) 2.2~2.2.2는
개인 비사업·비상업 이용과 다중 사용자 표시를 구분하며, 복사·다운로드에도
사전 서면 허가 조건을 둔다. 요금표 역시 표시·재배포에 별도 Data Display and
Licensing Agreement를 요구한다. **무료 API 권한으로 독립 Streamlit의 저장,
웹 표시, 원문/파생 자료 공개를 포괄 승인받았다고 판단할 수 없다.** 비공개
오프라인 저장·처리도 해당 목적을 덮는 권한 근거를 먼저 확인해야 한다.
별도 계약의 비용·승인 여부는 미확인이다.

세션 환경의 `FMP_API_KEY`, `FINANCIAL_MODELING_PREP_API_KEY`,
`FINANCIALMODELINGPREP_API_KEY`는 모두 부재였고 새 checkout에는
`.streamlit/secrets.toml`이 없다. 값이나 다른 계정의 자격증명을 찾지 않았다.
기존에 승인된 FMP 키가 제공되지 않았으므로 5개 파일럿을 실행하지 않았다.
문서 응답 예제도 실제 조회로 집계하지 않는다. 계정 생성, 카드 등록, 키 생성,
Secrets 변경, 유료 요청은 수행하지 않았다.

## 구현 및 재현

`fmp_sector_review.py`는 **네트워크 없는** cache/fixture 어댑터다. 기존
`stock_mapping.py`, `us_sector_mapping_batch.evaluate_new_rows` 및 Stage 엔진을
재사용한다. 새 API client, 자동 갱신, 앱 경로, 운영 승인 bridge는 만들지 않았다.

FMP의 11개 원문 label과 Industry를 보존하고 명시적 프로젝트 대응표를 사용한다.
Technology→Information Technology/XLK, Healthcare→Health Care/XLV,
Financial Services→Financials/XLF, Basic Materials→Materials/XLB,
Consumer Cyclical→Consumer Discretionary/XLY,
Consumer Defensive→Consumer Staples/XLP; 나머지는 동명 5개 업종의 ETF에 대응한다.
이는 프로젝트의 제안 대응표이며 FMP와 GICS의 방법론이 같다는 주장이 아니다.
Industry로 SOXX를 추정하지 않는다. 기존 Semiconductors/SOXX 등과의 차이는
`review_required`로 보류하고, 일반적인 정상 행은 `provider_based_proposed`다.

요청과 응답의 ticker, provider exchange↔KIS venue, 단일 프로필·중복,
HTTPS 공식 source, UTC 관측 시각, Sector/Industry, 주식 유형과 active flag,
기존 assigned/proposed/curated 매핑, active KIS ETF metadata를 검사한다.
BRK/A→BRK-A 등은 명시적 **후보 요청 표기**일 뿐 실측 검증된 alias가 아니다.
다른 표기/host/계정으로 재시도하지 않는다. 키가 들어간 URL도 받지 않는다.
현재 Profile은 분류 시행일을 제공하지 않으므로 source_as_of는 null이며
조회일을 시행일이나 과거 가격 시점의 분류로 바꾸지 않는다.

`mode=observed`는 `rights.local_storage=true`, `rights.offline_processing=true`,
`rights.evidence_reference`를 요구한다. 이는 전달받은 허가 근거를 기록하는
계약이며 코드가 허가를 발급하는 것이 아니다. `mode=synthetic`은 실제 추가
수에 절대 포함하지 않는다. CLI 출력은 입력 hash·집계·종목 ID이며 공급자
원문 프로필이나 가격을 공개하지 않는다. 로컬 cache 자체는 저장소에 넣지 않는다.

```sh
python fmp_sector_review.py --as-of 2026-11-05
python fmp_sector_review.py --as-of 2026-11-05 --cache /private/authorized-profiles.json
python -m pytest -q tests/test_fmp_sector_review.py tests/test_us_sector_mapping_batch.py tests/test_us_stage_mapping_expansion.py tests/test_us_stage_connection_plan.py tests/test_us_kis_evidence_readiness.py
```

Cache 구조는 `tests/fixtures/fmp_profiles_synthetic.json`의 완전한 합성 예제를
참조한다. 실제 파일은 해당 목적의 권한 확인 후 `mode=observed`, rights 근거,
각 응답의 registry_symbol/requested_symbol/source_url/http_status/fetched_at_utc와
원본 response 배열을 제공한다. 합성 fixture를 observed로 이름만 바꾸면 안 된다.

허가된 키가 나중에 제공되면 증거 JSON의 planned_five_symbol_pilot 5개를 먼저
확인한다. APP·SPOT·ABNB·UBER·CCEP는 **계획만** 수립했다. 공식 stable
단일 Profile을 각 1회 호출하고, 401/402/403/429·권한·형식 문제 시 중단한다.
자동 재시도·다중 키·로그인 우회는 없다. 실제 계정의 당일 잔여량을 확인하기
전에는 250회 전부가 남았다고 가정하지 않는다. 5개 결과와 권한이 허용될 때만
135개 집합으로 범위를 넓히며, 최초 5개를 중복 호출하지 않는다.

기존 KIS ticker+venue·유형/ADR·시총 $1B screening·완료35주·유효150일봉·
품질/신선도·시장/업종 benchmark gate를 통과한 경우에만 review-only Stage를
계산한다. 기존 85개는 재계산하지 않으며 운영 approved/active로 승격하지 않는다.

## SEC 및 State Street 대안

**SEC:** [공식 Submissions API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)는
인증·API 키가 필요 없다. `data.sec.gov/submissions/CIK##########.json`의
SIC·sicDescription과 ticker/exchange pair가 대상이다. SIC는 발행사 사업분류로
[공식 SIC 설명](https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list)에
정의되며 ETF/GICS와 같지 않다. 이번 `normalize_sec_sic`는 CIK·공식 source·
관측 시각·listing pair·SIC를 검증하고 원래 체계만 보존한다. 검증된 crosswalk가
없으므로 섹터와 ETF는 null이다. 최신 filings 날짜를 SIC 시행일로 쓰지 않는다.
[SEC FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)는 공시
재사용을 허용하며, 선언된 User-Agent와 초당10회 이하의 fair access를 안내한다.
이번 웹 도구의 AAPL submissions 조회는 `not accessible via this tool`로 실패했다.
성공한 SIC JSON은 **0**이며, 상태가 명시되지 않아 403이라고 단정하지 않는다.
별도 계정이나 우회 경로를 만들지 않았다. 다음 수집기는 실제 연락처를 포함한
User-Agent와 낮은 직렬 속도, 403/429 즉시 중단을 사용해야 한다.

**State Street:** [공식 XLK 페이지](https://www.ssga.com/us/en/individual/etfs/state-street-technology-select-sector-spdr-etf-xlk)에서
holdings as-of **2026-11-03**과 공식 Daily 다운로드 링크를 확인했다:
`https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-xlk.xlsx`.
웹 도구는 XLSX를 unsupported content-type으로 처리하여 전체 파일을 해석하지
못했다. 확인한 페이지 기준일을 읽지 않은 파일 내부 기준일로 대신하지 않는다.
같은 페이지는 제3자 복제·전송에 서면 동의를 요구한다. 따라서 전체 편입 자료
수집·저장소 게재·새 매핑 생성은 하지 않았다. 11개 Select Sector ETF 전체에
동일 권한이 있다고 일반화하지 않았다. 허용된 파일을 확보해도 펀드 편입은
특정 날짜의 구성 증거로서 전 미국 종목 업종 DB나 개별 종목 Industry가 아니다.
반도체도 XLK에 포함되므로 기존 SOXX 전문업종과의 차이를 명시해야 한다.

## 검증 및 다음 최소 조건

관련 **45 tests / 117 subtests** 통과. 신규11개 테스트는 합성5개를 실제 기존
엔진으로 계산하고, 권한/출처/요청·응답 연결/분류 충돌·가격/신원/시총 gate,
fixture 실제 수 제외, baseline 재계산 차단과 SEC taxonomy 보존을 검증한다.
UTF-8 전체 Windows pytest는 **486 passed / 28 failed / 7 skipped / 273 subtests**,
unittest는 406개 중 기존 Windows 오류26개/skip1이다. untouched merged base에서
실패한4개 모듈을 실행해 **동일28개 실패**를 재현했고 실패 식별자 집합도 같다.
원인은 기존 Windows fsync/POSIX shell/결측값 경로 문제이며 수정하거나 숨기지
않았다. 초기 기본 cp949 실행은 기준·변경 양쪽64개 실패/같은 식별자였다.
compileall·14 YAML 파싱 통과. 최종 SHA 자동 CI는 PR 본문에 결과를 기록한다.

FMP 다음 최소 조건은 **기존 승인된 키의 안전한 제공 및 비공개 저장·처리
권한 근거**다. 외부 Streamlit 표시·재배포는 별도 계약 확인이 필요하다.
SEC는 키 대신 선언할 실제 연락처와 검증된 SIC 대응 정책이 필요하다.
현재는 수집·비용·배포 승인을 요청하지 않고 구현과 증거를 Draft로 보존한다.
