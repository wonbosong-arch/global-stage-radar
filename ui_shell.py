"""Presentation state only; never changes providers or Stage calculations."""
import streamlit as st

TABS = {'stage2': 'Stage 2 후보', 'markets_commodities': '국가 및 원자재',
        'sectors': '업종', 'stocks': '종목'}


def remember_dashboard_state():
    memory = st.session_state.setdefault('dashboard_widget_memory', {})
    for key in list(st.session_state):
        if (key.startswith(('candidate_quick_', 'candidate_watchlist_', 'pending_candidate_chart_', 'markets_commodities_', 'sectors_', 'stocks_'))
                or key == 'global_asset_view_mode') and not any(
                    token in key for token in ('_pick_', '_next', '_prev', '_detail_', '_download', '_open_country')):
            memory[key] = st.session_state[key]


def restore_dashboard_state():
    for key in list(st.session_state):
        if (key.endswith(('view_mode', 'saved_view_mode')) or key == 'country_return_view') and st.session_state[key] == '표 보기':
            st.session_state[key] = '차트 고정 목록'
    for key, value in st.session_state.get('dashboard_widget_memory', {}).items():
        if key not in st.session_state:
            st.session_state[key] = '차트 고정 목록' if value == '표 보기' else value


def render_header(slot):
    with slot.container():
        with st.container(key='analysis_header'):
            st.markdown('### Global Stage Analysis Radar')
            if 'active_analysis_area' not in st.session_state:
                st.session_state['active_analysis_area'] = 'stage2'
            return st.radio('분석 탭', list(TABS), format_func=TABS.get,
                            horizontal=True, key='active_analysis_area',
                            label_visibility='collapsed', on_change=remember_dashboard_state)


def shell_styles():
    st.markdown('''<style>
    .stMainBlockContainer {padding-top:3rem;}
    .stMainBlockContainer > [data-testid="stLayoutWrapper"]:has(.st-key-analysis_header) {
      position:sticky;top:2.75rem;z-index:100;background:var(--background-color,#fff);
    }
    .st-key-analysis_header {background:var(--background-color,#fff);gap:0; border-bottom:1px solid #94a3b8;}
    .st-key-analysis_header h3 {padding:0 0 .25rem;font-size:1.3rem;}
    .st-key-analysis_header [role=radiogroup] {flex-wrap:nowrap;overflow-x:auto;white-space:nowrap;gap:1.3rem;}
    .st-key-analysis_header [role=radiogroup] label {flex-shrink:0;}
    </style>''', unsafe_allow_html=True)
