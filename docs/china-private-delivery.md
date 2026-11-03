# 중국 비공개 전달: 배포 전 설계 / 2026-11-03

## 검증 상태

- 통합 기준 `67cff86a4e3ede9130574f2d33fdd86f41111540`, #201 병합 유지.
- #202 Draft head `0181173bde04e6aa661921b7ceeba5eba64efeb4`의 Unit/Syntax
  run41589125198, Python run41589125409 모두 success. 해당 tree8af45b67를
  새 브랜치에 그대로 재사용했다. 기존 #197–#202 수정/병합 없음.
- 현재 세션 KIS_APP_KEY/SECRET 환경 제공 없음. **현재 인증된 호출 미실행**.
  secret 저장소에서 값을 읽거나 인증정보 재입력을 요청하지 않았다.
- 더 최근의 기존 정상 예약 실행을 읽기 전용 확인:
  [2026-11-02 07:23 KST 실행](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41356890322)
  observe job124998764400의 KIS 수집/commit 단계 success. 로그에서 두 KIS 환경
  변수가 각각 마스킹된 비어 있지 않은 값으로 주입된 증거 확인. secret 관리 API는
  연결 도구가 제공하지 않으므로 현재 secret 목록/갱신 상태까지 확인했다고 주장하지 않는다.
  07:25:52 KST 결과: requested30/data30/fresh30/error0, 대표12종 모두 SHS,
  rows300/latest2026-10-30, 512800 포함. 원본 응답 JSON/가격 bytes를 새로 취득한
  증거가 아니라 기존 인증 수집기의 성공 관측 로그다. 운영 권한/웹 표출권 확인과 별개다.
- [2026-11-03 예약 실행](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41537626610)
  cancelled, jobs 없음. 양쪽 실행 모두 artifact 없음. 취소 원인은 확인하지 못했다.
  정상 시각은 기존 cron `0 22 * * 0-5`(KST 월~토07:00), 실제 시작 지연 관측.
  스케줄/수동 실행/재실행 변경 없음.

## 새 코드 경로 (미설정 기본 비활성)

Community Cloud와 runner의 디스크는 별개다. 외부 비공개 S3를 매개로 수집기가
불변 세대의 가격/manifest 두 개를 업로드한 뒤 원격 current.json을 조건부 갱신한다.
대시보드는 서버에서 인증 GET으로 포인터를 한 번 고정하고 두 파일의 SHA256,
KIS manifest, 기존 12종 품질·Stage·최신성을 재검증한 뒤 로컬 포인터를 atomic replace한다.
화면은 기존 loader/Stage/UI를 사용한다. 공유 볼륨 방식도 그대로 가능하다.
화면 방문/재실행 시 갱신하며 브라우저 자동 타이머를 새로 추가하지 않는다.

- `china_private_delivery.py`: 주입 가능한 store 인터페이스 + AWS S3 adapter.
- S3 HTTPS 고정 regional endpoint, owner 검증, AES256 암호화, 공개 ACL 없음.
  conditional PUT `IfNoneMatch=*`/`IfMatch=ETag`, 파일당16MiB 제한, bounded SDK 재시도.
  [AWS PutObject 계약](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html).
- writer는 기존 KIS concurrency 내 단일 실행. 수집/가격 요청 정책은 #202 그대로.
  원격 포인터 충돌/부분 업로드는 이전 원격 포인터 보존. 부분 업로드 재시도 가능.
  CAS는 동시 덮어쓰기를 막지만 오래된 writer의 순서 역전을 전부 막지 않으므로
  기존 직렬화는 필수이며 별도 writer 생성 금지.
- reader 실패 시 이전 로컬 포인터 보존, 오류를 올려 실패를 최신 데이터처럼 표시하지 않음.
  변경 없는 세대는 해시/최신성 재검증 후 캐시 사용. 다운로드 중인 포인터 변경은
  현재 읽기를 섞지 않음. 이전 세대/실패한 staging은 자동 삭제하지 않음.
- 전송 설정은 사용권/운영 승인이 아니다. 모든 결과 operational_eligible=false.
  object URL/서명 URL/원본 가격/응답/스크린샷을 공개하지 않는다.

## 승인 후 배포 계약 (이번에는 실행하지 않음)

비용 및 운영환경 변경 승인 뒤 다음 설정을 AI가 적용한다. 사용자 수동 API 호출이나
가격 파일 복사는 필요 없다. AWS 저장소와 권한이 아직 없다면 생성/비용 승인 필요.

1. AWS general-purpose S3, Block Public Access 전체, bucket-owner-enforced,
   TLS 강제, versioning 및 암호화, prefix 제한 정책. 공개 bucket/object ACL과
   공개 bucket policy 금지. SDK가 ACL을 생략하는 것만으로 비공개 보장은 안 된다.
2. GitHub Actions writer 역할: 해당 prefix GetObject/PutObject만, ListBucket은
   해당 prefix만(없는 키의 NoSuchKey 판별용), Delete/ACL/정책 수정 권한 없음.
   기존 GitHub OIDC를 쓸 수 있으면 단기 역할 사용. KIS secrets는 기존 참조 유지.
3. Community Cloud는 승인된 비공개 앱/접근통제 확인 후 reader 전용 AWS 권한을
   서버 secret에 설정. GetObject만, writer/KIS 자격증명 전달 금지.
   인증 없는 기존 공개 앱에 활성화하지 않는다. 필요한 가격 저장·가공·웹 표출권 확인.
4. 두 환경에 선택 dependency `requirements-private-delivery.txt` 설치.
   기존 workflow 파일 변경은 이 승인 시점에만 별도 diff로 검토하며 cron은 유지.
5. 공통 환경: CHINA_PRIVATE_S3_REGION/BUCKET/PREFIX/OWNER(12자리 계정 ID),
   CHINA_PRIVATE_SNAPSHOT_DIR(모든 checkout 밖). 수집기는
   CHINA_KIS_PRIVATE_REFRESH=research 및 CHINA_PRIVATE_OBJECT_TRANSFER=publish,
   대시보드는 CHINA_PRIVATE_OBJECT_TRANSFER=sync. AWS 자격증명은 SDK의 승인된
   서버 환경 경로만 사용. 이번 작업은 어떤 플래그/secret도 설정하지 않았다.
6. writer 수집 성공→local commit→private upload→remote CAS→reader 검증 순서.
   업로드 실패 시 수집기 local 세대는 새것일 수 있지만 remote/reader는 이전 세대다.
   기존 공개 git add는 새 파일을 포함하지 않는다. 활성화 시 공개 CSV 경로로
   fallback하지 않는 research flag 분기를 점검한다.
7. 세대 보존/정리 정책은 별도 승인된 운영 절차로 설정. 읽기 중 세대를 즉시
   지우지 않는다. rollback은 flag 해제 및 승인된 이전 pointer 복구로 수행한다.

## 사용자 개입 없는 다음 검증 경로

현재 등록된 스케줄을 그대로 기다린 뒤 새 scheduled run의 job/마스킹된 주입/성공
집계/대표12종 observations/latest_date/error_count를 읽기 전용 확인한다.
512800 성공 관측과 전체12종의 정상 입력을 확인할 수 있으며 추가 KIS 요청은 없다.
artifact가 없으면 기존 collector status/commit과 로그 metadata만 대조하고 가격을
새 공개 파일에 복사하지 않는다. 이 방법은 기존 경로의 인증 성공 검증이며 새
비공개 backend E2E 운영 검증은 아니다. 이번 세션에서 미래 감시 자동화를 생성하지 않았다.
새 backend 운영 검증은 승인 후 동일 예약 실행의 writer 업로드 성공 및 비공개 앱
reader가 같은 세대/해시를 읽는 서버 측 검사로 마친다. 직접512800 최소 호출은
권한 있는 실행환경이 생길 때만 하고 기존 예약 결과로 충분하면 중복 호출하지 않는다.
