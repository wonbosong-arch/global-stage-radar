# 중국 KIS 비공개 자동 수집 연결 (2026-11-03)

## 지원 확인과 한계

기준은 PR #201 병합 SHA `67cff86a4e3ede9130574f2d33fdd86f41111540`.
기존 연구 #197~#200은 가져오거나 수정하지 않았다. 별도 기능 브랜치만 사용한다.
공식 KIS [dailyprice 예제](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/dailyprice/dailyprice.py)는
GET `/uapi/overseas-price/v1/quotations/dailyprice`, TR `HHDFS76240000`,
AUTH/EXCD/SYMB/GUBN/BYMD/MODP와 real/demo 공통 TR을 명시한다.
공식 [거래소 매핑](https://github.com/koreainvestment/open-trading-api/blob/main/backtester/kis_backtest/providers/kis/constants.py)은 Shanghai를 SHS로 연결하고,
[공식 수집 예제](https://github.com/koreainvestment/open-trading-api/blob/main/backtester/kis_backtest/providers/kis/data.py)는 GUBN=0, MODP=1(수정주가)을 사용한다.
이는 해외 **시세** API이며 주문용 `/overseas-stock/v1/trading/order`와 다르다.
거래용 exchange code를 시세 EXCD에 대입하지 않는다.

연구 커밋 `17c409960d54441346e575f4eee04e09c5c63d59`의 collector와
보존 status를 확인했다. 2026-10-28 취득 기록에 대표 12종 모두 SHS,
bars_received=299, latest_date=2026-10-27, 전체 30종 error_count=0이다.
보존된 개인 CSV에는 종목별 299~300행이 있다. 이 기록은 과거 실증이며
현재 배포 계정/권한의 지원 확인과 같지 않다. 이번 세션의 KIS_APP_KEY /
KIS_APP_SECRET 환경변수는 미제공, checkout에는 secret 설정 없음.
현재 라이브 호출은 **0회**, 현재 계정 지원은 미확인이다. 모의 SSE 지원도 추정하지 않는다.

기존 성공 경로 KISUSProvider → KISOverseasPrices.daily_bars를 그대로 사용한다.
실전 도메인은 https://openapi.koreainvestment.com:9443,
인증은 `/oauth2/tokenP` app key/secret → Bearer token, custtype=P.
대표 12종 SHS, GUBN=0, MODP=1, max_pages=3. 단일 client로 순차 처리하며
기존 종목 간/페이지 간 최소 1초 throttle, 최대 4회 가격 요청 시도와 bounded backoff,
EGW00201 처리, 토큰 EGW00133에 한 번 65초 대기를 유지한다.
정상 상한 36페이지이며 실패 재시도까지는 최대 144 price attempts이나 첫 실패 종목에서 중단한다.
계정별 최신 공급자 한도를 수치로 확정하지 않았으며 이 보수적 속도가 권한 보장은 아니다.
기존 Actions 공통 concurrency도 그대로 둔다. 별도 실행기는 같은 직렬화가 필요하다.

## 구현

기존 `refresh_china_candidate_prices.py` 진입점은
`CHINA_KIS_PRIVATE_REFRESH=research`일 때만 새 경로를 선택한다.
미설정이면 기존 30종 연구 동작을 유지한다. 플래그/secret/예약/manifest를 설정하지 않았다.
`CHINA_PRIVATE_SNAPSHOT_DIR`와 collector SHA(`GITHUB_SHA` 또는
`CHINA_COLLECTOR_COMMIT`)가 필요하다. 인증정보는 기존 환경/secret 경로만 사용한다.

새 경로는 공개 checkout 밖 `generations/<uuid>/`에 가격·해시 manifest·Stage report를 쓴다.
12종 전체 응답과 완료 일봉·달력·OHLCV·중복·누락·35개 완료 주봉·최신성·이상치 검사를
통과한 뒤 `current.json`을 atomic replace한다. 부분 실패/짧은 이력/오래된 입력은
이전 포인터를 유지하며 서로 다른 수정주가 스냅샷을 이어 붙이지 않는다.
기존 세대는 보존한다. Stage 계산/이전 Stage/신규 진입은 #201 엔진을 재사용한다.
대시보드는 포인터를 한 번 해석하여 같은 세대의 가격과 manifest를 읽는다.
기존 직접 개인 경로도 호환된다. 모두 operational_eligible=false이며 운영 후보에 편입하지 않는다.
공개 로그에는 집계와 고정 실패문만 출력한다. 비공개 파일은 Git에 추가하지 않는다.

## 호스팅 전달 경로와 승인 후 작업

현재 저장소 workflow는 연구 CSV를 공개 Git에 commit하는 방식이다.
새 비공개 경로는 그 CSV를 쓰지 않으며 기존 git add 대상에도 포함되지 않는다.
기존 workflow/schedule 파일은 변경하지 않았다. 플래그나 경로를 배포하지 않았다.
현재 호스팅의 실제 secret/영구 볼륨/접근 통제는 확인할 수 없다.
Community Cloud checkout와 일회성 GitHub runner는 공유 디스크가 아니므로
runner 임시 경로를 설정하는 것만으로 호스팅 연결 완료라고 할 수 없다.

구현한 무복사 경로는 **접근 제한된 수집기와 대시보드가 공유하는 비공개 영구 볼륨**이다.
수집기는 write, 대시보드는 read 권한으로 같은 디렉터리를 mount하고 위 경로를 설정한다.
가격을 HTTP static directory/공개 artifact/Git에 게시하지 않는다. 대시보드 자체도
비공개여야 한다. 이 구조는 서버 측 파일 생성부터 화면 loader까지 구현되어 있다.
기존 07:00 작업 runner가 그 볼륨에 접근하도록 하는 배포·secret 연결은 승인 후 과제다.
Community Cloud를 계속 쓰려면 별도 인증된 private object storage 전달 backend와
서버 측 fetch/cache를 추가해야 한다. 지원되지 않은 파일 공유를 가장하지 않는다.
수동 가격 파일 복사는 설계상 필요 없지만 **현 호스팅으로 자동 전달은 미구성**이다.

승인 후: 현재 계정으로 512800 한 종목 일봉부터 bounded probe → 12종 확인 →
비공개 저장/화면 접근 통제와 이용권 확인 → 기존 시각/직렬화 유지하는 runner/storage 연결 →
연구 플래그 활성화 및 실제 화면 검증. 현재 단계는 Draft이며 병합/운영 배포/활성화 금지.
현재 접근이 실패했다고 입증된 것은 아니므로 다른 가격 출처는 연결하지 않았다.
공식 SSE 캐시 경로는 연구 대안으로 존재하지만 최신 수정주가·운영 전달 경로를 대신하지 않는다.

## 검증

합성 provider로 12종 수집 → 비공개 저장 → Stage → 실제 dashboard loader를 검증한다.
실패 중단/이전 세대 보존/잘못된 종목·OHLC/오래된 이력/경로 탈출/기본 비활성/로그 비밀 제거 포함.
보존 실제 KIS CSV를 동일 경로에 오프라인 재생: 네트워크 0회, 12종 Stage 준비,
Stage2 2종, 신규 진입 0종. 이 결과는 새로운 실제 KIS 취득이 아니다.
전체 테스트 및 CI 최종 결과는 CODEX_PROGRESS.md와 PR을 참조한다.
