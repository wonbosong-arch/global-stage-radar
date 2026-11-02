# 중국 ETF 수정 후 재검토 보고서

검토일: 2026-11-02 · 기준 커밋: bdc49995e44b8527c67117191b317408899a47fa

**판정: 확인된 메타데이터·분류 오류의 로컬 수정은 통과. 운영 승격은 계속 보류.**

이 폴더는 기준 커밋에서 가져온 파일을 수정한 별도 검토 사본이다. GitHub 브랜치에 적용된 결과가 아니다. 원격 브랜치·PR #192·main·data-validation-mvp·운영 대시보드에는 쓰기 작업을 하지 않았다. 커밋·푸시·병합도 하지 않았다.

## 실제 반영한 수정

| ETF | 이전 지수 | 정정 지수 |
|---|---|---|
| 512290 | 399441 | 930726 생물의약 |
| 512400 | 930607 | 000819 신완 비철금속 |
| 512660 | 399973 | 399967 군공 |
| 512690 | 930606 | 399987 술 |
| 515030 | 930997 | 399976 신에너지 자동차 |
| 515120 | 931140 | 931152 혁신의약 |
| 515210 | 930608 | 930606 철강 |
| 516970 | 930616 | 399995 기건공정 |

- 등록부와 29개 지수 근거표를 동기화했다. 512400은 대표 12종 선정표도 정정했다.
- 512660·515120·512760의 중국어 법정 상품명을 정정했다. 운용사 매핑은 유지했다.
- 515650은 필수·재량소비 혼합, 512720은 하드웨어 포함 컴퓨터 테마, 512980은 미디어, 512400은 비철, 515220은 석탄, 516160은 복수업종 신에너지로 설명을 수정했다.
- 동일 지수인 은행 대안과, 서로 다른 지수의 고상관 반도체 대안을 구분했다. 12종은 잠정 연구 후보이며 비중복 업종 또는 현재 Stage2 통과로 승인하지 않는다.
- 000932의 근거 없는 최신 상한15% 주장을 삭제했다. 2022년 문서의10%는 과거 버전 부분 근거로만 남겼다.
- H30184만 읽은 버전의 상세 규칙 확인 상태로 두고, 나머지는 범위 부분 확인·상세 미검증으로 내렸다. 30종 모두 최신 버전 확인·주문 가능성·조정주가·데이터 권리는 미검증이다.
- 6개 행의 백업 CSV 열 밀림을 복구했다. 백업15행은 과거 기록으로만 표시해 현재 판단에서 제외했다.
- 기존 6종 비교표와 승격 게이트를 새 상태와 맞췄다. 전종목 비활성 상태를 유지했다.
- 과거의 “전종목 검증 완료” 문서는 archives로 보존하고, 현재 연구 메모에서 해당 결론을 철회했다.

등록부 핵심 식별 필드의 변경15건(코드8·상품명3·중국어 지수명4)은 correction_log.csv에서 이전값·새값·출처로 추적할 수 있다. 이15건은 전체 편집 필드 수가 아니라 핵심 식별 변경 수다.

## 공식 근거 재검토

8개 정정 코드를 CSI 공식 도메인의 지수 문서·검색색인 본문으로 다시 대조했다. 상품과 지수의 연결은 1차 감사에서 읽은 SSE·운용사 공시를 재사용했다. 나머지22개 ETF의 출처를 전부 새로 열었다고 주장하지 않는다. 수정된30행과 선정12행의 일관성은 전수 점검했다.

- [생물의약 930726](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/930726factsheet.pdf)
- [비철금속 000819](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000819factsheet.pdf)
- [군공 399967](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399967factsheet.pdf)
- [술 399987](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399987factsheet.pdf)
- [신에너지 자동차 399976](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399976factsheet.pdf)
- [혁신의약 931152](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931152factsheet.pdf)
- [철강 930606](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/930606factsheet.pdf)
- [기건공정 399995](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399995factsheet.pdf)

**이전 설명 보완:** 931152의 2023-12 V1.2 공식 방법론은 영문명을 `CSI Brand Name Drug Industry Index`로 기재한다. 따라서 “Brand Name Drug” 영문 표현 자체는 오류로 단정하지 않았다. 오류는 515120의 잘못된 중국어 법정명·지수명과931140 연결이다. [CSI 공식 방법론](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/20231208180434-931152_Index_Methodology_cn.pdf)

추가로 찾은930726·931152·399976·931139 정적 방법론 URL은 직접 열람에서 시간 초과가 발생했다. 공식 검색색인에서 코드·이름·범위를 확인할 수 있어도 최신 상세 가중·예외 조항 전체를 확인한 것으로 올리지 않았다. CES 직접 방법론도 미검증이다. 문서 사본 해시·현재 버전 시행일의 확정은 여전히 남아 있다.

## 검증 실행 결과

**18개 테스트 통과(기존 선정표 테스트7개 수정 + 독립 수정검사11개).**

- 공식 지수명·코드8쌍과 법정명3개를 고정 근거와 대조.
- 등록부30행·선정12행·지수29행의 연결과 선정 이유 일치 확인.
- 모든 CSV의 열 수 검사 및 백업 복구 후 원래 필드 내용 보존 확인.
- 동일 지수 중복과 고상관 대안 구분, 비활성 게이트·최신성 미검증 상태 확인.
- 12개 60관측일 평균 거래량과 은행·반도체 상관계수 재현.
- 원본 감사 사본 해시와 가격 CSV·수집상태 원문 보존 확인.

이번18개 통과는 저장소 전체 회귀 테스트나 외부 문서 자동 검증을 뜻하지 않는다. 이전 보고서의23개 테스트를 모두 재실행한 것도 아니다. 외부 문서의 내용 대조와 로컬 정합성 검사는 별도다.

재실행: 이 폴더에서 `python -B -m unittest discover -s tests -v`.

## 남은 항목과 승인 범위

| 항목 | 재검토 판정 |
|---|---|
| 잘못된 지수 연결8건·상품명3건 | 수정 확인 |
| 과장된 대표성·일괄 검증 상태 | 수정 확인 |
| 거래량·상관계수 내부 재현 | 확인 |
| 공식 거래량 단위·거래대금·스프레드·추적오차 | 미검증 |
| 12종 실제 구성종목 가중 중복 | 미검증 |
| 최신 전체 방법론·시행일·CES 직접 문서 | 미검증 |
| 조정주가·거래일 완전성·현재 주문 가능성·이용권 | 미검증 |
| 운영 활성화 | 보류 |

잔여 조사 우선순위는①최신 방법론과 문서 버전 고정,②동일 기준일 구성종목·업종 비중 중복 측정,③공식 거래량 단위와 거래비용 대사다. 이 증거가 채워지기 전까지 연구 후보 상태를 유지한다.

## 산출물 사용

- `research/china_mainland_30_etf_verification_register.csv`: 수정 등록부.
- `research/china_sector_representative_12_selection.csv`: 수정 선정표.
- `recheck_results_30.csv`: 30종 수정 후 판정과 출처.
- `correction_log.csv`: 핵심 식별 변경 내역.
- `source_manifest.json`: 기준 커밋과 입력 사본 해시.
- `research/official_identity_index_evidence.csv`: 1차 감사의 이전값·권고값 근거 기록. 현재 상태는 수정 등록부와 recheck_results_30.csv를 따른다.
- `research/archives/` 및 `backup_…csv`: 과거 기록. 현재 검증 상태로 재사용하지 않는다.

이 수정본은 원본에서 일부 CSV 스키마·상태값을 확장했다. 운영 코드나 다른 테스트와의 전체 호환성은 승인하지 않았다. 브랜치 적용 전 저장소 전체 회귀 검증이 필요하다.
