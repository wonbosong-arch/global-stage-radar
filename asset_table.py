"""Shared compact ticker table; metrics remain owned by the screening engine."""
from hashlib import sha256
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from analysis_preferences import favorite_button, is_favorite
from dashboard_ui import _finite_return, absolute_return_text


EXTRA_COLUMNS = (
    ('stage_label', 'Stage', 144),
    ('ret13_pct', '13주 수익률', 112),
    ('rs_market_26w_pct', '시장 대비', 112),
    ('rs_sector_26w_pct', '업종 대비', 112),
    ('vol_ratio', '거래량 배율', 108),
)
STOCK_TABLE = 'stocks_selected_symbol'
STAGE2_TABLES = {'candidate_quick_chart_symbol', 'research_candidate_quick_chart_symbol'}


def stage2_table_columns(frame, *, research):
    columns = [('symbol', '자산 / 티커', 124)]
    if not research:
        columns = [('_favorite', '☆', 40), *columns, ('_new', '신규', 44)]
    columns.extend([('stage_label', 'Stage', 90 if not research else 144), ('ret26_pct', '26주 수익률', 92)])
    columns.extend(column for column in EXTRA_COLUMNS if column[0] != 'stage_label'
                   and column[0] in frame and frame[column[0]].notna().any())
    return columns


def stock_table_columns(frame):
    columns = [
        ('_favorite', '☆', 40), ('symbol', '티커', 76),
        ('ret26_pct', '26주 수익률', 100), ('stage_label', 'Stage', 144),
        ('market_cap_usd', '시가총액($B)', 110), ('ret1y_pct', '1년 수익률', 110),
    ]
    extras = ('analysis_scope', '_new', 'rs_market_26w_pct', 'rs_sector_26w_pct', 'vol_ratio')
    columns.extend(column for column in table_columns(frame) if column[0] in extras)
    columns.extend([
        ('slope4_pct', '30주선 기울기', 116),
        ('ma30_distance_pct', '30주선 거리', 104),
    ])
    return columns


def entry_value(row):
    previous = str(row.get('previous_stage_label', ''))
    if previous in ('', '이전 주 데이터 부족', 'None', 'nan', '<NA>'):
        return None
    flag = row.get('stage2_new_entry')
    if pd.isna(flag):
        return None
    return str(row.get('stage_label')) == 'Stage 2 후보' and str(flag).lower() == 'true'


def table_columns(frame):
    columns = [('symbol', '자산 / 티커', 204)]
    if 'analysis_scope' in frame:
        columns.append(('analysis_scope', '구분', 64))
    columns.append(('ret26_pct', '26주 수익률', 104))
    if 'stage2_new_entry' in frame and any(entry_value(row) is not None for _, row in frame.iterrows()):
        columns.append(('_new', '신규', 44))
    columns.append(('_favorite', '관심', 40))
    includes_specialist_etf = (
        'asset_type_norm' in frame and frame['asset_type_norm'].eq('research_sector_etf').any()
    )
    for key, title, width in EXTRA_COLUMNS:
        if (key in frame and frame[key].notna().any()) or (key == 'ret13_pct' and includes_specialist_etf):
            columns.append((key, title, width))
    return columns


def sorted_rows(frame, column, ascending, favorite_ids=()):
    """Stable, null-last sorting without changing caller data or selection."""
    if not column:
        return frame
    rows = frame.copy()
    if column == '_new':
        values = pd.Series([entry_value(row) for _, row in rows.iterrows()], index=rows.index)
    elif column == '_favorite':
        from favorite_assets import asset_id
        values = rows.apply(lambda row: asset_id(row) in favorite_ids, axis=1)
    elif column in rows:
        values = rows[column] if column in ('symbol', 'stage_label', 'analysis_scope') else pd.to_numeric(rows[column], errors='coerce')
        if column == 'ma30_distance_pct':
            values = values.abs()
    else:
        return frame
    return rows.assign(_table_order=values).sort_values('_table_order', ascending=ascending,
        na_position='last', kind='stable').drop(columns='_table_order')


def toggle_sort(state_key, column):
    key = f'{state_key}_table_sort'
    old = st.session_state.get(key)
    if old is None and state_key == STOCK_TABLE:
        old = ('ret26_pct', False)
    st.session_state[key] = (column, not old[1] if old and old[0] == column else
                             column in ('symbol', 'stage_label', 'ma30_distance_pct'))


def cell_text(row, column):
    value = row.get(column)
    if column == '_new':
        return 'N' if entry_value(row) is True else '—'
    if column in ('stage_label', 'analysis_scope'):
        return str(value) if pd.notna(value) else '—'
    number = _finite_return(value)
    if number is None:
        return '—'
    if column == 'market_cap_usd':
        return f'{number / 1e9:,.2f}' if number > 0 else '—'
    return f'{number:.2f}×' if column == 'vol_ratio' else absolute_return_text(number)


def render_asset_table(frame, state_key, selected_symbol, button_key_prefix, select_asset, *,
                       allow_favorite=True, table_id=None):
    table_id = table_id or state_key
    stock_table = table_id == STOCK_TABLE
    stage2_table = table_id in STAGE2_TABLES
    if stage2_table:
        columns = stage2_table_columns(frame, research=not allow_favorite)
    else:
        columns = stock_table_columns(frame) if stock_table else table_columns(frame)
    if not allow_favorite:
        columns = [column for column in columns if column[0] != '_favorite']
    from favorite_assets import asset_id
    favorite_ids = {asset_id(row) for _, row in frame.iterrows() if is_favorite(row)}
    order = st.session_state.get(f'{table_id}_table_sort', ('ret26_pct', False) if stock_table else (None, False))
    rows = frame if stock_table else sorted_rows(frame, *order, favorite_ids)
    panel_key = f'{table_id}_compact_list'
    st.markdown('<style>' + Path(__file__).with_suffix('.css').read_text() + '</style>', unsafe_allow_html=True)
    with st.container(key=panel_key, border=True,
                      height=460 if state_key == 'stocks_selected_symbol' else "content"):
        with st.container(horizontal=True, wrap=False, gap=None, key=f'{table_id}_table_header'):
            for column, title, width in columns:
                marker = (' ↑' if order[1] else ' ↓') if order[0] == column else ''
                st.button(title + marker, key=f'asset_table_sort_pick_{table_id}_{column}', width=width,
                    help=f'{"관심 목록" if column == "_favorite" else title} 정렬',
                    on_click=toggle_sort, args=(table_id, column))
        for _, row in rows.iterrows():
            symbol = str(row.get('symbol', '')).strip()
            if not symbol:
                continue
            selected_id = str(row.get('_selection_id', symbol))
            token = sha256(selected_id.encode()).hexdigest()[:16]
            row_key = f'{table_id}_table_row_{token}'
            with st.container(horizontal=True, wrap=False, gap=None, key=row_key):
                for column, _, width in columns:
                    if column == 'symbol':
                        key = f'candidate_quick_pick_{symbol}' if button_key_prefix == 'candidate_quick_pick' else f'{state_key}_pick_{selected_id}'
                        with st.container(width=width, gap=None, key=f'asset_name_{state_key}_{token}'):
                            st.button(symbol, key=key, width=width, help=f"{row.get('name', symbol)} ({symbol})",
                                type='primary' if selected_id == str(selected_symbol) else 'secondary',
                                on_click=select_asset, args=(state_key, selected_id))
                            if stage2_table and symbol.isdecimal():
                                label = row.get('sector') if row.get('asset_type_norm') == 'sector_etf' else row.get('market')
                                if pd.notna(label) and str(label).strip():
                                    st.markdown(f'<span class="radar-table-ticker-context" title="{escape(str(label), quote=True)}">'
                                                f'{escape(str(label))}</span>', unsafe_allow_html=True)
                            elif not stock_table and not stage2_table:
                                name = str(row.get('name', symbol))
                                st.markdown(f'<span class="radar-table-name" title="{escape(name, quote=True)}">{escape(name)}</span>', unsafe_allow_html=True)
                    elif column == '_favorite':
                        if row.get('asset_type_norm') == 'research_sector_etf':
                            st.container(width=width).empty()
                        else:
                            favorite_button(row, f'{state_key}_table_star_{token}_favorite', width=width)
                    else:
                        text = cell_text(row, column)
                        title = '신규 여부 미확인' if column == '_new' and entry_value(row) is None else text
                        cls = 'radar-table-new' if column == '_new' else 'radar-table-stage' if column in ('stage_label', 'analysis_scope') else 'radar-table-number'
                        st.markdown(f'<span class="{cls}" title="{escape(title, quote=True)}">{escape(text)}</span>',
                            unsafe_allow_html=True, width=width)
