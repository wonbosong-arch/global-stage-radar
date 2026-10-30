"""Shared asset header, period controls and chart card for every analysis area."""
from __future__ import annotations
from html import escape
import streamlit as st
import pandas as pd

from analysis_preferences import favorite_button
from favorite_assets import asset_id
from dashboard_ui import candidate_entry_text


def render_chart_card(row, chart_key, period_key, make_chart, *, compact=False,
                      favorite_key=None, below=None):
    symbol = str(row.get("symbol", ""))
    with st.container(key=f"{chart_key}_asset_card", border=True):
        name = str(row.get("name", symbol) or symbol)
        with st.container(horizontal=True, vertical_alignment="center", gap="small", key=f"{chart_key}_asset_header"):
            heading = f"{name} ({symbol})"
            st.markdown(f'<h4 title="{escape(heading, quote=True)}">{escape(symbol)}</h4>',
                        unsafe_allow_html=True, width="content")
            favorite_button(row, favorite_key or f"{chart_key}_favorite")
        date = row.get("last_daily_date", row.get("last_date", ""))
        date = str(date)[:10] if pd.notna(date) and str(date) not in {"", "nan", "NaT"} else "기록 없음"
        memory = st.session_state.setdefault("analysis_chart_periods", {})
        if period_key not in st.session_state:
            st.session_state[period_key] = memory.get(period_key, "주봉")
        with st.container(key=f"{chart_key}_controls", horizontal=True, vertical_alignment="center", gap="small"):
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
                fig.update_layout(title_text="", margin_t=8, meta={"asset_symbol": symbol, "asset_id": asset_id(row)})
                st.plotly_chart(fig, use_container_width=True, key=chart_key,
                                config={"scrollZoom": True, "displayModeBar": True})
        st.caption(f"{row.get('stage_label', '')} · {candidate_entry_text(row)} · 기준일 {date}")
        if below is not None:
            below(row)
