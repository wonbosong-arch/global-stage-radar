"""Presentation state only; never changes providers or Stage calculations."""
from pathlib import Path
import streamlit as st
import streamlit.components.v2 as components

_fixed_header = components.component('fixed_analysis_header', js="""
export default function() {
  function place() {
    const header=document.querySelector('.st-key-analysis_header');
    const main=document.querySelector('.stMainBlockContainer');
    if(!header || !main) return;
    const rect=main.getBoundingClientRect(), css=getComputedStyle(main);
    const left=parseFloat(css.paddingLeft),right=parseFloat(css.paddingRight);
    const holder=header.parentElement;
    holder.style.minHeight=header.offsetHeight+'px';
    Object.assign(header.style,{position:'fixed',top:'2.75rem',left:(rect.left+left)+'px',
      width:Math.max(0,rect.width-left-right)+'px',zIndex:100});
  }
  place();const timer=setInterval(place,200);
  return ()=>clearInterval(timer);
}
""")

_list_keyboard = components.component('analysis_list_keyboard', js=Path(__file__).with_name('list_keyboard.js').read_text())

TABS = {'stage2': 'Stage 2 후보', 'markets_commodities': '국가 및 원자재',
        'sectors': '업종', 'stocks': '종목'}


def remember_dashboard_state():
    memory = st.session_state.setdefault('dashboard_widget_memory', {})
    for key in list(st.session_state):
        if (key.startswith(('candidate_quick_', 'candidate_watchlist_', 'pending_candidate_chart_', 'markets_commodities_', 'sectors_', 'stocks_'))
                or key == 'global_asset_view_mode') and not key.endswith('_favorite') and not any(
                    token in key for token in ('_pick_', '_next', '_prev', '_detail_', '_download', '_open_country', '_open_stocks_', '_back_to_', '_clear_route')):
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
            active = st.radio('분석 탭', list(TABS), format_func=TABS.get,
                            horizontal=True, key='active_analysis_area',
                            label_visibility='collapsed', on_change=remember_dashboard_state)
            _fixed_header(key='analysis_header_layout')
            _list_keyboard(key='analysis_list_keyboard')
            return active


def shell_styles():
    st.markdown('''<style>
    .stMainBlockContainer {padding-top:3rem;}
    [data-testid=stMain] {scroll-padding-top:8rem;}
    .st-key-analysis_header {background:var(--background-color,#fff);gap:0; border-bottom:1px solid #94a3b8;}
    .st-key-analysis_header h3 {padding:0 0 .25rem;font-size:1.3rem;}
    .st-key-analysis_header [role=radiogroup] {flex-wrap:nowrap;overflow-x:auto;white-space:nowrap;gap:1.3rem;}
    .st-key-analysis_header [role=radiogroup] label {flex-shrink:0;padding:.3rem .2rem;border-bottom:2px solid transparent;}
    .st-key-analysis_header [role=radiogroup] label:has(input:checked) {border-bottom-color:#0f766e;font-weight:600;}
    .st-key-analysis_header [role=radiogroup] label > div:first-child {display:none;}
    </style>''', unsafe_allow_html=True)
