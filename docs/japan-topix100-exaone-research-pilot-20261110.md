# K-EXAONE 일본 TOPIX100 업종 매핑 파일럿 — 중간 검증 기록 (2026-11-10)

## 실제 진행 및 제약

- 개발 통합 기준: `data-validation-mvp` (시작 SHA `1955365a0ff2c7eaabf950061ae9f70429b3e1db`). `main`, 앱, 가격 수집, Stage 판단 및 미국 관련 파일은 변경하지 않는다.
- 기존 일본 연구 중복 회피: `data/global_sector_expansion_plan.csv`, `data/japan_sector_candidate_review.json`, `data/japan_candidate_prices_status.json`과 일본 ETF 관련 회귀 테스트 확인. 현재 일본 TOPIX-17 ETF 1617~1633은 가격 수집·연구가 이미 진행 중이며 **ETF 실제 보유 종목 입증과 업종 지수 대응은 서로 다른 정보**이다.
- JPX 공식 소스 페이지: [List of TSE-listed Issues](https://www.jpx.co.jp/english/markets/statistics-equities/misc/01.html) / [English Excel 파일 링크](https://www.jpx.co.jp/english/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_e.xlsx). 2026년 10월 말 기준 데이터가 제공되는 것으로 페이지에서 확인. 월간 파일은 제3영업일 전후에 교체되므로 **다운로드 날짜만으로 유효일을 대체하지 말 것**.
- 참고 분류: [JPX 33업종→TOPIX-17](https://www.jpx.co.jp/english/markets/indices/factsheets/files/e_000_fac2_sector.pdf), [J-Quants 33 업종코드](https://jpx-jquants.com/ja/spec/eq-master/sector33code), [17 업종코드](https://jpx.gitbook.io/j-quants-pro-ja/api-reference/kdo/sector17code).
- TOPIX Core30/Large70 정기 구성 확인: [TOPIX index](https://www.jpx.co.jp/english/markets/indices/topix/), [2026-10-07 공표](https://www.jpx.co.jp/english/news/6030/20261007-01.html). 2026년 10월 30일 정기 변경 결과가 있으므로 **2026-10-31** 기준 파일의 Core30=30, Large70=70을 실제로 검증해야 TOPIX100으로 인정한다.
- ETF 연결: [NEXT FUNDS 공식 목록](https://nextfunds.jp/lineup/). ETF `1617~1633`은 TOPIX-17 지수의 업종별 *프록시*이며 실제 ETF 보유 종목 여부는 이 도구가 검증하지 않는다.

## 중요: JPX 이용권한

[JPX Terms of Use](https://www.jpx.co.jp/english/term-of-use/index.html)는 허가 없는 상업적 데이터 수집·2차 이용을 제한한다. 이번 프로젝트는 투자 관련 서비스와 연결되므로 해당 원본의 상업적 처리 및 배포 권한을 임의로 가정하지 않는다.

**현재 권한 확인 전 실행 범위**: 공개적으로 제공되는 분류 체계의 구조 검증, 별도 CLI, 합성 데이터 기반 단위 테스트, 공개 가능 문서. 공식 Excel 수집·파일 저장·100개 기업명/코드 파생 데이터·공개 PR 업로드를 하지 않는다. 100개 실측은 **0건**이며 TOPIX100 공식 분류 확인 건수도 **0건**이다. 이 수치는 조사·검증 실패가 아니라 권한 미확정에 따른 의도적 보류이다.

## 구현된 독립 검증 도구

- `japan_topix100_review.py`: 네트워크 호출/유료 데이터/운영 코드 접근이 없는 오프라인 CLI. 공식 English JPX CSV 및 XLSX(별도 `openpyxl` 설치 필요) 입력.
- 기본 `topix100` 선택: `Size (New Index Series)`의 Core30 30건 + Large70 70건 및 중복 없는 100개 코드를 확인하지 못하면 `UNCONFIRMED_INDEX_OR_FALLBACK` 처리.
- 별도 `--selection prime100_fallback`: 정렬된 동경 증권거래소 Prime 국내 종목 중 앞 100개를 **임의 순위 없는 대체 표본**으로 명시. 해당 결과를 TOPIX100이라 부르지 않는다.
- 산업 그룹 33→17 매핑 및 `1617~1633`의 지수 업종 프록시 연결. 33·17 코드는 JPX/J-Quants 구조와 일치해야 하며, 정보 누락과 불일치는 `review_required`.
- 코드 중복, 코드-회사명 충돌, 필수 업종, 자료 날짜, 외부 코드-회사명 검증 자료와 출처/기준일 교차 확인. 단일 JPX 파일만으로 회사명 검증을 완료했다고 주장하지 않는다.
- 결과는 `japan_topix_sector_review.csv`, `japan_topix_sector_summary.json`이며 **반드시 모든 Git 체크아웃 밖**의 비공개 경로로 출력.
- `verified`는 구성 종목·코드·업종 매칭·독립 코드-회사명 참조 출처/기준일이 정상인 경우에만 사용. 별도 참조가 없으면 `review_required`. ETF 보유 종목 확인 및 운영 활성화 값은 0이다.

## 사용 방법 — 권한 확보 이후에만

예시 (다음 경로는 개인 외부 작업 공간이며 Git 저장소와 무관):

```bash
python -m pip install openpyxl
python japan_topix100_review.py \
  --jpx-file "/private/authorized/data_e.xlsx" \
  --reference "/private/authorized/independent_identity.csv" \
  --reference-url "https://example.org/authorized-reference" \
  --reference-as-of "2026-10-31" \
  --as-of "2026-10-31" \
  --out "/private/authorized/review" \
  --authorized-use
```

`--authorized-use`는 **사용자가 실제 데이터 처리 허가를 갖고 있다는 확인 선언**으로, 허가 자체를 부여하지 않는다. `independent_identity.csv` 형식: `local_code,company_name`. 별도 공신력 있는 근거 및 기준일이 없다면 `--reference`를 생략하고 검토 보류 상태로 출력한다. 실제 URL과 출처를 허위로 채우지 말 것. `--source-url`로 공식 출처를 명시하지 않으면 모든 결과를 `review_required`로 분류한다. 보고서에 입력 파일 SHA-256을 기록하지만 이는 무결성 추적용일 뿐 **공식 출처의 암호학적 인증은 아니다**. 33·17 업종 데이터가 공식 파일에 포함되어도 외부 회사명 교차 확인이 없으면 완전 검증 처리하지 않는다.

## 테스트 및 다음 실행의 완료 기준

```bash
python -m unittest discover -s tests -p "test_japan_topix100_review.py" -v
```

- 합성 TOPIX100/비정상 길이/중복/회사명 불일치/업종 누락/33→17 불일치/날짜 오류/대체 표본 표시/비공개 파일 경계/미승인 입력 차단을 검증.
- 커밋/PR CI 성공은 합성 검증 도구에만 적용된다. **실제 일본 종목 100개 검증 완료나 대시보드 적용을 의미하지 않는다.**
- 공식 데이터 사용권한이 확인되면 사용자 소유 비공개 입력 위치에서 실행하고, 실측 30·70 종목 수, 33→17 검증 수 및 `review_required` 목록을 별도 보존.
- 실제 운영 데이터 반영은 별도 승인 필요.

## EXAONE 파일럿 사용량 및 중단 원인

이번 연구 지시를 받은 이후 이 작업 브랜치에서 **EXAONE API 직접 호출 0회, 성공 0회, 실패 0회**. 따라서 입력/출력/추론 토큰, 응답 지연 및 실제 남은 한도는 **미확인**이다. 계정 공식 일일·주간 한도 또한 미확인. 실험용 최대 **30회는 사용 상한이지 승인된 비용이나 공식 공급자 한도가 아니다.**

기존 직접 EXAONE 파서 테스트 생성 작업은 성공했으나 이것이 일본 연구 자율 개발 능력 검증으로 이전되지는 않는다. 이번 CLI와 단위 테스트는 GPT가 독립 브랜치에서 작성했다. 별도 EXAONE 위임에는 비용·API 실행 승인, 원본 접근·사용 권한 및 새 업무의 적정 범위 확인이 필요하다. 동일한 OpenCode 파일 작성 실험은 반복하지 않는다.

**파일럿 현황:** 공식 자료 출처 확인·코드 구현·합성 테스트까지 진행 / 공식 100개 실측·EXAONE 모델 주도 조사·개발·자체 수정·회귀 자동 실행은 미완료. GPT 개입은 이번 한 차례 작업 세션, 사용자 추가 개입 0회. 주간 EXAONE 처리능력은 실측 자료가 없어 수치화하지 않는다.
