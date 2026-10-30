"""Shared compact ticker table; metrics remain owned by the screening engine."""
from hashlib import sha256
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from analysis_preferences import favorite_button, is_favorite
from dashboard_ui import _finite_return, absolute_return_text


EXTRA_COLUMNS = (
    ('ret13_pct', '13주 수익률', 112),
    ('rs_market_26w_pct', '시장 대비', 112),
    ('rs_sector_26w_pct', '업종 대비', 112),
    ('vol_ratio', '거래량 배율', 108),
    ('stage_label', 'Stage', 144),
)


def entry_value(row):
    previous = str(row.get('previous_stage_label', ''))
    if previous in ('', '이전 주 데이터 부족', 'None', 'nan', '<NA>'):
        return None
    flag = row.get('stage2_new_entry')
    if pd.isna(flag):
        return None
    return str(row.get('stage_label')) == 'Stage 2 후보' and str(flag).lower() == 'true'


def table_columns(frame):
    columns = [('symbol', '티커', 88), ('ret26_pct', '26주 수익률', 104)]
    if 'stage2_new_entry' in frame and any(entry_value(row) is not None for _, row in frame.iterrows()):
        columns.append(('_new', '신규', 44))
    columns.append(('_favorite', '관심', 40))
    for key, title, width in EXTRA_COLUMNS:
        if key in frame and frame[key].notna().any():
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
        values = rows[column] if column in ('symbol', 'stage_label') else pd.to_numeric(rows[column], errors='coerce')
    else:
        return frame
    return rows.assign(_table_order=values).sort_values('_table_order', ascending=ascending,
        na_position='last', kind='stable').drop(columns='_table_order')


def toggle_sort(state_key, column):
    key = f'{state_key}_table_sort'
    old = st.session_state.get(key)
    st.session_state[key] = (column, not old[1] if old and old[0] == column else column in ('symbol', 'stage_label'))


def cell_text(row, column):
    value = row.get(column)
    if column == '_new':
        return 'N' if entry_value(row) is True else '—'
    if column == 'stage_label':
        return str(value) if pd.notna(value) else '—'
    number = _finite_return(value)
    if number is None:
        return '—'
    return f'{number:.2f}×' if column == 'vol_ratio' else absolute_return_text(number)


def render_asset_table(frame, state_key, selected_symbol, button_key_prefix, select_asset):
    columns = table_columns(frame)
    from favorite_assets import asset_id
    favorite_ids = {asset_id(row) for _, row in frame.iterrows() if is_favorite(row)}
    order = st.session_state.get(f'{state_key}_table_sort', (None, False))
    rows = sorted_rows(frame, *order, favorite_ids)
    panel_key = f'{state_key}_compact_list'
    st.markdown('<style>' + Path(__file__).with_suffix('.css').read_text() + '</style>', unsafe_allow_html=True)
    with st.container(key=panel_key, border=True):
        with st.container(horizontal=True, wrap=False, gap=None, key=f'{state_key}_table_header'):
            for column, title, width in columns:
                marker = (' ↑' if order[1] else ' ↓') if order[0] == column else ''
                st.button(title + marker, key=f'asset_table_sort_pick_{state_key}_{column}', width=width,
                    help=f'{title} 정렬', on_click=toggle_sort, args=(state_key, column))
        for _, row in rows.iterrows():
            symbol = str(row.get('symbol', '')).strip()
            if not symbol:
                continue
            selected_id = str(row.get('_selection_id', symbol))
            token = sha256(selected_id.encode()).hexdigest()[:16]
            row_key = f'{state_key}_table_row_{token}'
            with st.container(horizontal=True, wrap=False, gap=None, key=row_key):
                for column, _, width in columns:
                    if column == 'symbol':
                        key = f'candidate_quick_pick_{symbol}' if button_key_prefix == 'candidate_quick_pick' else f'{state_key}_pick_{selected_id}'
                        st.button(symbol, key=key, width=width, help=f"{row.get('name', symbol)} ({symbol})",
                            type='primary' if selected_id == str(selected_symbol) else 'secondary',
                            on_click=select_asset, args=(state_key, selected_id))
                    elif column == '_favorite':
                        favorite_button(row, f'{state_key}_table_star_{token}_favorite', width=width)
                    else:
                        text = cell_text(row, column)
                        title = '신규 여부 미확인' if column == '_new' and entry_value(row) is None else text
                        cls = 'radar-table-new' if column == '_new' else 'radar-table-number' if column != 'stage_label' else 'radar-table-stage'
                        st.markdown(f'<span class="{cls}" title="{escape(title, quote=True)}">{escape(text)}</span>',
                            unsafe_allow_html=True, width=width)
