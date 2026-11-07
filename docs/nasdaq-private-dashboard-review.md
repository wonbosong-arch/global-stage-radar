# 비공개 NASDAQ CSV → 검토 화면 (기본 비활성화)

이 문서는 #219에서 재사용한 기존 로컬 파일 모드의 기록이다. 새 웹 업로드의
동작·검증·세션 보관 및 영구 저장 제한은 [웹 업로드 문서](nasdaq-web-upload.md)를
기준으로 한다. 아래의 업로드 미구현·월별 절차 설명은 기존 로컬 모드에만 해당한다.

개인 전용 로컬 Streamlit 앱의 **검토 전용 연결**이다. 운영 유니버스, `screen`,
Stage2 목록, 관심 목록에 신규 종목을 추가하지 않는다. 병합·배포·운영 활성화는 별도
승인 대상이다. 기존85는 입력 유무와 관계없이 기존 경로를 사용한다. CSV 원본과
기업별 파생 자료는 모든 Git checkout 밖에 둔다.

## 전달 방식 비교와 선택

| 방식 | 월별 교체·지속성 | 현재 구현/제약 |
| --- | --- | --- |
| 개인 로컬 파일 + hash-bound manifest | 사용자가 파일을 보관하고 새 쌍을 수동 교체; 로컬 디스크에 지속 | 이번 구현. 새 서비스·비용·Secrets 없이 가능. 앱은 읽기만 수행 |
| 비공개 관리자 업로드 | 매 세션 수동 업로드 가능; 재접속·재시작 이후 보장 없음 | 보류. 영구 저장과 공개 호스팅 접근 통제 설계가 필요 |
| 기존 비공개 객체 저장소 | 버전·이전 정상본 보관 가능 | 보류. 승인된 연결 없음. 서비스 생성·권한/Secrets·비용 변경 안 함 |

Streamlit 공식 문서: [업로드는 RAM의 BytesIO에 저장](https://docs.streamlit.io/knowledge-base/using-streamlit/where-file-uploader-store-when-deleted),
[Session State는 WebSocket 연결에 종속](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state).
Community Cloud 세션 메모리/임시 파일은 월별 영구 저장 수단이 아니다. 업로드·S3·
네트워크 저장·자동 교체·cron을 구현하지 않는다.

## 실행 조건 (운영 설정은 변경하지 않음)

향후 개인 전용 로컬 앱을 수동 실행할 때만 아래 환경 변수를 프로세스에 전달한다.
현재 배포 앱이나 Secrets에 이 값을 추가하지 않는다.

- `NASDAQ_PRIVATE_REVIEW_ENABLED=1`
- `NASDAQ_PRIVATE_REVIEW_CONTEXT=local_private`
- `NASDAQ_PRIVATE_CSV`: 모든 Git checkout 밖의 수동 다운로드 원본 절대 경로
- `NASDAQ_PRIVATE_MANIFEST`: 모든 Git checkout 밖의 manifest 절대 경로

두 opt-in 값은 정확히 일치해야 한다. `local_private`는 실행자의 선언이며 호스팅/
네트워크의 접근 통제를 자동 검증하는 기능이 아니다. 공개 Cloud에서 켜는 것은 지원하지
않는다. 기존 `APP_PASSWORD`로 별도의 검토 잠금을 해제하고 개인 입력 검토 checkbox에
동의해야 읽는다. KIS 로그인과 독립적이며, 비밀번호가 없으면 잠긴다. 새 Secret을
만들지 않는다. 기존 비밀번호 변경 시 재인증한다.

데이터 관리 영역의 별도 expander에서 버튼을 누르면 CSV → 기존
`nasdaq_single_source.build_report` → 검토 표로 전달된다. 전역 mutable cache나
`st.cache_data`를 사용하지 않는다. 원문을 다운로드·로그·브라우저 저장소·CI artifact에
쓰지 않는다. 인증한 사용자의 브라우저에는 검토 표가 표시된다.

## 월별 수동 갱신

1. 사용자가 NASDAQ CSV를 직접 내려받아 Git 밖의 개인 폴더에 보관한다.
2. `nasdaq-single-source-offline.md`의 manifest 계약대로 원본 SHA256, 수동 다운로드
   출처, 개인 분석 지시를 연결한다. 모르는 날짜는 `null`이다. 다운로드일/분류 시행일/
   파일 mtime을 서로 대신 쓰지 않는다. 알려진 날짜에는 각 reference를 붙인다.
   이전 원본·manifest 쌍은 복귀용으로 별도 보관한다.
3. 새 파일·manifest 쌍의 준비를 마친 뒤 개인 로컬 프로세스를 실행한다. 같은 경로를
   교체할 때는 두 파일 교체를 완료한 뒤 버튼을 누른다.
4. 로그인·동의 후 검증 버튼을 누른다. 성공해야 세션 검토본을 교체한다. 알려진 원본일
   우선, 없으면 알려진 다운로드일 기준으로 45일을 넘으면 거부한다. 두 날짜 모두
   불명이면 최신성 미확인 경고를 항상 표시한다.
5. 누락·해시 불일치·구조 오류·오래된 날짜·입력 변경 시 이전 정상 세션본을 유지하고
   일반 오류만 표시한다. 이전 날짜의 검토본에는 고정 과거 snapshot 경고를 붙인다.
   최초 입력 없음은 빈 검토 영역으로 끝나며 기존 운영 목록은 정상 유지한다.

잠금/기능 해제/동의 철회 시 검토본을 비운다. 재접속·앱 재시작 후 자동 복구하지 않는다.
앱은 파일을 저장/교체하지 않으므로 영구 복귀는 사용자가 보관한 CSV·manifest 쌍을 다시
선택·검증해야 한다. 서버 파일 삭제나 보안 소거 보장은 아니다.

## 검증·회귀 경계

- 최대 CSV20MB/manifest100KB, SHA256, 출처·목적, 구조·필수 열·행 폭·빈 식별자,
  날짜·미래일·alias 선언을 검증한다. 중복/class/alias 충돌은 해당 후보를 보류한다.
  Exchange가 없다고 NASDAQ 상장으로 추정하지 않고 KIS venue/name/type을 쓴다.
- 변환 전후 CSV·manifest·KIS snapshot 해시가 같아야 한다. 중간 교체가 있으면 세션
  교체를 거부한다. 기존85를 같은 날짜에 재생한 결과와 신규 후보를 중복 없이 표시한다.
  과거 baseline label을 현재 통과로 합산하지 않는다.
- NASDAQ native Sector/Industry가 단일 업종 정보 원천이다. KIS 신원·시총·가격 품질,
  150일봉·35주·시장/업종 RS·기존 Stage 엔진과 11 ETF proxy 규칙을 재사용한다.
  SEC/FMP/Yahoo/Finviz 업종 결합 및 live 조회는 없다. 기존 KIS 시총 관측 보조 파일은
  기존 gate의 일부이며 업종 분류 소스로 승격하지 않는다.
- 기존 Stage2 목록/3×3·선택·pager·스크롤·watchlist 함수와 상태 key는 바꾸지 않는다.
  비공개 UI key는 `nasdaq_private_review_*`로 격리한다.
- 합성 전체 엔진/파일 불변·최초 누락/실패 fallback/인증·동의·잠금·필터 rerun을 검사한다.
  기존 UI AppTest와 브라우저 스크롤 회귀는 기존 자동 CI로도 실행한다. 실제 비공개
  파일·환경 변수·비밀번호는 CI로 전달하지 않는다.

다음 우선순위는 Draft 검토와 개인 로컬 앱에서 실제 파일 수동 갱신 시연이다. 공개
호스팅의 지속 저장·공개 표출, 새 연결/권한/비용/Secrets, 운영 활성화·서비스 배포에는
별도 사용자 승인이 필요하다.
