"""Shared asset header, period controls and chart card for every analysis area."""
from __future__ import annotations
from html import escape
import streamlit as st
import pandas as pd

from analysis_preferences import favorite_button
from favorite_assets import asset_id
from dashboard_ui import candidate_entry_text
from private_analysis_access import chart_config


def _toggle_stock_period(period_key):
    state = st.session_state
    state[period_key] = "일봉" if state.get(period_key, "주봉") == "주봉" else "주봉"


def _stock_chart_header(row, symbol, name):
    market = {"United States": "미국", "South Korea": "한국"}.get(row.get("market"), row.get("market"))
    fields = [name, market, row.get("sector"), row.get("stage_label")]
    label = " · ".join(str(value) for value in fields if pd.notna(value) and str(value).strip())
    pieces = [escape(str(value)) if pd.notna(value) and str(value).strip() else "—" for value in fields]
    return (
        f'<div class="stock-chart-heading" title="{escape(label, quote=True)}"><h4>{escape(symbol)}</h4>'
        f'<span>{pieces[0]}</span><span>{pieces[1]}</span><span>{pieces[2]}</span>'
        f'<strong>{pieces[3]}</strong></div>'
    )


def render_chart_card(row, chart_key, period_key, make_chart, *, compact=False,
                      favorite_key=None, below=None, allow_favorite=True, stock_details=None):
    symbol = str(row.get("symbol", ""))
    with st.container(key=f"{chart_key}_asset_card", border=True):
        name = str(row.get("name", symbol) or symbol)
        with st.container(horizontal=True, vertical_alignment="center", gap="small", key=f"{chart_key}_asset_header"):
            heading = f"{name} ({symbol})"
            if stock_details is not None:
                if allow_favorite:
                    favorite_button(row, favorite_key or f"{chart_key}_favorite")
                st.markdown(_stock_chart_header(row, symbol, name), unsafe_allow_html=True)
            else:
                st.markdown(f'<h4 title="{escape(heading, quote=True)}">{escape(symbol)}</h4>',
                            unsafe_allow_html=True, width="content")
            if allow_favorite and stock_details is None:
                favorite_button(row, favorite_key or f"{chart_key}_favorite")
        date = row.get("last_daily_date", row.get("last_date", ""))
        if stock_details is None:
            st.markdown(f'<div class="analysis-chart-name">{escape(name)} <span>{escape(str(row.get("market", "")))}</span></div>', unsafe_allow_html=True)
        date = str(date)[:10] if pd.notna(date) and str(date) not in {"", "nan", "NaT"} else "기록 없음"
        memory = st.session_state.setdefault("analysis_chart_periods", {})
        if period_key not in st.session_state:
            st.session_state[period_key] = memory.get(period_key, "주봉")
        with st.container(key=f"{chart_key}_controls", horizontal=True, vertical_alignment="center", gap="small"):
            if stock_details is not None:
                period = st.session_state[period_key]
                st.button("일/주", key=f"{period_key}_toggle", help="일봉/주봉 전환",
                          on_click=_toggle_stock_period, args=(period_key,))
            else:
                period = st.radio("차트 주기", ["일봉", "주봉"], horizontal=True,
                                  key=period_key, label_visibility="collapsed", width='content')
            st.markdown('<div class="radar-axis-host"></div>', unsafe_allow_html=True, width='content')
        memory[period_key] = period
        if not bool(row.get("price_available", True)):
            st.info(f"현재 가격 데이터가 없습니다. 마지막 확인: {str(date)[:10] if date else '기록 없음'}. 관심 등록은 유지됩니다.")
        else:
            fig = make_chart(symbol, compact=compact, period_is_weekly=period == "주봉", chart_period=period)
            if fig is None:
                st.info("표시할 가격 이력이 없습니다. 관심 등록은 유지됩니다.")
            else:
                # Send an explicit empty title so Plotly.react also clears a
                # previous title when reusing the same Streamlit chart widget.
                fig.update_layout(title_text="", height=440 if compact else 430, margin_t=8,
                                  meta={"asset_symbol": symbol, "asset_id": asset_id(row)})
                if stock_details is not None:
                    fig.update_layout(showlegend=False, margin=dict(l=48, r=14, t=22, b=34))
                    fig.update_yaxes(title_text="")
                st.plotly_chart(fig, use_container_width=True, key=chart_key,
                                config=chart_config(st, scrollZoom=True, displayModeBar=True))
        if stock_details is None:
            _render_chart_details(row, date, below)
    if stock_details is not None:
        with stock_details:
            _render_chart_details(row, date, below)


def _render_chart_details(row, date, below):
    if row.get("asset_type_norm") == "research_sector_etf" and date == "기록 없음":
        st.caption(str(row.get("stage_label", "")))
    else:
        st.caption(f"{row.get('stage_label', '')} · {candidate_entry_text(row)} · 기준일 {date}")
    if row.get("analysis_scope") == "연구":
        st.caption("미국 KIS 연구 · 운영 종목 활성화 및 매수 신호와 분리")
        note = row.get("review_note", "")
        if pd.notna(note) and str(note).strip():
            st.caption("Stage 보류 사유: " + str(note))
    if below is not None:
        below(row)
