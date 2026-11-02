"""Read-only, frozen China research explorer. Never extends an active universe."""
from pathlib import Path
import hashlib
import json
import pandas as pd
from stage_engine import weekly_bars

SNAPSHOT = Path(__file__).resolve().parent / 'research/china_dashboard_snapshot'
NOTICE = ('연구·관찰 후보 · 운영 비활성 · Stage 판정 보류. 실거래 가능성·데이터 이용권·최신 방법론 시행일·'
          '조정주가 미검증. KWEB·CQQQ는 미국 상장 대리지표이며 아래 SSE 본토 ETF와 다릅니다.')


RIGHTS_BLOCK = ('중국 연구 가격 사용권 미확인 · 모든 가격 차트·다운로드·Stage 계산 차단. '
                'KIS 및 해당 거래소의 저장·가공·웹 표출·재배포 권한 확인이 필요합니다.')


def research_prices_authorized():
    """No verified rights grant exists; never infer one from configuration."""
    return False


def load_research(root=SNAPSHOT):
    """No hosted or local UI may expose this unlicensed price snapshot.

    A manifest label, environment flag or password is not a data license.
    Enabling display requires a separately reviewed rights implementation.
    """
    if not research_prices_authorized():
        raise PermissionError(RIGHTS_BLOCK)
    return _load_reconciled_research(root)


def _load_reconciled_research(root=SNAPSHOT):
    """Offline validation, failing closed on changed or malformed evidence.

    Reconciliation is not a display authorization.
    """
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    for name, entry in manifest['files'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('연구 스냅샷 무결성 불일치: ' + name)
    read = lambda name: pd.read_csv(root / name, dtype={'symbol': str})
    selected = read('china_sector_representative_12_selection.csv')
    register = read('china_mainland_30_etf_verification_register.csv')
    if len(selected) != 12 or selected.symbol.nunique() != 12:
        raise ValueError('대표 후보 12종 식별 오류')
    candidates = selected.merge(register, on='symbol', suffixes=('', '_register'), validate='one_to_one')
    if len(candidates) != 12 or not candidates.exchange.eq('SSE').all():
        raise ValueError('SSE 후보 식별 오류')
    prices = read('china_candidate_prices.csv')
    reconciliation = read('official_market_reconciliation.csv')
    previews, reasons = [], {}
    for row in candidates.itertuples():
        symbol = row.symbol
        evidence = reconciliation[reconciliation.symbol.eq(symbol)].copy()
        frame = prices[prices.symbol.eq(symbol)].copy()
        # A single official discrepancy blocks the entire symbol, including 512400.
        valid_evidence = (len(evidence) == 60 and evidence.date.nunique() == 60
                          and evidence.ohlc_matches.astype(str).str.lower().eq('true').all()
                          and evidence.volume_matches.astype(str).str.lower().eq('true').all())
        if not valid_evidence:
            reasons[symbol] = '공식 OHLC 불일치 또는 대사 근거 부족 · 차트 차단'
            continue
        frame = frame[frame.date.isin(evidence.date)].sort_values('date')
        cols = ['open', 'high', 'low', 'close', 'volume']
        frame[cols] = frame[cols].apply(pd.to_numeric, errors='coerce')
        joined = frame.merge(evidence, on=['symbol', 'date'], validate='one_to_one')
        exact = all(joined[c].eq(joined['baseline_' + c]).all() for c in ['open', 'high', 'low', 'close'])
        exact = exact and joined.volume.eq(joined.baseline_volume).all()
        valid = (len(frame) == 60 and not frame[cols].isna().any().any()
                 and frame[['open', 'high', 'low', 'close']].gt(0).all().all()
                 and frame.volume.ge(0).all() and frame.high.ge(frame[['open', 'close', 'low']].max(axis=1)).all()
                 and frame.low.le(frame[['open', 'close', 'high']].min(axis=1)).all())
        if not (exact and valid and row.identity_status == 'verified_official_identity'):
            reasons[symbol] = '가격 구조·공식 신원·스냅샷 대사 검증 실패 · 차트 차단'
            continue
        frame['date'] = pd.to_datetime(frame.date, errors='raise')
        previews.append(frame)
        reasons[symbol] = '공식 대사 60일 연구 미리보기 · 운영/Stage 보류'
    preview = pd.concat(previews, ignore_index=True) if previews else prices.iloc[:0].copy()
    candidates['preview_status'] = candidates.symbol.map(reasons)
    # Do not calculate or import provisional trends: rights/adjustment gates are unverified.
    candidates['stage_label'] = '판정 보류 · 연구 전용'
    candidates['stage2_new_entry'] = False
    candidates['operational_eligible'] = False
    return candidates, preview, manifest


def render_china_dashboard(make_chart, split_columns, pager):
    import streamlit as st
    from chart_ui import render_chart_card
    st.warning(NOTICE)
    try:
        candidates, preview, manifest = load_research()
    except PermissionError:
        st.error(RIGHTS_BLOCK)
        return
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.error('연구 자료 검증 실패로 차트를 차단했습니다: ' + str(exc))
        return
    st.caption('공식 OHLC·거래량 대사 구간 2026-07-28~2026-10-27만 시각화합니다. '
               '가격은 CNY, 거래량은 ETF 좌수(份)입니다. '
               '기본 150봉 창이며 검증된 이력은 일봉 60개로 제한됩니다. 마지막 불완전 주봉은 제외합니다. '
               '512600·515650 공시 기준 관측 중복 49.53%p: 12개 독립 업종을 뜻하지 않습니다.')
    st.caption('가격 출처: KIS 해외 일봉 관측(SHS), 연구 스냅샷 8,905행 · '
               '2025-07-30~2026-10-27 · 권리 승인 근거 없음, 운영 사용 불가. '
               '공식 SSE 대사는 가격 정확성의 제한된 근거이며 재배포 이용권 승인이 아닙니다.')
    st.caption('고정 연구 커밋: ' + manifest['research_commit'])
    candidates['name'] = candidates['name_en']
    candidates['exchange'] = 'SSE'
    candidates['market'] = 'China'
    candidates['asset_type'] = 'sector_etf'
    candidates['price_available'] = candidates.symbol.isin(preview.symbol)
    candidates['last_daily_date'] = '2026-10-27'
    with st.expander('12종 선정·검증 상태 및 출처'):
        st.dataframe(candidates[['symbol', 'name', 'sector_category', 'tracked_index_code',
                                 'preview_status', 'data_rights', 'adjusted_price_quality',
                                 'latest_methodology_version_status', 'official_source_url']], hide_index=True)
    weekly = {s: weekly_bars(g, as_of_date='2026-11-02', calendar_name='XSHG', min_bars=1)
              for s, g in preview.groupby('symbol')}

    def chart(symbol, **kwargs):
        if symbol not in set(preview.symbol):
            return None
        return make_chart(symbol, daily_data=preview, weekly_data=weekly, **kwargs)

    def pick(symbol):
        st.session_state['china_research_selected'] = symbol
        st.session_state['china_research_view'] = '차트 고정 목록'

    def card(row, key, compact=False):
        st.caption(row['name'] + ' · ' + row['sector_category'] + ' · SSE')
        st.caption(row['preview_status'])
        if not row['price_available']:
            st.error('공식 가격 불일치 · 차트 및 Stage 계산 차단')
        render_chart_card(row, key, 'china_research_period_' + row.symbol, chart,
                          compact=compact, allow_favorite=False,
                          below=(lambda r: st.button('개별 차트 ' + r.symbol, key=key + '_open',
                                  on_click=pick, args=(r.symbol,))) if compact else None)

    # Streamlit deletes widget state when another area omits its widgets. Keep
    # the research mode separately, like the existing analysis-area controls.
    if 'china_research_view' not in st.session_state:
        st.session_state['china_research_view'] = st.session_state.get(
            'china_research_view_saved', '차트 고정 목록')
    view = st.radio('중국 연구 표시 방식', ['차트 고정 목록', '3×3 차트'],
                    key='china_research_view', horizontal=True)
    st.session_state['china_research_view_saved'] = view
    if view == '차트 고정 목록':
        if st.session_state.get('china_research_selected') not in set(candidates.symbol):
            st.session_state['china_research_selected'] = candidates.iloc[0].symbol
        left, right = split_columns('china_research_analysis_split')
        with left:
            with st.container(height=520, key='china_research_compact_list'):
                for row in candidates.itertuples():
                    st.button(row.symbol + ' · ' + row.sector_category, key='china_research_pick_' + row.symbol,
                              on_click=pick, args=(row.symbol,), use_container_width=True,
                              type='primary' if row.symbol == st.session_state['china_research_selected'] else 'secondary')
        with right:
            card(candidates[candidates.symbol.eq(st.session_state['china_research_selected'])].iloc[0],
                 'china_research_selected_chart')
    else:
        page = min(max(int(st.session_state.get('china_research_grid_page', 0)), 0), 1)
        st.session_state['china_research_grid_page'] = page
        rows = candidates.iloc[page * 9:(page + 1) * 9]
        with st.container(key='china_research_grid_canvas'):
            for offset in range(0, len(rows), 3):
                for col, (_, row) in zip(st.columns(3), rows.iloc[offset:offset + 3].iterrows()):
                    with col:
                        card(row, 'china_research_grid_' + row.symbol, compact=True)
        pager('china_research', 'china_research_grid_page', page, 2)
