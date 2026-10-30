"""Small, whitelisted UI preferences; authentication is never persisted here."""
import json
import re
from pathlib import Path
import streamlit.components.v2 as components
from favorite_assets import asset_id, bookmark, merge_bookmarks, refresh_bookmarks
import streamlit as st
import pandas as pd

AREAS = ('stage2', 'markets_commodities', 'sectors', 'stocks', 'favorites')
SOURCES = ('가상 데모', 'CSV 업로드', 'KIS API · 미국·한국')


def decode_preferences(raw):
    if not isinstance(raw, str) or len(raw) > 4096:
        return {}
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(value, dict):
        return {}
    result = {}
    if type(value.get('width')) is int and 30 <= value['width'] <= 45:
        result['dashboard_list_width'] = value['width']
    if value.get('tab') in AREAS:
        result['active_analysis_area'] = value['tab']
    if value.get('source') in SOURCES:
        result['data_source_mode'] = value['source']
    for area in AREAS:
        mode_key = 'global_asset_view_mode' if area == 'stage2' else f'{area}_view_mode'
        symbol_key = 'candidate_quick_chart_symbol' if area == 'stage2' else 'favorites_selected_id' if area == 'favorites' else f'{area}_selected_symbol'
        modes = ('차트 고정 목록', '3×3 차트', '히트맵') if area == 'markets_commodities' else ('차트 고정 목록', '3×3 차트')
        settings = value.get(area, {})
        if not isinstance(settings, dict):
            continue
        if settings.get('mode') in modes:
            result[mode_key] = settings['mode']
            if area != 'stage2':
                result[f'{area}_saved_view_mode'] = settings['mode']
        symbol = settings.get('symbol')
        if isinstance(symbol, str) and re.fullmatch(r'[A-Za-z0-9._/-]{1,40}:[A-Za-z0-9._/-]{1,40}' if area == 'favorites' else r'[A-Za-z0-9._-]{1,32}', symbol):
            result[symbol_key] = symbol
            if settings.get('period') in ('일봉', '주봉'):
                key = 'candidate_quick_chart_period' if area == 'stage2' else f'{area}_selected_period_{symbol}'
                result[key] = settings['period']
        page = settings.get('page')
        if type(page) is int and 0 <= page <= 5000:
            result['candidate_quick_grid_page' if area == 'stage2' else f'{area}_grid_page'] = page
    return result


def restore_preferences():
    if st.session_state.get('ui_preferences_loaded'):
        return
    for key, value in decode_preferences(st.query_params.get('radar', '')).items():
        if key not in st.session_state:
            st.session_state[key] = value
    st.session_state['ui_preferences_loaded'] = True


def save_preferences():
    value = {'tab': st.session_state.get('active_analysis_area', 'stage2'),
             'source': st.session_state.get('data_source_mode', SOURCES[0]),
             'width': st.session_state.get('dashboard_list_width', 33)}
    for area in AREAS:
        symbol = st.session_state.get('candidate_quick_chart_symbol' if area == 'stage2' else 'favorites_selected_id' if area == 'favorites' else f'{area}_selected_symbol')
        value[area] = {
            'mode': st.session_state.get('global_asset_view_mode' if area == 'stage2' else f'{area}_saved_view_mode', '히트맵' if area == 'markets_commodities' else '차트 고정 목록'),
            'symbol': symbol,
            'period': st.session_state.get('candidate_quick_chart_period' if area == 'stage2' else f'{area}_selected_period_{symbol}', '주봉'),
            'page': st.session_state.get('candidate_quick_grid_page' if area == 'stage2' else f'{area}_grid_page', 0),
        }
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    if st.query_params.get('radar') != raw:
        st.query_params['radar'] = raw


_favorite_storage = components.component('favorite_asset_storage', js=Path(__file__).with_name('favorite_storage.js').read_text())


def favorite_assets():
    return st.session_state.setdefault('analysis_favorite_assets', [])


def bind_favorite_catalog(frame):
    catalog = {asset_id(row): bookmark(row) for _, row in frame.iterrows()}
    st.session_state['favorite_asset_catalog'] = catalog
    # Migrate session-only ticker bookmarks without guessing an ambiguous venue.
    if not st.session_state.get('favorite_legacy_migrated'):
        legacy_symbols = list(dict.fromkeys(st.session_state.get('analysis_favorites', []) +
                                           st.session_state.get('candidate_watchlist_symbols', [])))
        for symbol in legacy_symbols:
            matches = [r for r in catalog.values() if r['symbol'] == symbol]
            if len(matches) == 1:
                st.session_state['analysis_favorite_assets'] = merge_bookmarks(favorite_assets(), matches)
            else:
                st.session_state['analysis_favorite_assets'] = merge_bookmarks(favorite_assets(), [bookmark({'symbol': symbol})])
        st.session_state['favorite_legacy_migrated'] = True
    st.session_state['analysis_favorite_assets'] = refresh_bookmarks(favorite_assets(), catalog)
    favorites()


def sync_favorite_storage():
    result = _favorite_storage(key='favorite_storage_bridge',
        data={'loaded': st.session_state.get('favorite_storage_loaded', False), 'assets': favorite_assets()},
        on_restored_change=lambda: None, on_storage_error_change=lambda: None)
    if not st.session_state.get('favorite_storage_loaded') and result.restored is not None:
        st.session_state['analysis_favorite_assets'] = merge_bookmarks(
            result.restored, favorite_assets(), st.session_state.get('favorite_removed', []))
        st.session_state['favorite_storage_loaded'] = True
    if result.storage_error:
        st.caption('브라우저 저장소를 사용할 수 없어 관심 목록은 현재 연결에서만 유지됩니다.')


def favorites():
    # Legacy session mirror for callers that only need ticker labels.
    symbols = list(dict.fromkeys(r['symbol'] for r in favorite_assets()))
    st.session_state['analysis_favorites'] = symbols
    return symbols


def is_favorite(row):
    return asset_id(row) in {r['id'] for r in favorite_assets()}


def favorite_mask(frame):
    ids = {r['id'] for r in favorite_assets()}
    return frame.apply(lambda row: asset_id(row) in ids, axis=1) if not frame.empty else pd.Series(False, index=frame.index)


def toggle_favorite(row):
    identity = asset_id(row)
    current = favorite_assets().copy()
    if identity in {r['id'] for r in current}:
        current = [r for r in current if r['id'] != identity]
        st.session_state.setdefault('favorite_removed', []).append(identity)
    else:
        current.append(bookmark(row))
        st.session_state['favorite_removed'] = [s for s in st.session_state.get('favorite_removed', []) if s != identity]
    st.session_state['analysis_favorite_assets'] = current
    favorites()


def favorite_button(row, key):
    selected = is_favorite(row)
    name = str(row.get('name', row.get('symbol', '')))
    label = ('★ 관심 해제: ' if selected else '☆ 관심 등록: ') + name
    st.button(label, key=key, help=label, type='primary' if selected else 'secondary',
              on_click=toggle_favorite, args=(dict(row),))
