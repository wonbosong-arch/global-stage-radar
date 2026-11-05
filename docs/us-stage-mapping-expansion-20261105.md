# 미국 Stage 검토 커버리지 확대 — 2026-11-05

기준은 작업 시작 시 최신 `data-validation-mvp`
`168ccf14c1a0043d37125a3438179920cb1156fa`다. 독립 브랜치
`feat/us-stage-mapping-expansion-20261105`에서 작업했다. #209~#213의 미국
검증·수집 수정은 이미 병합되어 있다. 열린 PR 13개를 확인했으며 미국 매핑
확대와 같은 목적의 열린 PR은 없었다. 중국 연구/전달 PR들과 #46/#47의
별도 대상·범위를 가져오지 않았다. 공통 진행 기록 외 신규 파일은 독립적이다.
직전 통합 코드의 Python CI(90ac2c8, run 41937713905)는 성공했다.
최종 PR의 충돌 가능성과 Python/Unit CI는 해당 PR head에서 별도 확인한다.

## 변경 및 실제 결과

`stock_mapping.py`에 14개 **검토용** 업종/ETF 제안을 추가했다.
`us_stage_mapping_expansion.py`는 기존 `OfflineStageReplay`, KIS 신원 판정,
시총 선택/출처 함수와 weekly/RS/Stage 엔진을 그대로 사용한다. 대상 14개와
필요한 ETF만 주봉으로 변환하며 기존 72개는 재계산하지 않는다. 상태를
승인으로 위장하거나 원본의 assigned/proposed 필드를 고치지 않는다.

| 검토 업종 | 추가 제안 | 업종 ETF | 신원·데이터 통과 |
|---|---|---|---:|
| Utilities | XEL, D, SRE, ETR, EXC | XLU | 5 |
| Materials | VMC, MLM, NUE | XLB | 3 |
| Real Estate | PSA, VTR, CBRE, O | XLRE | 4 |
| Communication Services | TTWO | XLC | 1 |
| Health Care | IDXX | XLV | 0 (신원 근거 부족) |

시장 벤치마크는 기존 US-listed-market fallback인 SPY다. 신규 13개는 저장
KIS 마스터의 상장 venue/type 근거가 일치한다. 14개 모두 시총 추정 $1B 이상,
기본 OHLCV/중복/미래값 검사, 완료 35주, MA30·4주 기울기, 일봉 150개,
정렬된 시장/업종 26주 RS와 7일 freshness 검사를 통과했다. 13개의 매핑 적절성
검토가 완료되거나 운영 승인이 부여되었다는 뜻은 아니다.

IDXX는 registry에 KIS 업종 코드 510과 종목명이 남아 있고 발행사 사업 설명도
확인되지만 `unranked_us_stock_master.csv`에 행이 없다. 현재 discovery_source도
Yahoo review이므로 KIS ranking fallback 조건을 충족하지 않는다. **Stage label은
null로 보류**한다. 최소 후속 조치는 보존된 KIS 마스터/랭킹 원본에서 IDXX의
NAS·주식 유형 출처 행을 찾아 연결하는 것이다. 가격이나 업종 코드만으로 신원을
승격하지 않는다. 이번에 새 KIS API를 호출하지 않았다.

## 같은 입력 스냅샷의 비교

단순히 서로 다른 날짜의 Stage 개수를 합치지 않았다. 기존 #211 평가에 사용한
`9416654`의 여섯 입력을 Git에서 `/tmp`의 별도 디렉터리로 읽어 냈고, 기존
72개 검증 JSON에 기록된 **모든 입력 SHA256/바이트 수와 CRLF 동등성을 확인**했다.
원래 증거는 Windows CRLF checkout을 해시했으므로 Git의 LF 파일을 그대로
해시하면 다르다. 내용 변경은 허용하지 않으며 줄바꿈 동등성만 인정한다.

같은 입력, 같은 평가일 **2026-11-04**에서 새 14개만 계산한 결과다. 새로 확인한
업종 근거를 과거 가격 스냅샷에 적용한 검토 비교이며 성과 백테스트가 아니다.

| 항목 | 기존 보존 결과 | 추가 통과분 | 확대 후 |
|---|---:|---:|---:|
| Stage 분석 가능 종목 | 72 | 13 | **85 (+18.1%)** |
| Stage 2 후보 | 25 | 3 | **28** |
| Stage 2A 관찰 후보 | 5 | 0 | **5** |
| 중립 / 추가 확인 | 35 | 7 | 42 |
| 하락 추세 관찰 | 7 | 3 | 10 |
| 운영 편입 | 0 | 0 | **0** |

추가 Stage 2 후보는 **D, NUE, PSA**다. 추가 하락 관찰은 MLM/O/SRE이며 나머지
7개는 중립이다. 완료 주봉은 62~63주, ETF는 210주다. 기존 72개 label과
membership/count만 저장 JSON에서 가져왔고 해당 종목의 엔진 호출은 0이다.
회귀 테스트가 baseline 종목을 주봉 입력에서 제외하는지 직접 검사한다.

최신 시작 기준 데이터의 **2026-11-05** 평가도 새 14개만 따로 수행했다.
13개 통과, Stage 2=3, 2A=0이며 모두 완료 63주다. 평가일/입력이 달라지는
경우 도구는 합산 Stage 개수를 `null`로 반환하여 기존 72개까지 최신 검증했다고
표시하지 않는다. 이 최신 결과의 누적 검토 커버리지는 85개다.
NUE/XEL의 최신 저장일은 11/04(7일 gate 11/11까지), 나머지는 10/30(11/06까지)다.
이후 사용 시 저장 가격의 신선도를 다시 확인해야 한다.

## 누락 원인과 근거의 범위

기존 제안은 curated ticker 목록에 의존한다. 최신 US registry 2,148개 중
저장된 proposal의 업종/업종 ETF 누락은 1,877개다. 이 중 `000`이 아닌 KIS
업종 코드가 있는 것은 XEL/IDXX/IBN 세 개뿐이다. IBN은 별도 ADR 검토 대상이며
이번 확대에 포함하지 않았다. `unranked_us_stock_master.csv`에는 업종 코드 열이
없고, `yahoo_master_cap_triage.csv`의 6,444개 `kis_industry_code`는 모두 비었다.
따라서 이 자료만으로 나머지 종목의 업종을 일괄 판정할 수 없다.

이번에는 운용사의 공식 **2026-11-03 편입 내역**에서 이름을 확인한 13개만
명시적으로 추가했다. IDXX는 KIS 510과 발행사의 진단/의료 사업 설명을 사용한
별도 제안이다. XEL의 KIS 910도 보조 근거로 기록했다. KIS 코드 전체의 공식
분류표를 확보한 것으로 간주하거나, 빈 코드·`000`·회사명으로 일반화하지 않는다.
나머지 확대에는 업종 코드가 보존된 마스터 또는 종목별 명확한 업종 근거가 필요하다.

- [XLU 공식 편입 내역](https://www.ssga.com/us/en/intermediary/etfs/state-street-utilities-select-sector-spdr-etf-xlu)
- [XLB 공식 편입 내역](https://www.ssga.com/us/en/intermediary/etfs/state-street-materials-select-sector-spdr-etf-xlb)
- [XLRE 공식 편입 내역](https://www.ssga.com/us/en/intermediary/etfs/state-street-real-estate-select-sector-spdr-etf-xlre)
- [XLC 공식 편입 내역](https://www.ssga.com/us/en/intermediary/etfs/state-street-communication-services-select-sector-spdr-etf-xlc)
- [IDEXX 사업 설명](https://www.idexx.com/en/about-idexx/)

종목별 URL/관측일/편입 기준일/보존 코드/검토 상태는
`docs/evidence/us-sector-mapping-sources-20261105.json`에 남겼다.
시총은 confirmed가 아닌 screening estimate다. XEL은 보존 KIS ranking의
$48.70B(10/27), 나머지는 기존 Yahoo review 값/URL과 유일하게 일치한다.
Yahoo 관측 시각은 시총 as-of가 아니며 빈 기준일을 채우지 않았다.

## 재현과 검증

최신 시작 스냅샷 재현:

```sh
python us_stage_mapping_expansion.py --as-of 2026-11-05
```

동일 스냅샷 비교는 아래 여섯 파일을 임시 디렉터리에 `git show
9416654:<path>`로 추출한 후 실행한다. 원본 checkout의 data 파일은 변경하지 않는다.

```python
from pathlib import Path
import subprocess
from us_stage_mapping_expansion import INPUTS
target = Path('/tmp/us-stage-baseline-9416654')
target.mkdir(exist_ok=True)
for name in INPUTS:
    (target / name).write_bytes(subprocess.check_output(['git', 'show', '9416654:data/' + name]))
```

```sh
python us_stage_mapping_expansion.py --as-of 2026-11-04 --data-dir /tmp/us-stage-baseline-9416654
```

두 실행 결과는 `docs/evidence/us-stage-mapping-expansion-{comparison,current}-20261105.json`에
보존했다. 입력·구현 SHA256, 시총 provenance, 종목별 보류 이유/기존 상태,
벤치마크 metadata, 완료 주봉 및 label이 포함된다. stdout만 쓰는 오프라인 도구다.
입력 스냅샷이 바뀌면 과거 보고서를 최신 결과로 간주하지 않는다.

신규 9개 테스트를 포함한 관련 33개 테스트/하위 84개가 통과했다. 전체 unittest는
386개 실행, 성공(외부 개인 스냅샷 의존 1개 skip)했다. 처음에는 sandbox가
`/tmp/.git`을 자동 생성하여 중국 private-root 검사 13개가 실패했으며, 검사
로직을 변경하지 않고 공개 checkout 밖의 `/dev/shm/us-stage-tests`를 TMPDIR로
지정하여 해결했다. pytest도 같은 환경에서 확인하며 최종 결과는 PR에 기록한다.
compileall 및 전체 workflow YAML 파싱은 통과했다. 최종 커밋의 자동
Python tests와 Unit tests and syntax validation은 PR에서 SHA와 함께 확인한다.

`main`, 운영 universe, 후보/가격 원본, Stage 엔진, 수집 workflow/스케줄,
Secrets, 승인 bridge는 변경하지 않았다. 새 KIS 호출·활성화·병합·배포는 0이다.
