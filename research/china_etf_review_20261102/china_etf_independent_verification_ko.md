# Global Stage Radar 중국 본토 ETF 독립 검증 보고서

검토일: 2026-11-02 (한국시간)  
대상: `wonbosong-arch/global-stage-radar`, `research/antigravity-china-etf`  
고정 커밋: `bdc49995e44b8527c67117191b317408899a47fa`  
교차 비교: PR #192의 검토 시점 head `54799e18712409773f2eac93193ee4168e80e096`

## 판정

**조사 등록부는 수정 후 재검토가 필요하다. “30종 공식 검증 완료”와 “겹치지 않는 12개 거시 업종 대표”라는 결론은 승인할 수 없다.** 30종 전체를 검토했지만, 모든 필드가 공식 자료로 확인됐다는 뜻은 아니다.

- **불일치:** ETF–지수 연결 8건. 512290, 512400, 512660, 512690, 515030, 515120, 515210, 516970이다. 대표 12종 선정표에도 포함된 512400의 코드가 잘못됐다.
- **불일치:** 중국어 법정 상품명 512660·515120·512760, 515650의 자동차 노출 설명, 512600의 지수 종목 상한 설명, “12개 비중복 업종” 주장.
- **확인:** 30개 종목과 12개 선정 종목의 집합·CSV 구조, 12개 60거래일 평균 거래량, 은행·반도체 상관계수의 저장 자료 내 재현성, 전 종목 연구 전용 상태.
- **미검증:** 대부분 지수의 최신 상세 가중·리밸런싱·예외 규정, CES 웹사이트 직접 방법론, 공식 거래소 수치와 일별 거래량 단위 대사, 조정주가·거래일 완전성·한국 증권사 현재 주문 가능 여부·데이터 이용권.

**권고:** 연구 전용 상태를 유지하고, P0의 잘못된 연결과 검증 상태를 먼저 정정한다. 대표 12종은 업종·하위업종·테마를 구분한 잠정 관찰 목록으로만 사용한다.

## 1. 검토 기준과 자료 고정

판정은 필드별이다. **확인**은 공식 본문 또는 공식 문서의 검색색인 본문에서 해당 주장을 확인했다는 뜻이며, **불일치**는 기재와 공식 내용이 충돌한다는 뜻이다. **미검증**은 접근 실패·근거 부족·버전 불명 등으로 판정할 수 없다는 뜻이다. 개요나 명칭을 확인했다고 상세 방법론 전체를 확인한 것으로 올리지 않았다.

읽은 연구 자료는 [30종 등록부](https://github.com/wonbosong-arch/global-stage-radar/blob/bdc49995e44b8527c67117191b317408899a47fa/research/china_mainland_30_etf_verification_register.csv), [12종 선정표](https://github.com/wonbosong-arch/global-stage-radar/blob/bdc49995e44b8527c67117191b317408899a47fa/research/china_sector_representative_12_selection.csv), [29행 지수 근거표](https://github.com/wonbosong-arch/global-stage-radar/blob/bdc49995e44b8527c67117191b317408899a47fa/research/china_index_official_methodology_evidence.csv), 가격 CSV·수집 상태·기존 6종 비교표·추가 테스트다. 대조 대상 [PR #192](https://github.com/wonbosong-arch/global-stage-radar/pull/192)는 Draft/open이며, 독립 검증과 운영 승격을 구분하고 있다.

GitHub의 커밋 메타데이터상 대상 커밋의 직접 부모가 위 PR head와 같다. 따라서 새 조사 결과는 PR 자료와 독립적인 두 번째 출처가 아니라, 그 자료 위에 추가한 결과다. 이번 보고서에서는 외부 공식 문서 대조와 원시 수치 재계산을 별도로 수행했다. 원격 브랜치 등록부의 blob SHA도 고정 커밋의 `e210eda94fb911ef2c17b4e0ea5a429c2f5f174a`와 일치했다. 이것만으로 원격 브랜치의 전체 head SHA까지 동일하다고 주장하지 않는다.

공식 웹페이지는 동적이고 PDF의 동일 URL도 갱신될 수 있다. 직접 열람이 실패한 일부 문서는 공식 도메인의 검색색인 본문으로 보완했다. 색인의 게시일·수집일을 문서 발행일이나 최신성의 증명으로 사용하지 않았다. 모든 상세 방법론의 2026-11-02 현재 최신 버전을 확정한 감사는 아니다.

## 2. 우선 정정할 지수 연결 8건

| ETF | 등록된 코드 | 공식 자료에 맞는 코드·지수 | 확인한 충돌 |
|---|---|---|---|
| 512290 | 399441 | **930726 · 中证生物医药指数** | 상품의 생물의약 지수명과 코드 불일치 |
| 512400 | 930607 | **000819 · 中证申万有色金属指数** | 선정표에도 잘못된 코드 전파 |
| 512660 | 399973 | **399967 · 中证军工指数** | 军工과 国防을 혼동; 상품명까지 잘못 기재 |
| 512690 | 930606 | **399987 · 中证酒指数** | 930606 공식 PDF는 술이 아니라 철강 |
| 515030 | 930997 | **399976 · 中证新能源汽车指数** | 新能源汽车와 新能源汽车产业는 별도 지수 |
| 515120 | 931140 | **931152 · 中证创新药产业指数** | 931140 공식 PDF는 中证医药50指数 |
| 515210 | 930608 | **930606 · 中证钢铁指数** | 930608 공식 PDF는 中证基建指数 |
| 516970 | 930616 | **399995 · 中证基建工程指数** | GF 공시와 CSI 방법론이 399995를 명시 |

각 정정은 아래 30종 표의 상품 공시와 지수 링크로 추적할 수 있다. 특히 930606·931140·930608은 **URL이 열리지만 다른 지수 본문을 보여주는 경우**다. 접근 성공 여부만 검사하는 방식으로는 잡히지 않는다.

515030은 [2026-05-29 상품자료](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-05-29/515030_20260529_8GVO.pdf)가 中证新能源汽车指数를 명시하고, [운용사 모집설명서의 지수 부록](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-11-24/515030_20251124_YULO.pdf)이 399976을 기재한다. [CSI 399976](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399976factsheet.pdf)과 [CSI 930997](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/930997factsheet.pdf)도 서로 다른 명칭과 표본 설명을 제공한다.

## 3. 30종 전수 대조표

상품명은 읽기 쉬운 중국어 약칭이다. “명칭 확인”은 이 표에 적은 식별 수준이며, 모든 영문 번역을 현재 법정명으로 승인한다는 뜻은 아니다. 운용사 중국어 표기는 30종 모두 공식 목록·공시와 대조해 확인했다. 전체 원문 필드·개별 URL·접근 결과는 동봉한 `china_etf_independent_audit_30.csv`에 있다.

지수 코드는 정정 후 기준이다. 표의 **범위 확인과 상세 방법론 완전 확인은 구별**한다. H30184는 선정·가중·정기조정 본문까지 읽었다. 나머지는 아래 4절의 제한을 적용한다.

| ETF | 상품 약칭 / 운용사 | 명칭 판정 | 지수 코드 판정·공식 출처 | 방법론·범위 대조 |
|---|---|---|---|---|
| 512010 | [易方达沪深300医药卫生 / 易方达](https://cdn.efunds.com.cn/owch/data/bulletin/20260328/易方达沪深300医药卫生交易型开放式指数证券投资基金更新的招募说明书.pdf?from=person) | 확인 | 확인 · [000913](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000913factsheet.pdf) | CSI300 구성종목의 의료보건; 전체 A주 의료보건보다 좁음 |
| 512170 | [华宝中证医疗 / 华宝](https://www.fsfund.com/fund/512170/fundDetail.shtml) | 확인 | 확인 · [399989](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399989factsheet.pdf) | 의료기기·의료서비스·의료정보화; 순수 서비스만 아님 |
| 512200 | [南方全指房地产 / 南方](https://www.nffund.com/new/personal-financing/detail.html?fundCode=512200) | 확인 | 확인 · [931775](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931775factsheet.pdf) | 전지수 부동산 업종 |
| 512290 | [国泰生物医药 / 国泰](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2023-07-21/512290_20230721_2D8M.pdf) | 확인 | 불일치 · [930726](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/930726factsheet.pdf) | 세포의료·유전자·혈액제제·생물의약·백신·체외진단 |
| 512400 | [南方申万有色金属 / 南方](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-03-12/512400_20260312_O8AZ.pdf) | 확인 | 불일치 · [000819](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000819factsheet.pdf) | 신완 비철금속 및 비금속재료 50종목; 전체 소재 아님 |
| 512480 | [国联安半导体 / 国联安](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-01-22/512480_20260122_IWNM.pdf) | 확인 | 확인 · [H30184](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/H30184factsheet.pdf) | 반도체 제품·장비; 거래대금 하위10%와 누적시총90% 이후 제외; 종목상한15%; 반기 |
| 512580 | [广发环保 / 广发](https://www.gffunds.com.cn/funds/?fundcode=512580) | 확인 | 확인 · [000827](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000827factsheet.pdf) | 자원관리·청정기술/제품·오염관리; 단순 폐기물 테마 아님 |
| 512600 | [嘉实主要消费 / 嘉实](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-06-24/512600_20250624_FOQK.pdf) | 확인 | 확인 · [000932](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000932factsheet.pdf) | CSI800 필수소비; 기존 공식 방법론 상한10%와 등록부15% 충돌 |
| 512620 | [天弘农业 / 天弘](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-06-26/512620_20260626_JDV7.pdf) | 확인 | 확인 · [000949](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000949factsheet.pdf) | 농산물·농기계·비료/농약·가축약품 등 50종목 |
| 512660 | [国泰军工 / 国泰](https://www.gtfund.com/product/productlist/zhishu/512663/summary/index.html) | 불일치 | 불일치 · [399967](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399967factsheet.pdf) | 군공그룹 및 군수사업 대표기업; 국방399973과 별도 |
| 512690 | [鹏华酒 / 鹏华](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-03-04/512690_20260304_2X3X.pdf) | 확인 | 불일치 · [399987](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399987factsheet.pdf) | 백주·맥주·와인 등; 철강930606과 별도 |
| 512700 | [南方银行 / 南方](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-04-22/512700_20250422_ETPM.pdf) | 확인 | 확인 · [399986](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399986factsheet.pdf) | 전지수 은행 업종; 512800과 동일 지수 |
| 512720 | [国泰计算机主题 / 国泰](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-04-22/512720_20260422_EOEE.pdf) | 확인 | 확인 · [930651](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/930651factsheet.pdf) | IT서비스·응용/시스템소프트웨어·컴퓨터 하드웨어 포함 |
| 512760 | [国泰CES半导体芯片 / 国泰](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-03-29/512760_20250329_58R6.pdf) | 불일치 | 확인 · [990001](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/990001factsheet.pdf) | 상하이·선전 반도체 소재/장비/설계/제조/패키징/테스트; CES 직접 방법론 미열람 |
| 512800 | [华宝银行 / 华宝](https://www.fsfund.com/fund/512800/fundDetail.shtml) | 확인 | 확인 · [399986](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399986factsheet.pdf) | 전지수 은행 업종; 512700과 동일 지수 |
| 512880 | [国泰证券公司 / 国泰](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-04-22/512880_20260422_R2T8.pdf) | 확인 | 확인 · [399975](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399975factsheet.pdf) | 증권회사 세부업종; 금융 전체 아님 |
| 512980 | [广发传媒 / 广发](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-01-22/512980_20260122_DOBT.pdf) | 확인 | 확인 · [399971](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399971factsheet.pdf) | 광고·문화오락·디지털미디어 50종목; 통신서비스 전체 아님 |
| 515030 | [华夏新能源汽车 / 华夏](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-05-29/515030_20260529_8GVO.pdf) | 확인 | 불일치 · [399976](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399976factsheet.pdf) | 리튬배터리·충전설비·신에너지 완성차; 산업930997과 별도 |
| 515050 | [华夏5G / 华夏](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-01-12/515050_20260112_2B1L.pdf) | 확인 | 확인 · [931079](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931079factsheet.pdf) | 5G 구축·단말·응용의 복수업종 테마 |
| 515070 | [华夏人工智能 / 华夏](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-03-23/515070_20260323_KBOS.pdf) | 확인 | 확인 · [930713](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/930713factsheet.pdf) | AI 기초자원·기술·응용 50종목 |
| 515120 | [广发创新药 / 广发](https://www.gffunds.com.cn/funds/?fundcode=515120) | 불일치 | 불일치 · [931152](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931152factsheet.pdf) | 혁신의약 R&D 기업; 의약50 931140과 별도 |
| 515170 | [华夏细分食品饮料 / 华夏](https://www.chinaamc.com/upload/resources/file/2026/04/22/3b86510829934e7fac305e356ca4b48f.pdf) | 확인 | 확인 · [000815](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000815factsheet.pdf) | 규모·유동성 기준 식음료 세부산업 |
| 515210 | [国泰钢铁 / 国泰](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-03-21/515210_20250321_N4I3.pdf) | 확인 | 불일치 · [930606](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/930606factsheet.pdf) | 철강; 인프라930608과 별도 |
| 515220 | [国泰煤炭 / 国泰](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-03-19/515220_20260319_DP5F.pdf) | 확인 | 확인 · [399998](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399998factsheet.pdf) | 석탄채굴·가공; 석유·가스 또는 발전사 전체 아님 |
| 515650 | [富国消费50 / 富国](https://www.fullgoal.com.cn/wbs-file/fund_report/20260323/CN_50100000_515650_FA010080_20260003.pdf) | 확인 | 확인 · [931139](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931139factsheet.pdf) | 필수+재량소비 혼합; 승용차/부품 제외; 규모와 경영품질 고려 |
| 515790 | [华泰柏瑞光伏 / 华泰柏瑞](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-04-22/515790_20260422_0XZ8.pdf) | 확인 | 확인 · [931151](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931151factsheet.pdf) | 태양광 상중하류; 산업재/유틸리티 혼합 |
| 515880 | [国泰通信设备 / 国泰](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-04-22/515880_20260422_W9TD.pdf) | 확인 | 확인 · [931160](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931160factsheet.pdf) | 통신장비; 통신서비스와 공식 분류관계 기록 필요 |
| 516150 | [嘉实稀土 / 嘉实](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-01-22/516150_20260122_6I3V.pdf) | 확인 | 확인 · [930598](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/930598factsheet.pdf) | 희토류 채굴·가공·무역·응용 |
| 516160 | [南方新能源 / 南方](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-04-01/516160_20260401_Y2LG.pdf) | 확인 | 확인 · [399808](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399808factsheet.pdf) | 신재생 생산·응용·저장·상호작용설비; 공식 산업재 비중 높음 |
| 516970 | [广发基建工程 / 广发](https://www.gffunds.com.cn/funds/?fundcode=516970) | 확인 | 불일치 · [399995](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399995factsheet.pdf) | 건축/엔지니어링 및 인테리어; 인프라930608과도 별도 |

### 법정명·영문명에서 추가로 확인한 문제

- **512660:** 등록부의 `国泰中证国防安全…` 대신 운용사 상품은 **国泰中证军工交易型开放式指数证券投资基金**이다. 399973의 실제 이름도 “国防安全”이 아니라 中证国防指数다. [국태 상품 개요](https://www.gtfund.com/product/productlist/zhishu/512663/summary/index.html), [CSI 399967](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399967factsheet.pdf), [CSI 399973](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399973factsheet.pdf).
- **515120:** `广发中证细分名牌大药房/名优大药产业主题…`는 공식 법정명이 아니다. 공식 GF 상품명은 **广发中证创新药产业交易型开放式指数证券投资基金**이다. SSE 영문 적격목록의 “Brand Name Drug”를 중국어 법정명이나 지수명으로 역번역하면 안 된다. [GF 공식 상품 본문](https://www.gffunds.com.cn/funds/?fundcode=515120).
- **512760:** 대상 파일의 긴 중국어 명칭과 달리, 등록부가 직접 인용한 2024 연차보고서 표지·§2.1은 **国泰CES半导体芯片行业交易型开放式指数证券投资基金**을 사용한다. §2.2의 비교지수도 中华交易服务半导体芯片行业指数다. 영문 상장 별칭·중국어 법정명을 별도 관리해야 한다. [해당 연차보고서](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-03-29/512760_20250329_58R6.pdf).
- **512480:** 중국어 운용사 国联安는 최신 SSE 중국어 공시와 맞는다. 다만 SSE 영문 적격목록은 여전히 CPIC라는 표현을 사용한다. PR #192가 기록한 이 명칭 차이를 보존하고, CPIC 표기만으로 별도 운용사라고 단정하지 않는다. [SSE 중국어 청약·환매 목록](https://www.sse.com.cn/disclosure/fund/etflist/detail.shtml?fundid=512480), [SSE 영문 목록](https://english.sse.com.cn/access/via/eligible/).

## 4. 근거 URL과 방법론 상태의 실제 의미

### 등록부의 상품 근거 URL

30개 URL을 모두 열어 보았다.

| URL 유형 | 수 | 이번 직접 열람 결과 |
|---|---:|---|
| SSE `basic/index.shtml?FUNDID=…` | 25 | 23개는 페이지 틀만 반환, 515210·516160은 접근 실패 |
| SSE PDF | 5 | 512600·512620·512700·512760은 본문 확인; 512480은 직접 열람 실패 후 같은 공식 문서의 검색색인 본문과 대체 공시로 보완 |

페이지 틀만 나온 것은 URL이 가짜라는 증거가 아니다. 동적 페이지·수집 도구의 한계일 수 있다. 그러나 **그 결과를 공식 상품·지수 확인의 증거로 쓸 수도 없다.** 보고서는 운용사 본문 및 정적 PDF로 보완했다. 예를 들어 [512170 화바오](https://www.fsfund.com/fund/512170/fundDetail.shtml)와 [512800 화바오](https://www.fsfund.com/fund/512800/fundDetail.shtml)는 실제 명칭·관리회사·비교지수를 제공한다.

### 방법론 근거표의 과장

29개 고유 지수 행을 갖춘 점은 구조적으로 맞지만, 은행 지수와 000913의 두 행을 제외한 27행의 `methodology_evidence_url`은 대부분 CSI 해시 경로 또는 CES 상세페이지다. 표본선정·가중·상한·조정일을 담은 정적 방법론 파일을 보관한 구조가 아니다. `official_index_methodology_located`와 등록부의 `verified_csi_official`은 동일한 검증 수준도 아니다.

- **H30184: 확인.** [2024-11 V1.2 방법론](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/H30184_Index_Methodology_cn.pdf)은 전지수 표본공간, 반도체 사업 조건, 거래대금 하위 10%와 누적 시총 90% 이후 제외, 조정시총 방식·종목 상한 15%, 6월·12월 조정을 명시한다. 등록부의 일반적 반도체 설명보다 이 규칙을 저장하는 것이 재현 가능하다.
- **399989: 범위 확인, 상세 전체는 미검증.** [2023-12 V1.2 방법론](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/20231208175354-399989_Index_Methodology_cn.pdf)은 의료기기·서비스·의료정보화와 유동성 필터를 명시한다. “의료서비스만”이라는 축약은 좁다. 이 검토에서는 최신 가중·예외 조항 전체를 확정하지 않았다.
- **000932: 불일치/버전 대조 필요.** 등록부 근거표는 종목 상한 15%라고 썼다. [CSI 800 업종 방법론의 공식 검색색인 본문](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000841_Index_Methodology_cn.pdf)에는 000932/399932 상한이 **10%**로 명시돼 있다(2022-04 V1.3). 새 규칙이 있다면 발효일과 새 문서를 제시해야 한다. 현재 근거로 15%를 확인 처리할 수 없다. 이 지수는 CSI800 필수소비로, 전 A주 전체가 아니다.
- **931139: 선정 근거 불일치.** [CSI 방법론](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/20231208180420-931139_Index_Methodology_cn.pdf)의 선정 항목은 시총뿐 아니라 매출·ROE·매출총이익률을 포함하고, 승용차·부품을 제외한다. [2026-09-30 factsheet](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931139factsheet.pdf)도 필수·재량소비 혼합이며 필수소비 56.5%, 재량소비 43.5%를 보여준다. 선정표의 “auto components”와 순수 재량소비 분류는 고쳐야 한다.
- **000949·000819·399995: 명칭·표본범위 확인.** 공식 방법론을 추가로 찾았다. [농업 2023-12 V1.4](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/20231208175430-000949_Index_Methodology_cn.pdf), [비철 2023-12 V1.3](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/20231208175400-000819_Index_Methodology_cn.pdf), [기건공정 2023-12 V1.3](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/20231208175441-399995_Index_Methodology_cn.pdf). 이 보고서는 모든 최신 가중·예외 조항에 대한 완전 확인으로 올리지 않았다.
- **은행 399986: 지수 일치 확인, 상세 최신 규칙은 일부 미검증.** 두 상품의 운용사 공시와 CSI factsheet가 동일 지수를 가리킨다. PR의 H30199 통합 업종 방법론은 이번 직접 열람이 반복 실패했고 검색색인에서는 선정규칙 일부만 확인했다. 별첨의 은행 상한·최신 예외까지 이번 감사에서 새로 완전 검증했다고 하지 않는다.
- **CES 990001: 직접 방법론 미검증.** 등록된 CES 상세 URL은 접근할 수 없었다. 대신 [CSI 공식 factsheet](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/990001factsheet.pdf)가 이름·코드·상하이/선전 반도체 범위·반기 조정을 뒷받침한다. “cross-market”을 홍콩 종목 포함으로 해석하면 안 된다. CES 직접 문서의 최신 선정·가중 규칙과 위탁 계산 관계는 남아 있다.
- **그 밖의 지수:** factsheet에서 명칭·코드·대표 범위·반기 조정 등을 부분 확인한 수준이다. factsheet는 전체 선정·가중 방법론을 대신하지 않는다. 상세 상태는 미검증으로 유지해야 한다.

문서 버전 충돌도 기록해야 한다. 예를 들어 515030 운용사 모집설명서 부록과 CSI factsheet의 표본 수 설명이 다르므로, 코드 정정과 별도로 최신 규칙의 시행 시점을 확인해야 한다. 문서가 공식이라는 이유만으로 서로 다른 시점의 내용을 합쳐 하나의 최신 방법론으로 만들면 안 된다.

## 5. 대표 12종 선정 타당성

아래 판단은 **연구 관찰 목록에 남길지**에 관한 것이며, 현재 Stage 2·매수 후보·운영 활성화 판정이 아니다.

| 선정 ETF | 독립 판단 | 수정할 설명·추가 근거 |
|---|---|---|
| 512800 은행 | 잠정 유지 타당 | 동일 399986 중 한 개를 남기는 판단은 합리적. 거래량 우위는 재현되지만 거래대금·스프레드·추적오차 필요 |
| 512880 증권 | 하위업종으로 유지 | 금융 전체 대표가 아니다. “Unrivaled”는 전체 시장 경쟁상품 조사가 없어 입증되지 않음 |
| 512600 필수소비 | 잠정 유지 | CSI800 기반임을 명시. 515650과 중복 정도를 측정해야 함 |
| 515650 소비50 | 분류 재작성 필요 | 필수+재량소비 혼합, 승용차/부품 제외. 순수 재량소비 대용으로 승인 불가 |
| 512010 의료보건 | 대형주 제한을 붙여 유지 | CSI300 안의 의료보건. 전체 본토 의료보건 시장 대표성은 별도 검토 |
| 512480 반도체 | 잠정 유지 | 업종 관찰용 후보 선택과 현재 추세 적격성을 분리. 512760과 다른 지수임을 보존 |
| 512720 컴퓨터 | 명칭 범위 수정 후 유지 | 소프트웨어/서비스 전용이 아니라 하드웨어도 포함 |
| 512980 미디어 | 미디어 하위업종으로 유지 | 광고·오락·디지털미디어를 전체 통신서비스로 확대하지 말 것 |
| 512200 부동산 | 잠정 유지 타당 | 후보 30개 안의 유일한 광역 부동산 후보라는 제한된 근거는 성립 |
| 512400 비철금속 | **코드 정정 후** 하위업종 유지 | 000819. 철강·화학·건자재를 모두 포괄하는 전체 소재 대표가 아님 |
| 515220 석탄 | 석탄 하위업종으로 유지 | 석유·가스·전력 생산 전체를 포괄하지 않음 |
| 516160 신에너지 | 복수업종 테마로 재분류 | 태양광·저장·설비 등에 걸친 테마. CSI factsheet 산업재 76.3%, 원재료 12.5%, 유틸리티 11.3%(2026-09-30) |

분류 판단의 공식 근거: [소비50](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931139factsheet.pdf), [컴퓨터](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/930651factsheet.pdf), [미디어](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399971factsheet.pdf), [비철](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000819factsheet.pdf), [석탄](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399998factsheet.pdf), [신에너지](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399808factsheet.pdf).

등록부 자체의 `sector_category`도 12개 선정 종목에 **9개 범주**만 있다. 금융·IT·에너지가 각각 둘이고, 산업재와 유틸리티의 독립 광역 대표는 없다. 여러 하위업종을 관찰하는 설계는 가능하지만 이를 “12개 서로 겹치지 않는 거시 업종”이라고 설명할 수는 없다.

**은행과 반도체 중복 해소는 구분해야 한다.**

- 은행: 512700·512800은 같은 지수를 추종하므로 `same_index_alternative` 또는 동일 지수 중복으로 처리할 근거가 있다.
- 반도체: H30184·990001은 **서로 다른 지수**다. 높은 수익률 상관관계로 신호 수를 줄이는 것은 합리적이지만, `hold_duplicate`를 동일 지수나 동일 구성종목이라는 의미로 쓰면 틀린다. `high_correlation_alternative`처럼 이유를 구분하고, 동일 기준일 구성종목별 최소 가중치 합계 등으로 실제 보유 중복률을 측정해야 한다.
- 512600·515650은 소비주를 공유할 수 있다. 지수 코드 12개가 서로 다르다는 테스트는 이 중복을 검사하지 않는다. 12종 전체의 구성종목·업종 비중 행렬이 없어 “비중복”은 미검증이다.

## 6. 거래량·상관계수 재계산

[고정 커밋의 원시 가격 CSV](https://github.com/wonbosong-arch/global-stage-radar/blob/bdc49995e44b8527c67117191b317408899a47fa/data/china_candidate_prices.csv)는 **8,905행·30종목**, 마지막 날짜는 모두 **2026-10-27**이다. [수집 상태 JSON](https://github.com/wonbosong-arch/global-stage-radar/blob/bdc49995e44b8527c67117191b317408899a47fa/data/china_candidate_prices_status.json)은 2026-10-28 수집과 KIS 반환 자료라는 출처를 기록한다.

날짜 중복, 날짜 역전, OHLC 범위 위반, 비양수 가격, 비정상/음수 거래량을 독립 재검사했으며 해당 위반은 발견되지 않았다. 512620은 **224행, 2025-11-21~2026-10-27**이다. [SSE 상장 공지](https://etf.sse.com.cn/disclosure/ssenotice/c/c_20251121_10799250.shtml)의 상장일과 첫 관측일도 맞는다. 이것은 거래일 누락·조정주가·매매 가능성을 검증한 결과가 아니다.

최근 **60개 관측 거래일(2026-07-28~2026-10-27)**의 `volume` 산술평균을 계산해 반올림하면 선정표 12개 값이 모두 일치한다.

| ETF | 저장 거래량의 60관측일 평균(반올림) |
|---|---:|
| 512800 | 1,237,170,554 |
| 512880 | 1,554,631,877 |
| 512600 | 22,792,223 |
| 515650 | 70,306,377 |
| 512010 | 1,104,018,219 |
| 512480 | 1,408,454,320 |
| 512720 | 24,160,198 |
| 512980 | 415,377,819 |
| 512200 | 151,200,668 |
| 512400 | 498,152,136 |
| 515220 | 622,868,496 |
| 516160 | 57,528,585 |

- 은행 거래량 비율: 512800 / 512700 = **17.1231배**.
- 반도체 거래량 비율: 512480 / 512760 = **3.4991배**.
- 종목별 종가 일간 단순수익률을 계산한 뒤 공통 날짜 298개로 Pearson 상관을 구하면 은행 **0.9827867**, 반도체 **0.9950151**이다. 기존 0.9828·0.9950과 일치한다.

**수치 재현은 확인, 유동성 우월성의 최종 판정은 미검증**이다. 원시 `volume`의 거래소 단위 변환, 거래대금, 호가 스프레드, 주문 규모 대비 시장 깊이, ETF 규모와 추적오차를 대사하지 않았다. 가격·1좌 단위가 다른 ETF의 수량 거래량만으로 “확정적 대표”, “시장 내 최고 유동성”을 선언할 수 없다. 또한 이 값은 11월 2일 현재 60일 수치가 아니라 10월 27일 종료 스냅샷이다.

## 7. PR #192와의 교차 비교

| 항목 | PR #192 | 대상 커밋 | 독립 판단 |
|---|---|---|---|
| 조사 기반 | 17개 기존 + 12개 보완 + 512620 | 30행으로 통합 | 종목 집합 정리는 타당 |
| 공식 방법론 | 2행 근거표, 다수 pending | 29행 근거표, 전종목 verified | 근거 수준을 일괄 상향할 근거 부족 |
| 은행 | 512800 우선 연구, 512700 중복 보류 | 동일 | 방향과 수치 재현 |
| 의료 | 000913·399989 구분 | 512010 대표 선정 | 대형주 의료 vs 의료 테마 구분 유지 타당 |
| 반도체 | 별도 지수·고상관, 현재 Stage2 미충족 | 512480 선정, 512760 duplicate 보류 | 연구 목록 선정은 가능. 동일 지수 중복으로 읽히지 않게 수정 |
| 512480 명칭 | 기존 identity CSV는 国联安로 정정; 일부 과거 분석 CSV는 CPIC 잔존 | 새 등록부는 国联安, 기존 6종 표는 CPIC 잔존 | 동일 종목의 표기 이력·별칭 정리 필요 |
| 승격 게이트 | 전부 비활성, 은행 이외 방법론 false | 기존 게이트 파일은 그대로이나 새 등록부 전부 verified | 파일 간 상태 충돌. 한쪽을 자동 우선하지 말고 문서 단위로 재판정 |
| 조정주가·주문·권리 | 미완료 | 미완료 | 연구 전용 유지가 맞음 |

8개 잘못된 지수 연결은 PR #192의 2행 방법론 근거표가 확인해 준 내용이 아니다. 새로 확장한 표의 내부 코드 커버리지를 공식 검증으로 오인하면 안 된다. 반면 PR #192의 pending 상태 또한 외부 문서가 틀렸다는 증거는 아니다.

대상 커밋에서 변경된 것은 연구 CSV·연구 문서·테스트 및 기존 6행 표의 쉼표 인용 수정이다. 자동 수집·Stage 계산·운영 앱 변경은 해당 커밋의 7개 변경 파일에 포함되지 않는다.

## 8. CSV와 테스트에 대한 평가

- 30행 등록부(20열), 12행 선정표(12열), 29행 방법론표(9열), 기존 6행 대표표(19열)는 열 수가 일치했다.
- 새 `backup_china_sector_representative_review_expanded.csv`는 15행이며, **6행에서 열 초과**가 발생한다: 파일 3·5·11·12·14·16행. 19열 헤더에 각각 20·20·22·22·23·22개 필드가 들어간다. “보존한 백업”도 안전한 CSV 입력으로 재사용할 수 없는 상태다.
- 추가 테스트의 `test_selected_representatives_have_distinct_sectors`는 실제로 **지수 코드의 유일성**만 검사한다. 업종 유일성·성분 중복·공식 문서 내용은 검사하지 않는다.
- `identity_status`·`index_methodology_status`가 `verified_`로 시작하는지, URL이 HTTPS인지 확인하는 테스트는 잘못된 코드와 문서 본문을 탐지하지 못한다. 오히려 불확실한 행을 verified로 유지하도록 강제할 수 있다.
- 원본이 말하는 23개 테스트 통과는 이번 보고서에서 재실행·재인증하지 않았다. 이번에 독립 실행한 검증은 CSV 구조·종목 집합·원시 가격 기본 구조·거래량·상관계수 재계산이다. 외부 공식 자료의 정확성은 별도로 판정했다.

## 9. 우선순위별 수정 권고

| 우선순위 | 수정 항목 | 완료 기준 |
|---|---|---|
| **P0** | 8개 ETF–지수 코드·명칭 정정 | 등록부·방법론표·12종표·연구 문서의 연결이 모두 공식 공시와 일치. 512400은 선정표까지 수정 |
| **P0** | 512660·515120·512760 법정명 정정 | 중국어 법정명, 영문 상장명, 과거 별칭을 별도 필드로 기록 |
| **P0** | “30종 검증 완료” 및 일괄 verified 철회·세분화 | 상품 신원/추종관계/지수명코드/선정/가중/조정/구성종목 상태를 분리. 미열람은 pending |
| **P1** | 방법론 URL과 문서 버전 보강 | 정적 PDF·제목·발행일·버전·시행일·페이지/절·확인 문장·열람일·사본 해시를 저장 |
| **P1** | 000932의 상한 15% 근거 정정 | 10%와 다른 최신 규칙을 주장하려면 공식 발효 문서 제시. 그렇지 않으면 15% 삭제 |
| **P1** | 12종 대표성 설명 수정 | 515650 혼합소비/자동차 제외, 512400 비철, 512980 미디어, 515220 석탄, 516160 복수업종 테마 명시 |
| **P1** | 중복 해소 기준 분리 | 동일 지수와 고상관 대안을 구분. 12종 구성종목·가중중복·산업 비중 표 작성 |
| **P1** | 거래량 출처·단위·기간 명시 | KIS 단위와 SSE 일별 자료 대사; 동일 기간 거래대금·스프레드·추적오차로 보완 |
| **P1** | 현재 추세와 대표 목록 선정 분리 | 대표 ETF가 현재 Stage2 통과라는 오해를 방지. 조정주가 검증 후 추세 평가 |
| **P2** | CSV 백업 6행 수정 및 검증 | 모든 보관 CSV에 헤더 길이·누락/초과 열 검사 |
| **P2** | 테스트의 주장 범위 수정 | 코드 유일성 테스트 이름 정정, 고정 공식 fixture로 실제 매핑 오류 탐지 |
| **P2** | 운영 전 미완료 게이트 유지 | 주문 가능 여부·조정주가·거래일 완전성·데이터 이용권을 별도 확인 |

## 10. 수행 범위와 남은 미검증

보고서·감사 CSV·읽기 전용으로 가져온 사본만 이 작업 폴더에 작성했다. **main, data-validation-mvp, PR #192, 운영 대시보드, 원격 브랜치를 수정하지 않았고 커밋·푸시·병합·PR 댓글 게시도 하지 않았다.**

이번 전수 검토로 8개 지수 연결 오류와 대표성·근거 수준 문제는 구체적으로 확인했다. 그러나 30개 상품의 모든 최신 방법론·성분종목·주문 가능성까지 완전 검증됐다고 결론내릴 수 없다. 접근 실패와 문서 시점 차이는 “미검증”으로 남겼으며, 운영 승격 조건은 충족되지 않았다.

