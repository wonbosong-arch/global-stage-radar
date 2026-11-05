# NASDAQ 공식 CSV 실측 확인과 로컬 입력 검사 — 2026-11-05

**실제 NASDAQ CSV 다운로드 0건, 확보 원본 0개, 분석 행 0개.**
최신 파일의 필드·종목 수·결측률·NYSE/NASDAQ/AMEX 범위·sector coverage와
기존85개/조건부135개의 NASDAQ 일치 수는 모두 **미측정(null)**이다.
0% coverage 또는135개 불일치라는 뜻이 아니다. 기존 검토 Stage 가능85개 보존,
신규 검증 매핑/Stage 가능0개. 합성 테스트를 실측에 포함하지 않는다.

## 공식 확인과 시작 상태

확인 기록: 2026-11-05 06:09:28 UTC. 이 시각은 다운로드일/데이터 기준일이 아니다.
[공식 스크리너](https://www.nasdaq.com/market-activity/stocks/screener)에는
Download CSV 버튼과 Exchange/Sector/Region/Country 필터 제목이 있다.
이번 공개 페이지 조회는 No filter applied, no matching symbols / data unavailable다.
파일/직접 CSV URL/다운로드 응답, Exchange 개별 선택값과 CSV 내부 열은 미확인이다.
다운로드 시도0, 403/429 관측·재시도0. `/terms-of-use`는 도구 접근 불가였으나
HTTP 상태가 제공되지 않았으므로403이라고 하지 않는다.

[공식 약관 전문](https://www.nasdaq.com/legal), 표시 개정일2026-05-11을 읽었다.
Section6의 개인 비상업 서비스 이용 허용과 별도로 Sections2/7은 데이터 캡처 및
분석 소프트웨어 개발 목적의 수동/자동 콘텐츠 활용을 제한하며 서면 허가를 요구한다.
Sections7/11은 복제·파생물·공개·후속 저장·제삼자 제공을 제한한다.
Section8의 제삼자 조건도 별도다. 버튼이나 개인 연구 목적만으로 이번 프로그램 대조,
GitHub 보관 또는 대시보드 표시가 허용됐다고 해석하지 않았다. 목적에 대한 허가
근거가 없어 다운로드/버튼 조작을 수행하지 않았다. 숨은 endpoint·JS/네트워크
역분석·차단 우회·Finviz/Yahoo 재시도는 없다. CSV 원본을 저장/업로드하지 않았다.

최신 원격 integration `cac6c702603b0e4c967a3cc1cc5eba34564716ed`에서 독립 브랜치를
만들었다. #215 merged, head6c01682의 PR Python/Unit CI 성공을 재확인했다.
#216 Draft7d5a1c8, #217 Draft258477e의 PR Python/Unit CI도 모두 성공.
열린 PR15개와 관련 Codex chats를 확인했으며 중복 NASDAQ PR은 없고 관련 chats는 idle.
다른 checkout의 중국 연구 미커밋 파일이나 두 Draft의 코드는 변경/가져오지 않았다.

## 최소 구현

`nasdaq_local_csv_review.py`는 네트워크/쓰기 없는 독립 CLI다.
`us_sector_mapping_batch.saved_baseline`으로 저장85개 membership을 검증하고,
기존 batch 증거의 조건부135개 및 등록부 미국2,148개를 읽는다. 현재 가격/Stage
readiness 재계산은 하지 않는다. 기존 FMP/Yahoo 어댑터·crosswalk를 복제하지 않았다.

`Symbol, Name, Exchange, Sector, Industry, Market Cap`은 **검사할 입력 계약**이며
최신 NASDAQ CSV의 확인된 열이라는 주장이 아니다. BOM/공백/대소문자/MarketCap을
지원하며 열 부재·행 너비·결측률·시총 비정상 수를 검사한다. NASDAQ 시총으로 KIS
가격이나 기존 cap gate를 대체하지 않는다.

symbol+venue로 연결한다. NASDAQ/NAS, NYSE/NYS, AMEX/NYSE American/AMS만 지원한다.
미국 상장 시장과 미국 본사 기업 조건을 혼동하지 않는다. ADR/종목 유형은 재분류하지
않는다. Exchange 열이 없으면 추정하지 않으며, 확인된 단일 거래소 필터의 근거가
manifest에 있는 경우에만 파일 단위 venue를 부여한다. 열이 있는데 빈 행은 채우지
않는다. 필터별 파일 병합 시 Exchange 보존과 중복 검토가 필요하다.

표기 차이는 자동 제거하지 않는다. 명시적 근거가 있는 같은 클래스의 점/하이픈/
슬래시 대응만 허용한다. A/B를 합치지 않으며 중복·alias collision을 보류한다.
source_as_of가 없으면 null이고 다운로드일로 대신하지 않는다. native Sector 있음,
날짜 있는 native 관측, Industry 있음을 따로 센다. 이름 동일 여부도 보고하지만
NASDAQ 이름으로 KIS 신원을 덮어쓰지 않는다. GICS/업종 ETF 적합성·새 Stage 자격은
검증하지 않는다. 관련 수0, 승인·active·운영 입력 연결 없음.

원본은 모든 Git checkout 밖에서만 읽는다. 출력은 stdout이며 기업명/Industry/시총
원본 행을 출력하지 않는다. sector 빈도 등 파생 보고서도 권한 없는 외부 게시 대상이
아니다. CSV/manifest/등록부/cohort 해시와 UTC 기록을 출력한다. 명시적 synthetic
모드의 실제 파일 집계는0이다. manifest는 사용자 권한 선언이며 법적 권한을 인증/
부여하지 않는다. 새 계정·키·비용·Secrets가 필요하지 않다.

## 허가 후 수동 전달 절차

1. NASDAQ의 수동 다운로드·비공개 로컬 저장·오프라인 KIS 대조와 결과 보관을
   허용하는 근거부터 확보한다. 일반 개인 이용 조항/버튼만으로 허용됐다고 하지 않는다.
   대시보드/재배포/외부 AI나 에이전트로 파일 전달·처리하는 범위도 별도 확인한다.
2. 허용 범위 안에서 사용자가 공식 Download CSV로 받아 Git 밖 개인 폴더에 둔다.
   원본 SHA256, 다운로드 UTC, 실제 필터, 제공자가 명시한 기준일과 근거를 기록한다.
   기준일이 없으면 null. 실제 필드·3거래소 범위는 이때 파일로 측정한다.
3. 같은 개인 폴더에 아래 manifest를 채우고 허용된 로컬 환경에서 실행한다.

```json
{
  "dataset_kind": "nasdaq_manual_csv",
  "source_url": "https://www.nasdaq.com/market-activity/stocks/screener",
  "acquisition_method": "user_manual_download",
  "permission_status": "unconfirmed",
  "permission_reference": "",
  "manual_download_allowed": false,
  "local_storage_allowed": false,
  "offline_analysis_allowed": false,
  "csv_sha256": "",
  "downloaded_at_utc": null,
  "source_as_of": null,
  "source_as_of_reference": null,
  "symbol_aliases": []
}
```

이 미확인 예시는 실패하도록 되어 있다. 실제 허가·해시·UTC 확인 뒤에만 채운다.
Exchange 열 없는 파일은 `export_exchange`와 `export_exchange_reference`가 필요하다.
합성 표기 예시: `{"source_symbol":"TEST.A","kis_symbol":"TEST/A","venue":"NYS","evidence_reference":"실제 확인 근거"}`.
이는 실제 CSV의 대응표가 아니다.

```powershell
python nasdaq_local_csv_review.py --csv <Git밖CSV절대경로> --manifest <권한manifest절대경로>
```

관련21 tests/46 subtests 통과(신규12). 합성 결측/거래소/dual class/중복/미상 날짜/
구조/권한 선행 거부/Git 내부 거부/2,148·85·135 집합 연결/실제 파일0을 검증했다.
전체 Windows 검사와 최종 SHA 자동 CI는 PR 본문 최종 기록으로 확인한다.
실제 대조 성공 테스트가 아니며 기존 플랫폼 실패를 수정·숨기지 않는다.
전체 Windows UTF-8 pytest487 passed/28 failed/7 skipped/236 subtests.
수정하지 않은 병합 기준에서 실패4개 모듈을 실행해 동일28개 실패 행을 재현했다.
최종 provenance 해시 추가 후 관련21/46 재통과, compile/14 YAML/JSON 검사 통과.
전체 로컬 성공은 주장하지 않으며 최종 SHA 자동 CI 결과와 구분한다.
main/integration 직접 변경, 운영/Stage/수집/workflow/cron/queue 변경, 다른 PR 병합,
배포·승인·활성화, KIS live, 수동 Actions 없음. 다음 한 단계는 **NASDAQ 목적별
이용허가 근거 확보**다.
