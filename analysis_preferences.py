"""Small, whitelisted UI preferences; authentication is never persisted here."""
import json
import re
import streamlit as st

AREAS = ('stage2', 'markets_commodities', 'sectors', 'stocks')
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
        symbol_key = 'candidate_quick_chart_symbol' if area == 'stage2' else f'{area}_selected_symbol'
        modes = ('차트 고정 목록', '3×3 차트', '히트맵') if area == 'markets_commodities' else ('차트 고정 목록', '3×3 차트')
        settings = value.get(area, {})
        if not isinstance(settings, dict):
            continue
        if settings.get('mode') in modes:
            result[mode_key] = settings['mode']
            if area != 'stage2':
                result[f'{area}_saved_view_mode'] = settings['mode']
        symbol = settings.get('symbol')
        if isinstance(symbol, str) and re.fullmatch(r'[A-Za-z0-9._-]{1,32}', symbol):
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
        symbol = st.session_state.get('candidate_quick_chart_symbol' if area == 'stage2' else f'{area}_selected_symbol')
        value[area] = {
            'mode': st.session_state.get('global_asset_view_mode' if area == 'stage2' else f'{area}_saved_view_mode', '히트맵' if area == 'markets_commodities' else '차트 고정 목록'),
            'symbol': symbol,
            'period': st.session_state.get('candidate_quick_chart_period' if area == 'stage2' else f'{area}_selected_period_{symbol}', '주봉'),
            'page': st.session_state.get('candidate_quick_grid_page' if area == 'stage2' else f'{area}_grid_page', 0),
        }
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    if st.query_params.get('radar') != raw:
        st.query_params['radar'] = raw


def favorites():
    return st.session_state.setdefault('analysis_favorites', [])


def toggle_favorite(symbol):
    current = favorites().copy()
    if symbol in current:
        current.remove(symbol)
    else:
        current.append(symbol)
    st.session_state['analysis_favorites'] = current


def favorite_button(symbol, key):
    st.button('★ 관심 해제' if symbol in favorites() else '☆ 관심 추가', key=key,
              on_click=toggle_favorite, args=(symbol,))
