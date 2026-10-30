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
    const banner=document.querySelector('[data-testid=stHeader]');
    const top=Math.max(0,banner?.getBoundingClientRect().bottom||0)+8;
    main.style.paddingTop=top+'px';
    holder.style.minHeight=header.offsetHeight+'px';
    document.querySelector('[data-testid=stMain]')?.style.setProperty('scroll-padding-top',(top+header.offsetHeight+12)+'px');
    Object.assign(header.style,{position:'fixed',top:top+'px',left:(rect.left+left)+'px',
      width:Math.max(0,rect.width-left-right)+'px',zIndex:100});
  }
  place();const timer=setInterval(place,200);
  return ()=>clearInterval(timer);
}
""")

_list_keyboard = components.component('analysis_list_keyboard', js=Path(__file__).with_name('list_keyboard.js').read_text())

_grid_paging = components.component('grid_paging', js=Path(__file__).with_name('grid_paging.js').read_text())

TABS = {'stage2': 'Stage 2 후보', 'markets_commodities': '국가 및 원자재',
        'sectors': '업종', 'stocks': '종목', 'favorites': '☆ 관심 목록'}


def remember_dashboard_state():
    memory = st.session_state.setdefault('dashboard_widget_memory', {})
    for key in list(st.session_state):
        if (key.startswith(('candidate_quick_', 'candidate_watchlist_', 'pending_candidate_chart_', 'markets_commodities_', 'sectors_', 'stocks_', 'favorites_'))
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
            st.markdown('### Global Stage Radar')
            if 'active_analysis_area' not in st.session_state:
                st.session_state['active_analysis_area'] = 'stage2'
            active = st.radio('분석 탭', list(TABS), format_func=TABS.get,
                            horizontal=True, key='active_analysis_area',
                            label_visibility='collapsed', on_change=remember_dashboard_state)
            _fixed_header(key='analysis_header_layout')
            _list_keyboard(key='analysis_list_keyboard')
            _grid_paging(key='grid_paging')
            return active


def shell_styles():
    st.markdown('''<style>
    .stMainBlockContainer {padding-top:4.5rem;}
    [data-testid=stMain] {scroll-padding-top:8rem;}
    .st-key-analysis_header {background:var(--background-color,#fff);gap:0; border-bottom:1px solid #94a3b8;}
    .st-key-analysis_header h3 {padding:0 0 .25rem;font-size:1.3rem;}
    .st-key-analysis_header [role=radiogroup] {flex-wrap:nowrap;overflow-x:auto;white-space:nowrap;gap:1.3rem;}
    .st-key-analysis_header [role=radiogroup] label {
      position:relative;flex-shrink:0;padding:.55rem .85rem;border:1px solid #cbd5e1;
      border-radius:8px 8px 0 0;background:#e2e8f0;color:#475569;cursor:pointer;}
    .st-key-analysis_header [role=radiogroup] label:has(input:checked) {
      background:#fff;color:#0f766e;font-weight:700;border-bottom-color:#fff;}
    .st-key-analysis_header [role=radiogroup] label > div:first-child,
    .st-key-analysis_header [role=radiogroup] label > input + div:empty {display:none;}
    .st-key-analysis_header [role=radiogroup] label input {
      position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;}
    .st-key-analysis_header [role=radiogroup] {gap:6px;padding-top:4px;}
    .st-key-analysis_header {overflow:visible;height:auto!important;min-height:max-content;gap:6px;}
    .st-key-analysis_header > div {flex-shrink:0;}
    .st-key-analysis_header h3 {margin:0;line-height:1.4;padding:0;}
    .st-key-analysis_header .st-key-active_analysis_area {margin-top:14px;}
    .st-key-analysis_header [data-testid=stRadioOption] > div > div:not([data-testid=stMarkdownContainer]) {display:none;}
    [class*="period"] [data-testid=stRadioOption] > div > div:not([data-testid=stMarkdownContainer]) {display:none;}
    [class*="period"] [role=radiogroup] {gap:0;flex-wrap:wrap;}
    [class*="period"] [role=radiogroup] label {
      position:relative;border:1px solid #94a3b8;padding:.35rem .7rem;cursor:pointer;}
    [class*="period"] [role=radiogroup] label:has(input:checked) {background:#0f766e;color:white;}
    [class*="period"] [role=radiogroup] label > div:first-child {display:none;}
    [class*="period"] [role=radiogroup] input {position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;}
    [class*="_grid_pager"].stVerticalBlock {max-width:260px;width:100%;margin-inline:auto;}
    [class*="_grid_pager"] [data-testid=stHorizontalBlock] {flex-wrap:nowrap;align-items:center;gap:8px;}
    [class*="_grid_pager"] [data-testid=stColumn] {min-width:0;}
    [class*="_grid_pager"] [data-testid=stCaptionContainer] {text-align:center;}
    [class*="_asset_card"] {gap:4px!important;min-width:0;padding:10px!important;border-color:#dbe2ea!important;border-radius:8px;}
    [class*="_asset_card"] h4 {font-size:1.05rem;line-height:1.4;margin:0;padding:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
    [class*="_asset_header"] {min-width:0;flex-wrap:nowrap!important;}
    [class*="_asset_header"] > div:has(h4) {min-width:0!important;max-width:calc(100% - 44px);flex:0 1 auto!important;overflow:hidden;}
    [class*="_asset_header"] [data-testid="stMarkdown"] {min-width:0;overflow:hidden;}
    [class*="_asset_header"] [data-testid="stMarkdownContainer"] {margin:0!important;}
    [class*="_asset_header"] > div:has(button) {flex:0 0 auto!important;min-width:32px!important;}
    [class*="_asset_card"] [data-testid="stCaptionContainer"] {font-size:.75rem;color:#64748b;}
    [class*="_asset_card"] [data-testid="stHorizontalBlock"] {flex-direction:row!important;flex-wrap:nowrap;gap:4px!important;}
    [class*="_asset_card"] [data-testid="stColumn"] {min-width:0!important;}
    [class*="_asset_card"] [class*="_favorite"] button {min-width:32px;padding:2px 6px;background:transparent;border-color:transparent;color:#0f766e;}
    [class*="_asset_card"] [class*="_favorite"] button p {font-size:0;white-space:nowrap;}
    [class*="_asset_card"] [class*="_favorite"] button p::before {content:'☆';font-size:1.35rem;}
    [class*="_asset_card"] [class*="_favorite"] button[kind="primary"] p::before {content:'★';}
    [class*="_asset_card"] [class*="_controls"] {gap:0!important;}
    [class*="_asset_card"] [class*="_controls"] [data-testid="stRadio"] {margin:0;}
    [class*="_asset_card"] [class*="_controls"] label {padding:2px 8px!important;}
    .radar-axis-host {display:flex;align-items:center;min-height:36px;}
    .radar-chart-controls {padding:0!important;margin:0;font-size:.8rem;}
    @media(max-width:900px) {
      [class*="_grid_canvas"] > [data-testid="stHorizontalBlock"],
      [class*="_grid_canvas"] > div > [data-testid="stHorizontalBlock"] {flex-direction:column;}
      [class*="_grid_canvas"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
      [class*="_grid_canvas"] > div > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {width:100%;flex:1 1 100%;}
    }

    [class*="_grid_pager"] [data-testid=stCaptionContainer] p {margin:0;white-space:nowrap;}
    </style>''', unsafe_allow_html=True)
