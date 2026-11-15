"""Read-only weekly presentation of existing, guarded screening results.

No provider calls, Stage reclassification, historical-universe reconstruction or
sample values. Comparisons use the current displayed universe at one common week.
"""
from math import isfinite

import pandas as pd

from favorite_assets import asset_id

STAGE2 = 'Stage 2 후보'
VALID_STAGES = {STAGE2, 'Stage 2A 관찰 후보', '중립 / 추가 확인', '하락 추세 관찰'}
UNAVAILABLE = '비교 불가'


def number(value):
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (ValueError, TypeError):
        return None


def weekly_snapshot(screen, weekly_by_symbol):
    """Enrich copies only; require an immediately preceding, aligned weekly bar.

    Stage history is owned by app.py. Never infer a prior Stage for research
    candidates that only have a current provisional classification.
    """
    rows = screen.copy()
    dates = pd.to_datetime(rows.get('last_date', pd.Series(dtype='datetime64[ns]')), errors='coerce')
    reference = dates.max()
    observations = []
    ambiguous = set(rows.loc[rows.symbol.duplicated(keep=False), 'symbol']) if not rows.empty else set()
    for _, row in rows.iterrows():
        current_date = pd.to_datetime(row.get('last_date'), errors='coerce')
        item = dict(id=asset_id(row), week_comparable=False, stage_comparable=False,
                    previous_ret26=None, strength_change=None, return1w=None)
        history = weekly_by_symbol.get(str(row.get('symbol')))
        if (row.get('symbol') not in ambiguous and history is not None and len(history) >= 2
                and pd.notna(current_date) and current_date == reference):
            history = history.sort_values('date')
            current, previous = history.iloc[-1], history.iloc[-2]
            if (pd.Timestamp(current.date) == current_date
                    and current_date - pd.Timestamp(previous.date) == pd.Timedelta(days=7)):
                close, prior_close = number(current.get('close')), number(previous.get('close'))
                item['week_comparable'] = close is not None and prior_close is not None and prior_close > 0
                if item['week_comparable']:
                    item['return1w'] = (close / prior_close - 1) * 100
                    prior_return = number(previous.get('ret26_pct'))
                    current_return = number(row.get('ret26_pct'))
                    item['previous_ret26'] = prior_return
                    if prior_return is not None and current_return is not None:
                        item['strength_change'] = current_return - prior_return
                    item['stage_comparable'] = (row.get('stage_label') in VALID_STAGES
                        and row.get('previous_stage_label') in VALID_STAGES)
        observations.append(item)
    for key in ('id', 'week_comparable', 'stage_comparable', 'previous_ret26', 'strength_change', 'return1w'):
        rows[key] = [item[key] for item in observations]
    for key in ('week_comparable', 'stage_comparable'):
        rows[key] = rows[key].astype(bool)
    return rows, reference


def stage_summary(rows):
    """Conservation holds: delta == entries - exits, or every total is unknown."""
    current = rows.stage_label.eq(STAGE2)
    comparable = bool(len(rows) and rows.stage_comparable.all())
    result = dict(current=int(current.sum()), coverage=int(rows.stage_comparable.sum()),
                  total=len(rows), previous=None, delta=None, entries=None, exits=None)
    if comparable:
        previous = rows.previous_stage_label.eq(STAGE2)
        result.update(previous=int(previous.sum()), delta=int(current.sum() - previous.sum()),
                      entries=int((current & ~previous).sum()), exits=int((previous & ~current).sum()))
    return result


def ranked_rows(rows):
    """Rank within the selected asset group/country; ties share a minimum rank.

    If any member lacks comparable returns, withhold rank movement for the whole
    group rather than silently comparing against a smaller previous universe.
    """
    rows = rows.copy()
    rows['ret26_pct'] = pd.to_numeric(rows.ret26_pct, errors='coerce').map(number)
    rows['rank'] = rows.ret26_pct.rank(ascending=False, method='min')
    rows['rank_move'] = None
    if len(rows) and rows.week_comparable.all() and rows.ret26_pct.notna().all() and rows.previous_ret26.notna().all():
        rows['rank_move'] = rows.previous_ret26.rank(ascending=False, method='min') - rows['rank']
    return rows.sort_values(['rank', 'symbol'], kind='stable', na_position='last')


def percent(value, suffix='%'):
    value = number(value)
    return UNAVAILABLE if value is None else f'{value:+.1f}{suffix}'


def transition(row):
    if not row.get('stage_comparable', False):
        return UNAVAILABLE
    old, current = row['previous_stage_label'], row['stage_label']
    short = lambda value: value.replace(' 후보', '').replace(' 관찰', '')
    return short(current) + ' 유지' if old == current else f'{short(old)} → {short(current)}'


def render_weekly_briefing(st, screen, weekly_by_symbol, bookmarks, open_asset, open_area, *, data_source=None):
    """Chart-free briefing; callbacks reuse the application's existing routes."""
    from hashlib import sha256
    from favorite_assets import asset_area, watchlist_frame
    from briefing_assets import icon
    from html import escape
    source_label = {'가상 데모':'가상 데모 · 모의 데이터', 'CSV 업로드':'CSV 업로드 · 분석 데이터',
                    'KIS API · 미국·한국':'운영 유니버스 · 저장된 실제 데이터'}.get(data_source, '현재 분석 데이터')
    # Sunday crypto closes are a separate analysis calendar, never mixed into a
    # Friday market briefing. The existing crypto analysis menu is unchanged.
    rows, reference = weekly_snapshot(screen[screen.asset_type_norm.ne('crypto_asset')], weekly_by_symbol)

    def link(row, key, detail, value=None, movement=None, rank=None):
        token = sha256(str(row['id']).encode()).hexdigest()[:12]
        kind = row.get('asset_type_norm')
        name = row.get('market') if kind == 'market_etf' else row.get('sector', '') if kind == 'sector_etf' else row.get('name', row['symbol'])
        subtitle = str(row['symbol']) if kind == 'market_etf' else f"{row.get('market', '')} · {row['symbol']}"
        with st.container(key=f'briefing_row_{key}_{token}'):
            columns = st.columns([.28, 3.6, 1.55, 1.2] if rank is not None else [3.6, 1.55, 1.2] if key == 'watch' else [3.6, 2.3], gap='small', vertical_alignment='center')
            if rank is not None:
                columns[0].caption(str(rank))
            with columns[1 if rank is not None else 0]:
                st.button(f"**{name}**  \n{subtitle}",
                          key=f'briefing_{key}_{token}', width='stretch', help=f'{name} · {subtitle} · {detail}',
                          on_click=open_asset, args=(str(row['symbol']), asset_area(row)))
            with columns[2 if rank is not None else 1]:
                tone = 'positive' if number(value) is not None and number(value) > 0 else 'negative' if number(value) is not None and number(value) < 0 else 'muted'
                detail_html = escape(detail)
                if key == 'strength':
                    detail_html = f'<small>{percent(row.get("previous_ret26"))} → {percent(row.get("ret26_pct"))}</small>' + detail_html
                elif key == 'events' and row.get('stage_comparable'):
                    labels = {STAGE2:'2', 'Stage 2A 관찰 후보':'2A', '중립 / 추가 확인':'중립', '하락 추세 관찰':'하락'}
                    before, after = row['previous_stage_label'], row['stage_label']
                    detail_html = f'<span class="briefing-stage">{labels.get(before, escape(before))}</span> → <span class="briefing-stage current">{labels.get(after, escape(after))}</span>'
                st.markdown(f'<div class="briefing-number {tone}">{detail_html}</div>', unsafe_allow_html=True)
            if rank is not None:
                columns[3].markdown(f'<div class="briefing-move">{escape(movement or UNAVAILABLE)}</div>', unsafe_allow_html=True)
            elif key == 'watch':
                columns[2].markdown(f'<div class="briefing-move">{escape(movement or UNAVAILABLE)}</div>', unsafe_allow_html=True)

    def table_head(first='순위 · 자산', second='26주 절대수익률', third='전주 대비'):
        st.markdown(f'<div class="briefing-table-head"><span>{first}</span><span>{second}</span><span>{third}</span></div>', unsafe_allow_html=True)

    search_rows = rows.to_dict('records')
    def search_label(index):
        row = search_rows[index]
        return f"{row.get('market', '')} · {row.get('sector', '')} · {row.get('name', '')} · {row['symbol']}"
    def search_open():
        index = st.session_state.get('briefing_global_search')
        if index is not None:
            row = search_rows[index]
            st.session_state['briefing_global_search'] = None
            open_asset(str(row['symbol']), asset_area(row))
    with st.container(key='briefing_search'):
        st.selectbox('국가, 업종, 종목 검색', range(len(search_rows)), index=None, format_func=search_label,
                     placeholder='국가, 업종, 종목을 검색하세요…', key='briefing_global_search',
                     label_visibility='collapsed', on_change=search_open)

    with st.container(key='weekly_briefing'):
        date = str(reference.date()) if pd.notna(reference) else '기준일 없음'
        st.markdown(f'<div class="briefing-context"><h2>주간 시장 브리핑</h2><span>완료 주봉 기준 <b>{date}</b></span><small>{source_label}</small></div>', unsafe_allow_html=True)
        with st.container(key='briefing_header_status'):
            st.markdown(f'<span class="briefing-source">{source_label.split(" · ")[0]}</span><span>완료 주봉 기준 <b>{date}</b></span>', unsafe_allow_html=True)
        groups = [('Stage 2 시장', rows[rows.asset_type_norm.eq('market_etf')], 'markets_commodities'),
                  ('Stage 2 업종', rows[rows.asset_type_norm.eq('sector_etf')], 'sectors'),
                  ('Stage 2 종목', rows[rows.asset_type_norm.eq('stock')], 'stocks')]
        with st.container(key='briefing_summary'):
            for col, (title, group, area) in zip(st.columns(4), groups + [('Stage 2 진입·이탈', rows, 'stage2')]):
                summary = stage_summary(group)
                with col, st.container(border=True, key=f'briefing_card_{area}'):
                    artwork = {'markets_commodities':'GlobeHemisphereWest', 'sectors':'Factory', 'stocks':'ChartBar', 'stage2':'Star'}[area]
                    st.markdown(f'<div class="briefing-kpi-icon">{icon(artwork)}</div>', unsafe_allow_html=True)
                    if area == 'stage2':
                        value = UNAVAILABLE if summary['entries'] is None else f"+{summary['entries']} / −{summary['exits']}"
                        st.metric(title, value)
                    else:
                        st.metric(title, str(summary['current']),
                                  delta=None if summary['delta'] is None else f"{summary['delta']:+d} 전주 대비",
                                  delta_color='off' if summary['delta'] == 0 else 'normal')
                    st.caption(UNAVAILABLE if summary['delta'] is None else f"전주 {summary['previous']}개 · 진입 {summary['entries']} / 이탈 {summary['exits']}")
                    st.button('후보 분석 →' if area == 'stage2' else '분석 →', key=f'briefing_area_{area}',
                              icon=':material/arrow_outward:', on_click=open_area, args=(area,))
        left, middle, right = st.columns([1, 1, 1])
        for panel, title, group, key in [(left, '강한 시장', groups[0][1], 'markets'),
                                          (middle, '강한 업종', groups[1][1], 'sectors')]:
            with panel, st.container(border=True, key=f'briefing_panel_{key}'):
                with st.container(key=f'briefing_panel_header_{key}'):
                    a,b = st.columns([2,1], vertical_alignment='center')
                    a.markdown(f'#### {title}')
                    with b:
                        if key == 'sectors':
                            countries = ['전체'] + sorted(group.market.dropna().astype(str).unique())
                            country = st.selectbox('업종 국가', countries, key='briefing_sector_country', label_visibility='collapsed')
                            if country != '전체':
                                group = group[group.market.eq(country)]
                        else:
                            st.button('분석하기', key='briefing_open_markets', on_click=open_area, args=('markets_commodities',))
                table_head()
                dated = group[pd.to_datetime(group.last_date, errors='coerce').eq(reference)]
                ranked = ranked_rows(dated)
                if len(dated) != len(group):
                    ranked['rank_move'] = None
                if ranked.empty:
                    st.info('현재 분석 가능한 자산이 없습니다.')
                for _, row in ranked.head(5).iterrows():
                    move = number(row['rank_move'])
                    movement = UNAVAILABLE if move is None else '유지' if move == 0 else f"{'↑' if move > 0 else '↓'}{abs(int(move))}"
                    rank = str(int(row['rank'])) if pd.notna(row['rank']) else '—'
                    link(row, key, percent(row['ret26_pct']), row['ret26_pct'], movement, rank)
                st.caption(f'같은 자산군·국가 범위 · 기준 주간 {len(dated)}/{len(group)}개 · 누락 시 순위 비교 불가')
        with right, st.container(border=True, key='briefing_panel_events'):
            st.markdown('#### Stage 2 진입·이탈')
            summary = stage_summary(rows)
            event = st.radio('변화', ['신규 진입', '이탈'], horizontal=True, key='briefing_event', label_visibility='collapsed')
            eligible = rows[rows.stage_comparable]
            mask = (eligible.stage_label.eq(STAGE2) & ~eligible.previous_stage_label.eq(STAGE2)) if event == '신규 진입' else (~eligible.stage_label.eq(STAGE2) & eligible.previous_stage_label.eq(STAGE2))
            changes = eligible[mask]
            with st.container(height=200, border=False, key='briefing_event_list'):
                for _, row in changes.iterrows():
                    link(row, 'events', transition(row))
                if changes.empty:
                    st.info('확인 가능한 ' + event + ' 자산이 없습니다.' if len(eligible) else UNAVAILABLE + ' · 전주 판정 데이터 없음')
            st.caption('전주 후보 집합과 비교 · 판정 보류는 이탈에서 제외')
            if summary['delta'] is None:
                st.caption(f"전체 합계 비교 불가 · 개별 전주 판정 {summary['coverage']}/{summary['total']}개 확인")
        strength, watch = st.columns([1.18, 1])
        with strength, st.container(border=True, key='briefing_panel_strength'):
            st.markdown('#### 이번 기준 주간, 강도의 변화')
            market_sector = rows[rows.asset_type_norm.isin(['market_etf', 'sector_etf'])]
            for col, title, ascending in zip(st.columns(2), ['↑ 개선', '↓ 약화'], [False, True]):
                with col:
                    st.markdown(f'**{title}**')
                    valid = market_sector[market_sector.strength_change.lt(0) if ascending else market_sector.strength_change.gt(0)]
                    for _, row in valid.sort_values('strength_change', ascending=ascending).head(3).iterrows():
                        link(row, 'strength', percent(row['strength_change'], '%p'), row['strength_change'])
                    if valid.empty:
                        st.caption(UNAVAILABLE if market_sector.strength_change.notna().sum() == 0 else '해당 자산 없음')
            st.caption(f"26주 절대수익률의 전주 대비 증감 · 별도 RS 지표 아님 · 비교 가능 {market_sector.strength_change.notna().sum()}/{len(market_sector)}개")
        with watch, st.container(border=True, key='briefing_panel_watch'):
            watched = watchlist_frame(bookmarks, rows)
            with st.container(key='briefing_panel_header_watch'):
                a, b = st.columns([3,1], vertical_alignment='center')
                a.markdown('#### 관심 목록의 한 주')
                b.button('관심 목록 분석 →', key='briefing_area_favorites', on_click=open_area, args=('favorites',))
            table_head('관심 자산', '주간 수익률', 'Stage 변화')
            if watched.empty:
                with st.container(key='briefing_watch_empty'):
                    st.caption('관심 자산이 없습니다. 분석 목록의 ☆로 등록하세요.')
            for _, row in watched.head(8).iterrows():
                detail = percent(row.get('return1w')) if row.price_available else UNAVAILABLE
                link(row, 'watch', detail, row.get('return1w'), transition(row) if row.price_available else '현재 가격 없음')
        st.caption('범위: 현재 필터·시총·데이터 조건을 통과한 분석 자산. 과거 편입·편출 유니버스를 복원한 전체 시장 통계가 아닙니다. 원자재는 진입·이탈에 포함하며 시장 수·순위에서는 제외합니다. 일요일 마감 가상자산은 국가 및 원자재 메뉴에서 별도로 분석합니다.')
