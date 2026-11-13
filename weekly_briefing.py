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


def render_weekly_briefing(st, screen, weekly_by_symbol, bookmarks, open_asset, open_area):
    """Chart-free briefing; callbacks reuse the application's existing routes."""
    from hashlib import sha256
    from favorite_assets import asset_area, watchlist_frame
    # Sunday crypto closes are a separate analysis calendar, never mixed into a
    # Friday market briefing. The existing crypto analysis menu is unchanged.
    rows, reference = weekly_snapshot(screen[screen.asset_type_norm.ne('crypto_asset')], weekly_by_symbol)

    def link(row, key, detail):
        token = sha256(str(row['id']).encode()).hexdigest()[:12]
        kind = row.get('asset_type_norm')
        name = row.get('market') if kind == 'market_etf' else f"{row.get('market', '')} · {row.get('sector', '')}" if kind == 'sector_etf' else row.get('name', row['symbol'])
        st.button(f"**{name} · {row['symbol']}**  \n{detail}",
                  key=f'briefing_{key}_{token}', width='stretch',
                  on_click=open_asset, args=(str(row['symbol']), asset_area(row)))

    with st.container(key='weekly_briefing'):
        st.markdown('## 주간 시장 브리핑')
        st.caption(('완료 주봉 기준 ' + str(reference.date()) if pd.notna(reference) else '완료 주봉 기준일 없음')
            + ' · 현재 분석 유니버스 안에서 전주와 비교 · 운영 유니버스의 Stage 후보이며 운영 확정·매수 신호 아님')
        groups = [('Stage 2 시장', rows[rows.asset_type_norm.eq('market_etf')], 'markets_commodities'),
                  ('Stage 2 업종', rows[rows.asset_type_norm.eq('sector_etf')], 'sectors'),
                  ('Stage 2 종목', rows[rows.asset_type_norm.eq('stock')], 'stocks')]
        with st.container(key='briefing_summary'):
            for col, (title, group, area) in zip(st.columns(4), groups + [('Stage 2 진입·이탈', rows, 'stage2')]):
                summary = stage_summary(group)
                with col, st.container(border=True, key=f'briefing_card_{area}'):
                    if area == 'stage2':
                        value = UNAVAILABLE if summary['entries'] is None else f"+{summary['entries']} / −{summary['exits']}"
                        st.metric(title, value)
                    else:
                        st.metric(title, str(summary['current']),
                                  delta=None if summary['delta'] is None else f"{summary['delta']:+d} 전주 대비",
                                  delta_color='off' if summary['delta'] == 0 else 'normal')
                    st.caption(UNAVAILABLE if summary['delta'] is None else f"전주 {summary['previous']}개 · 진입 {summary['entries']} / 이탈 {summary['exits']}")
                    st.button('후보 분석 →' if area == 'stage2' else '분석 →', key=f'briefing_area_{area}',
                              on_click=open_area, args=(area,))
        left, middle, right = st.columns([1, 1, 1])
        for panel, title, group, key in [(left, '강한 시장', groups[0][1], 'markets'),
                                          (middle, '강한 업종', groups[1][1], 'sectors')]:
            with panel, st.container(border=True, key=f'briefing_panel_{key}'):
                st.markdown(f'#### {title}')
                if key == 'sectors':
                    countries = ['전체'] + sorted(group.market.dropna().astype(str).unique())
                    country = st.selectbox('업종 국가', countries, key='briefing_sector_country')
                    if country != '전체':
                        group = group[group.market.eq(country)]
                st.caption('26주 절대수익률 · 전주 순위 변화')
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
                    link(row, key, f"{rank}위 · {percent(row['ret26_pct'])} · {movement}")
                st.caption(f'같은 자산군·국가 범위 비교 · 기준 주간 {len(dated)}/{len(group)}개. 비교 대상 누락 시 순위 변화는 비교 불가.')
        with right, st.container(border=True, key='briefing_panel_events'):
            st.markdown('#### Stage 2 진입·이탈')
            summary = stage_summary(rows)
            if summary['delta'] is None:
                st.caption(f"전체 합계 비교 불가 · 개별 전주 판정 {summary['coverage']}/{summary['total']}개 확인")
            event = st.radio('변화', ['신규 진입', '이탈'], horizontal=True, key='briefing_event')
            eligible = rows[rows.stage_comparable]
            mask = (eligible.stage_label.eq(STAGE2) & ~eligible.previous_stage_label.eq(STAGE2)) if event == '신규 진입' else (~eligible.stage_label.eq(STAGE2) & eligible.previous_stage_label.eq(STAGE2))
            changes = eligible[mask]
            with st.container(height=250):
                for _, row in changes.iterrows():
                    link(row, 'events', transition(row))
                if changes.empty:
                    st.info('확인 가능한 ' + event + ' 자산이 없습니다.' if len(eligible) else UNAVAILABLE + ' · 전주 판정 데이터 없음')
            st.caption('신규 = 전주 후보에 없고 이번 완료 주간에 포함. 판정 보류를 이탈로 계산하지 않습니다.')
        strength, watch = st.columns([1.4, 1])
        with strength, st.container(border=True, key='briefing_panel_strength'):
            st.markdown('#### 이번 주, 강도의 변화')
            st.caption('시장·업종의 26주 절대수익률 증감 (%p) · 별도 RS 지표 아님')
            market_sector = rows[rows.asset_type_norm.isin(['market_etf', 'sector_etf'])]
            for col, title, ascending in zip(st.columns(2), ['↑ 개선', '↓ 약화'], [False, True]):
                with col:
                    st.markdown(f'**{title}**')
                    valid = market_sector[market_sector.strength_change.lt(0) if ascending else market_sector.strength_change.gt(0)]
                    for _, row in valid.sort_values('strength_change', ascending=ascending).head(3).iterrows():
                        link(row, 'strength', percent(row['strength_change'], '%p'))
                    if valid.empty:
                        st.caption(UNAVAILABLE if market_sector.strength_change.notna().sum() == 0 else '해당 자산 없음')
            st.caption(f"전주 비교 가능 {market_sector.strength_change.notna().sum()}/{len(market_sector)}개 · 가격 미보유 자산은 포함하지 않습니다.")
        with watch, st.container(border=True, key='briefing_panel_watch'):
            st.markdown('#### 관심 목록의 한 주')
            watched = watchlist_frame(bookmarks, rows)
            if watched.empty:
                st.info('관심 자산이 없습니다. 분석 목록의 ☆로 등록하세요.')
            for _, row in watched.head(8).iterrows():
                detail = f"주간 {percent(row.get('return1w'))} · {transition(row)}" if row.price_available else UNAVAILABLE + ' · 현재 가격 없음'
                link(row, 'watch', detail)
            st.button('관심 목록 분석 →', key='briefing_area_favorites', on_click=open_area, args=('favorites',))
        st.caption('범위: 현재 필터·시총·데이터 조건을 통과한 분석 자산. 과거 편입·편출 유니버스를 복원한 전체 시장 통계가 아닙니다. 원자재는 진입·이탈에 포함하며 시장 수·순위에서는 제외합니다. 일요일 마감 가상자산은 국가 및 원자재 메뉴에서 별도로 분석합니다.')
