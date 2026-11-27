"""Private KIS analysis and legacy research explorer; never activates a universe."""
from pathlib import Path
import os
import hashlib
import json
import pandas as pd
from stage_engine import weekly_bars
from unified_stock_explorer import stock_one_year_returns

SNAPSHOT = Path(__file__).resolve().parent / 'research/china_dashboard_snapshot'
NOTICE = ('연구·관찰 후보 · 운영 비활성 · Stage 판정 보류. 실거래 가능성·데이터 이용권·최신 방법론 시행일·'
          '조정주가 미검증. KWEB·CQQQ는 미국 상장 대리지표이며 아래 SSE 본토 ETF와 다릅니다.')


RIGHTS_BLOCK = ('중국 연구 가격 사용권 미확인 · 모든 가격 차트·다운로드·Stage 계산 차단. '
                'KIS 및 해당 거래소의 저장·가공·웹 표출·재배포 권한 확인이 필요합니다.')


def research_prices_authorized():
    """No verified rights grant exists; never infer one from configuration."""
    return False


def load_research(root=None):
    """Explicit private input only; never fall back to repository price files."""
    configured = root or os.environ.get('CHINA_PRIVATE_SNAPSHOT_DIR')
    if not configured:
        raise PermissionError('개인 가격 저장 경로 미설정 · 메타데이터만 표시합니다.')
    if root is None and os.environ.get('CHINA_PRIVATE_OBJECT_TRANSFER') == 'sync':
        from china_private_delivery import configured_transfer
        configured_transfer(configured, 'sync')
    from china_private_pipeline import current_snapshot
    path = current_snapshot(configured)
    repository = Path(__file__).resolve().parent
    if path == repository or repository in path.parents:
        raise PermissionError('가격 경로는 공개 저장소 밖이어야 합니다.')
    from china_kis_stage import load_kis_stage, MANIFEST_FILE
    if (path / MANIFEST_FILE).exists():
        return load_kis_stage(path)
    return _load_reconciled_research(path)


def load_metadata():
    return json.loads(Path(__file__).with_name('china_sector_metadata.json').read_text(encoding='utf-8'))


def _load_reconciled_research(root=SNAPSHOT):
    """Offline validation, failing closed on changed or malformed evidence.

    Reconciliation is not a display authorization.
    """
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    required = {'china_sector_representative_12_selection.csv',
                'china_mainland_30_etf_verification_register.csv',
                'china_candidate_prices.csv', 'official_market_reconciliation.csv'}
    if not required.issubset(manifest['files']):
        raise ValueError('연구 스냅샷 필수 무결성 근거 부족')
    for name, entry in manifest['files'].items():
        if Path(name).name != name or (root / name).resolve().parent != root.resolve():
            raise ValueError('연구 스냅샷 경로 오류')
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
        if symbol == '512400':
            reasons[symbol] = '공식 가격 불일치 미해결 · 차트 및 Stage 차단'
            continue
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
        from china_stage import validated_daily
        try:
            frame = validated_daily(frame, as_of_date='2026-11-03')
        except ValueError as exc:
            reasons[symbol] = '거래일·가격 검증 실패 · 차트 차단: ' + str(exc)
            continue
        previews.append(frame)
        reasons[symbol] = '공식 대사 60일 연구 미리보기 · 운영/Stage 보류'
    preview = pd.concat(previews, ignore_index=True) if previews else prices.iloc[:0].copy()
    candidates['preview_status'] = candidates.symbol.map(reasons)
    # No operational classification from unadjusted/short research history.
    candidates['stage_label'] = '판정 보류 · 연구 전용'
    from china_stage import stage_readiness
    for index, row in candidates.iterrows():
        frame = preview[preview.symbol.eq(row.symbol)]
        if not frame.empty:
            result = stage_readiness(frame, as_of_date='2026-11-03')
            candidates.loc[index, 'preview_status'] += ' · ' + result['stage_reason']
    candidates['stage2_new_entry'] = None
    candidates['operational_eligible'] = False
    return candidates, preview, manifest


def render_china_dashboard(make_chart, split_columns, pager, *, stage_filter_slot=None):
    import streamlit as st
    from asset_table import CHINA_SECTOR_TABLE, DEFAULT_RETURN_SORT, render_asset_table, sorted_rows
    from chart_ui import render_chart_card
    st.caption('연구 · 중국 본토 SSE ETF · CNY · 운영 집계 제외')
    try:
        candidates, preview, manifest = load_research()
    except PermissionError as exc:
        st.info(str(exc))
        st.dataframe(pd.DataFrame(load_metadata()), hide_index=True)
        st.caption('12종 모두 Stage 판정 보류 · 개인 가격 자료가 연결되면 검증된 구간만 표시합니다.')
        return
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.error('연구 자료 검증 실패로 차트를 차단했습니다: ' + str(exc))
        return
    kis_analysis = manifest.get('price_basis') == 'KIS_ADJUSTED'
    as_of = pd.Timestamp.today().normalize()
    if kis_analysis:
        research_note = ('KIS 제공 조정주가 · CNY · 외부 대사/조정 공식 역산은 필수 조건이 아닙니다. '
                         'MA30·4주 기울기·절대 26주 수익률 기반 후보이며 시장 대비 RS가 아닙니다. '
                         '운영 Stage2 목록과 분리된 개인 분석입니다. 외부 재배포 금지.')
        columns = ['symbol', 'stage_label', 'previous_stage_label', 'stage2_new_entry',
                   'completed_weeks', 'ma30', 'slope4_pct', 'ret26_pct', 'preview_status']
        if 'china_kis_stage2_only' not in st.session_state:
            st.session_state['china_kis_stage2_only'] = st.session_state.get('china_kis_stage2_saved', False)
        with stage_filter_slot if stage_filter_slot is not None else st.container():
            only_stage2 = st.checkbox('중국 Stage2 후보만 표시', key='china_kis_stage2_only')
        st.session_state['china_kis_stage2_saved'] = only_stage2
        if only_stage2:
            candidates = candidates[candidates.stage_label.eq('Stage 2 후보')].copy()
        if candidates.empty:
            st.info('현재 조건의 중국 Stage2 후보가 없습니다.')
            return
    else:
        research_note = ('공식 OHLC·거래량 대사 구간 2026-07-28~2026-10-27만 시각화합니다. '
                         '가격은 CNY, 거래량은 ETF 좌수(份)입니다. '
                         '기본 150봉 창이며 검증된 이력은 일봉 60개로 제한됩니다. 마지막 불완전 주봉은 제외합니다. '
                         '512600·515650 공시 기준 관측 중복 49.53%p. 개인 저장 자료 · KIS 해외 일봉 관측(SHS), '
                         '연구 스냅샷 8,905행 · 2025-07-30~2026-10-27 · 외부 재배포 금지 · 운영 비활성. '
                         '공식 SSE 대사는 가격 정확성의 제한된 근거이며 재배포 이용권 승인이 아닙니다.')
    candidates['name'] = candidates['name_en']
    candidates['sector'] = candidates['sector_category']
    candidates['exchange'] = 'SSE'
    candidates['market'] = 'China'
    candidates['asset_type'] = 'sector_etf'
    candidates['price_available'] = candidates.symbol.isin(preview.symbol)
    candidates['ret1y_pct'] = candidates.symbol.map(stock_one_year_returns(preview)) if not preview.empty else None
    if not kis_analysis:
        candidates['last_daily_date'] = '2026-10-27'
    order = st.session_state.get(f'{CHINA_SECTOR_TABLE}_table_sort', DEFAULT_RETURN_SORT)
    candidates = sorted_rows(candidates, *order)
    weekly = {s: weekly_bars(g, as_of_date=as_of if kis_analysis else '2026-11-02', calendar_name='XSHG', min_bars=1)
              for s, g in preview.groupby('symbol')}

    def chart(symbol, **kwargs):
        if symbol not in set(preview.symbol):
            return None
        return make_chart(symbol, daily_data=preview, weekly_data=weekly, **kwargs)

    def pick(symbol):
        st.session_state['china_research_selected'] = symbol
        st.session_state['china_research_view'] = '차트 고정 목록'

    def select_row(_state_key, symbol):
        st.session_state['china_research_selected'] = symbol

    def card(row, key, compact=False):
        blocked = row['preview_status'] if kis_analysis else '공식 가격 불일치 · 차트 및 Stage 계산 차단'
        render_chart_card(row, key, 'china_research_period_' + row.symbol, chart,
                          compact=compact, allow_favorite=False,
                          above=(lambda _row: st.error(blocked)) if not row['price_available'] else None,
                          stock_details=details if not compact else None,
                          below=(lambda r: st.button('개별 차트 ' + r.symbol, key=key + '_open',
                                  on_click=pick, args=(r.symbol,))) if compact else None)

    # Streamlit deletes widget state when another area omits its widgets. Keep
    # the research mode separately, like the existing analysis-area controls.
    if 'china_research_view' not in st.session_state:
        st.session_state['china_research_view'] = st.session_state.get(
            'china_research_view_saved', '차트 고정 목록')
    with st.container(key="china_research_view_picker"):
        view = st.radio('중국 연구 표시 방식', ['차트 고정 목록', '3×3 차트'],
                        key='china_research_view', horizontal=True, label_visibility='collapsed',
                        format_func=lambda value: '목록' if value == '차트 고정 목록' else value)
    st.session_state['china_research_view_saved'] = view
    if view == '차트 고정 목록':
        if st.session_state.get('china_research_selected') not in set(candidates.symbol):
            st.session_state['china_research_selected'] = candidates.iloc[0].symbol
        left, right = split_columns('china_research_analysis_split')
        details = st.container(key='china_research_chart_details')
        with left:
            with st.container(key='china_research_list_card', border=True):
                render_asset_table(candidates, CHINA_SECTOR_TABLE, st.session_state['china_research_selected'],
                                   'china_research_pick', select_row, allow_favorite=False)
        with right:
            selected = candidates[candidates.symbol.eq(st.session_state['china_research_selected'])].iloc[0]
            card(selected, 'china_research_selected_chart')
        details.caption(selected['preview_status'])
    else:
        pages = max(1, (len(candidates) + 8) // 9)
        page = min(max(int(st.session_state.get('china_research_grid_page', 0)), 0), pages - 1)
        st.session_state['china_research_grid_page'] = page
        rows = candidates.iloc[page * 9:(page + 1) * 9]
        with st.container(key='china_research_grid_canvas'):
            for offset in range(0, len(rows), 3):
                for col, (_, row) in zip(st.columns(3), rows.iloc[offset:offset + 3].iterrows()):
                    with col:
                        card(row, 'china_research_grid_' + row.symbol, compact=True)
        pager('china_research', 'china_research_grid_page', page, pages)
    with st.expander('12종 선정·검증 상태 및 출처'):
        st.caption(research_note)
        st.caption('KWEB·CQQQ는 미국 상장 대리지표이며 본토 ETF와 상장 시장이 다릅니다.')
        st.caption('고정 연구 커밋: ' + manifest['research_commit'])
        if kis_analysis:
            st.dataframe(candidates.reindex(columns=columns), hide_index=True)
        st.dataframe(candidates.reindex(columns=['symbol', 'name', 'sector_category', 'tracked_index_code',
                                 'preview_status', 'data_rights', 'adjusted_price_quality',
                                 'latest_methodology_version_status', 'official_source_url']), hide_index=True)


def render_hong_kong_research():
    """Show HKEX metadata and the user's privately generated Stage report."""
    from datetime import datetime
    import streamlit as st
    from china_kis_stage import private_root
    from hong_kong_etf_research import CANDIDATES, HONG_KONG, REPORT_FILE, completed_session

    st.caption('홍콩 상장 ETF 연구 · HKD · MA30·4주 기울기·절대 26주 수익률')
    now = datetime.now(HONG_KONG)
    configured = os.environ.get('CHINA_PRIVATE_SNAPSHOT_DIR')
    results, observed = {}, {}
    if configured:
        try:
            root = private_root(configured)
            path = (root / REPORT_FILE).resolve()
            if path.parent != root:
                raise PermissionError('개인 연구 보고서 경로 오류')
            if path.is_file():
                report = json.loads(path.read_text(encoding='utf-8'))
                summary = report['summary']
                session = completed_session(now).date().isoformat()
                if summary['exchange'] != 'HKS' or summary['currency'] != 'HKD':
                    raise ValueError('시장 정보 불일치')
                if summary['latest_expected_session'] == session:
                    observed = {row['symbol']: row for row in summary['observations']}
                    results = {row['symbol']: row for row in report['results']
                               if row['stage_ready'] is True and row['operational_eligible'] is False
                               and observed.get(row['symbol'], {}).get('status') == 'stage_ready'
                               and observed[row['symbol']]['latest_session'] == session}
                    st.caption(f"분석 기준일 {summary['as_of']} · 최신 거래일 {session}")
                else:
                    st.info('개인 연구 보고서 갱신이 필요합니다.')
        except (OSError, ValueError, TypeError, KeyError):
            st.warning('개인 연구 보고서를 확인할 수 없습니다.')
    if not observed:
        st.caption('개인 KIS 연구 보고서가 연결되면 Stage와 완료 주봉이 표시됩니다.')
    st.dataframe(pd.DataFrame([
        {'티커': symbol.lstrip('0'), '투자 대상': sector, '추종 지수': index,
         'Stage': results.get(symbol, {}).get('stage_label', '판정 보류'),
         '26주 수익률 (%)': results.get(symbol, {}).get('ret26_pct'),
         '완료 주봉': observed.get(symbol, {}).get('completed_weeks')}
        for symbol, (sector, index, _) in CANDIDATES.items()
    ]), hide_index=True)
