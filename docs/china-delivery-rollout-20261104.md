# 중국 ETF 운영 연결 사전 조사 — 2026-11-04 KST

## 확인된 상태와 마지막 연결

기준: `data-validation-mvp` = `9d53acf858403fe2b82dd27b7071b87ed6866f16`.
[PR #204](https://github.com/wonbosong-arch/global-stage-radar/pull/204)는 해당 SHA로 병합되었고
[병합 후 Python CI](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41743038552)는 success.
작업 시작 시 열린 PR #202는 기존 pipeline 작업이며 #204에 통합된 기능을 다시 구현하지 않았다.
#194/#197–#200 등 연구 PR, #47(main 통합), #46(main 대상)도 열려 있어 건드리지 않았다.
로컬 기존 checkout의 미커밋 가격/연구 변경도 그대로 보존하고 새 clone에서 작업했다.

마지막 연결은 **07:00 runner의 private publish 설정과 접근 제한된 Streamlit reader의
동일 저장소 sync 설정**이다. 저장소 코드가 이 배포 계약을 자동 적용하지 않는다.

| 경계 | 코드/읽기 전용 증거 | 아직 확인되지 않은 조건 |
|---|---|---|
| 수집 | china_candidate_prices.yml: `0 22 * * 0-5`, KST 월–토07:00, shared concurrency | private research/publish 환경은 workflow에 없음 |
| 현재 출력 | 기존 entry point는 flag 없으면 30종 후보 CSV를 Git에 기록 | 새 비공개 세대가 이 경로로 전달되는 것은 아님 |
| 전달 | china_private_delivery.py: immutable files → CAS current.json → reader hash/Stage 검증 | 실제 bucket/owner/prefix, IAM, SDK 설치, 배포 env 미확인 |
| 표시 | china_dashboard.load_research: env root 선택, sync 후 private loader | Cloud 배포 branch/SHA, root/env, reader 인증, 앱 privacy 미확인 |
| 운영 편입 | 모든 private 결과 operational_eligible=false | 비공개 연구 표시는 운영 Stage2 universe 편입과 다름 |

[11월4일07:28 KST 중국 예약 실행](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41731127547)은
cancelled, jobs=[]였다. 직전 11월3일도 cancelled. 취소 원인은 API 결과만으로 확정할 수 없다.
[11월2일 성공 실행](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41356890322)의
observe/수집/commit 단계 success는 재확인했다. 새 KIS 호출은 하지 않았다.
KIS_APP_KEY/KIS_APP_SECRET 기존 workflow 참조만 확인했으며 connector가 Secrets API를
지원하지 않으므로 현재 secret 등록·유효성·수정 시각은 미확인이다. 값 조회/재입력 요청 없음.

기존 hosted inspector를 설치된 Edge로 `--inspect` 실행했으나
`Hosted app was not available for inspection` 결과였다. 배포 SHA/화면/로그인 상태를
확인하지 못했으며 이를 앱 장애나 공개/비공개 판정으로 해석하지 않는다.
로컬 결과는 checkout 밖 delivery-hosted-inspection-20261104/result.json에 보존했다.

## 기존 저장소 재사용 판단

읽은 workflow/docs에는 실제 승인된 bucket, AWS 역할 또는 공유 영구 볼륨의 배포 증거가 없다.
이는 계정에 저장소가 없다는 뜻이 아니다. 현재 도구에는 AWS/Streamlit 관리자 세션이 없다.
로컬 private snapshot/runner 임시 디스크/GitHub artifact/공개 Git CSV는 Cloud와 공유되는
비공개 영구 저장소로 간주할 수 없다. 기존 general-purpose AWS S3가 아래 조건을 충족하면
새 bucket 없이 별도 prefix를 재사용할 수 있다. 기존 저장·요청 비용의 증가도 미리 승인해야 한다.
S3 호환 타사 endpoint는 현 adapter가 지원하지 않으므로 재사용 가능하다고 추정하지 않는다.

## 승인 후 배포 계약 (아직 적용하지 않음)

- 저장소: owner/region 확인, Block Public Access 전체, bucket-owner-enforced,
  TLS 강제, AES256 허용, versioning/보존 정책 확인. 기존 SSE-KMS 강제 정책과 현 AES256
  요청은 호환 여부를 따로 검토한다. 현 adapter에는 KMS 키 설정이 없다.
- writer: 승인된 prefix/*의 GetObject/PutObject, 해당 bucket의 prefix 제한 ListBucket
  (없는 키가 NoSuchKey로 판별되어 최초 게시 가능해야 함). Delete/ACL/bucket 정책 권한 불필요.
  기존 OIDC가 확인된 경우만 재사용하고 ref/repository trust를 제한한다. 별도 병렬 writer 금지.
- reader: 동일 prefix/* GetObject만. KIS/writer 키 전달 금지. S3는 private여도 가격을 보내는
  대시보드가 공개이면 데이터가 공개되므로 앱 인증/허용 사용자와 저장·가공·웹 표출 권한부터 확인.
- dependency: 양쪽 모두 `requirements-private-delivery.txt`의 boto3 필요. Cloud 현재
  requirements.txt는 이를 설치하지 않는다. 설치 방식 변경도 배포 승인 대상이다.
- 서버 인증: 승인된 SDK credential chain 사용. preflight는 자격증명을 resolve하지 않는다.
  임시 AWS 인증이면 session token/만료/갱신 경로까지 확인한다.

| 환경변수 | writer | reader |
|---|---|---|
| CHINA_PRIVATE_OBJECT_TRANSFER | publish | sync |
| CHINA_KIS_PRIVATE_REFRESH | research | 설정 불필요 |
| CHINA_PRIVATE_SNAPSHOT_DIR | runner의 checkout 밖 private 디렉터리 | Cloud의 checkout 밖 쓰기 가능한 private cache |
| CHINA_PRIVATE_S3_REGION/BUCKET/PREFIX/OWNER | 승인된 동일 대상 | 승인된 동일 대상 |
| GITHUB_SHA 또는 CHINA_COLLECTOR_COMMIT | provenance 필수 | 불필요 |
| KIS_APP_KEY/KIS_APP_SECRET | 기존 Secrets 참조 유지 | 전달 금지 |

Cloud loader는 os.environ을 읽는다. `[china]` 등 TOML 하위 테이블만 넣으면 이 경로가
읽지 못한다. 승인 후 root-level secret/env 매핑을 확인해야 한다.
[Streamlit root-level secrets 문서](https://docs.streamlit.io/develop/concepts/connections/secrets-management),
[Cloud secrets 설정](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management),
[앱 접근 설정](https://github.com/streamlit/docs/blob/main/content/deploy/community-cloud/manage-your-app/app-settings.md),
[S3 권한 문서](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-management.html)를 기준으로 검토한다.
reader cache는 영구 원본이 아니며 재시작 후 S3에서 다시 받는다. 화면 방문/재실행 시 sync이며
새 데이터가 열린 브라우저에 07:00 정각 자동 push되는 타이머는 없다.

## 배포 전 실행 가능한 점검

`python china_delivery_preflight.py --role writer` 또는 `--role reader`.
미설정 기본 OFF이며 종료코드2. 필요한 설정의 형식/역할/checkout 경계와 writer 필수 항목을
검사한다. 값·경로·예외문을 출력하지 않고 고정 issue code만 출력한다. 디렉터리 생성,
AWS/KIS 호출, SDK credential 조회, secret 쓰기 없음. 유효하면 코드0이지만
deployment_verified=false, operational_eligible=false를 유지한다.
IAM/비공개 여부/이용권/credential 유효성/쓰기 권한/실제 snapshot 상태는 이 검사로 증명되지 않는다.
합성 smoke는 기존 tests/test_china_private_delivery.py의 분리 디스크 왕복·hash·CAS·실패 시
pointer 보존 테스트를 재사용한다. 외부 가격 대사/SSE 재수집은 수행하지 않는다.

## Rollout / rollback 검증 체크리스트

1. 소유자가 기존 저장소 대상, 비용 조건, 앱 접근 제한 및 데이터 이용권을 확인한다.
   배포 branch/SHA와 requirements 설치 방식을 읽기 전용 확인한 뒤 정확한 설정 diff를 승인한다.
2. 두 역할 preflight를 실제 서버 환경에서 수행한다. writer/reader 권한 분리를 검증하고
   비인증 사용자가 앱/가격/파일에 접근할 수 없는지 검사한다. 시세/키는 로그·artifact에 보존하지 않는다.
3. 승인된 workflow 설정만 연결하고 기존 07:00 cron/concurrency와 기존 KIS secret 참조를 유지한다.
   수동 실행 없이 다음 정상 예약 실행을 사용한다. 기존 공개 git add에 private 파일이 없음을 확인한다.
4. 12종 수집·품질/완료주봉/최신성 → local generation → private upload → remote CAS →
   reader가 동일 remote generation/hash를 검증하는지 서버 측 점검한다. 공개 CSV fallback 금지.
   reader local generation 이름은 별도 UUID이므로 양쪽 local 폴더명 일치를 요구하지 않는다.
5. 비공개 화면 목록/3×3 차트, 실패·stale 표시, 재시작 재동기화, 기존 US/KR/JP 회귀를 확인한다.
   운영 universe 편입은 하지 않는다. public 권한을 구성 플래그에서 추론하지 않는다.
6. 실패하면 publish/research/sync 플래그를 해제하고 승인된 배포 설정으로 되돌린다.
   sync 해제만으로 CHINA_PRIVATE_SNAPSHOT_DIR의 기존 로컬 가격이 사라지지 않으므로
   표시 중단이 목적이면 reader root 설정도 제거한다. 불변 세대는 삭제하지 않는다.
   이전 pointer 복구는 별도 승인된 CAS 절차와 최신성 검증 후에만 수행한다.

다음 최소 결정: **기존 비공개 저장소와 Streamlit 앱 설정을 관리자 권한으로 읽기 전용 확인하는
단계만 승인**한다. 저장소/비용/접근통제를 아직 특정하지 못했으므로 현 단계에서 운영 활성화
승인을 한꺼번에 요청하지 않는다. 키 재입력이나 사용자 KIS 호출은 필요 없다.
