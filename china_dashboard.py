"""China ETF identity metadata only; no market-data loader or activation path."""
import json
from pathlib import Path

RIGHTS_BLOCK = ('중국 연구 가격 사용권 미확인 · 모든 가격 차트·다운로드·Stage 계산 차단. '
                'KIS 및 해당 거래소의 저장·가공·웹 표출·재배포 권한 확인이 필요합니다.')


def research_prices_authorized():
    """Rights cannot be granted by environment, password or local files."""
    return False


def load_research(*args, **kwargs):
    raise PermissionError(RIGHTS_BLOCK)


def load_metadata():
    return json.loads(Path(__file__).with_name('china_sector_metadata.json').read_text(encoding='utf-8'))


def render_china_dashboard(*args):
    import streamlit as st
    st.warning('중국 본토 SSE 연구·관찰 후보 12종 · 운영 비활성 · Stage 판정 보류. '
               'KWEB·CQQQ는 미국 상장 대리지표이며 아래 본토 ETF와 다릅니다.')
    st.error(RIGHTS_BLOCK)
    st.caption('종목·업종·추적지수 식별 정보만 제공합니다. 최신 방법론·중복·주문 가능성은 추가 확인이 필요합니다.')
    for row in load_metadata():
        with st.container(key='china_metadata_' + row['symbol']):
            st.markdown('**' + row['symbol'] + ' · ' + row['sector_category'] + '**')
            st.write(row['name_en'])
            st.caption('SSE · ' + row['tracked_index_code'] + ' · ' + row['tracked_index_name'])
            st.markdown('[상품 공식 출처](' + row['benchmark_source_url'] + ') · '
                        '[지수 공식 출처](' + row['index_source_url'] + ')')
