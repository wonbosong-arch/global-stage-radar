"""Shared asset header, period controls and chart card for every analysis area."""
from __future__ import annotations
import streamlit as st
import pandas as pd

from analysis_preferences import favorite_button
from favorite_assets import asset_id
from dashboard_ui import candidate_entry_text


def render_chart_card(row, chart_key, period_key, make_chart, *, compact=False,
                      favorite_key=None, below=None):
    symbol = str(row.get("symbol", ""))
    with st.container(key=f"{chart_key}_asset_card", border=True):
        title, star = st.columns([.86, .14], gap="small", vertical_alignment="center")
        name = str(row.get("name", symbol) or symbol)
        with title:
            # Native text rendering escapes user-provided names.
            st.markdown(f"#### {name} ({symbol})", help=f"{name} ({symbol}) · {row.get('exchange', '')}")
        with star:
            favorite_button(row, favorite_key or f"{chart_key}_favorite")
        date = row.get("last_daily_date", row.get("last_date", ""))
        date = str(date)[:10] if pd.notna(date) and str(date) not in {"", "nan", "NaT"} else "기록 없음"
        st.caption(f"{row.get('stage_label', '')} · {candidate_entry_text(row)} · 기준일 {date}")
        memory = st.session_state.setdefault("analysis_chart_periods", {})
        if period_key not in st.session_state:
            st.session_state[period_key] = memory.get(period_key, "주봉")
        with st.container(key=f"{chart_key}_controls"):
            period_col, axis_col = st.columns([1, 1], gap="small", vertical_alignment="center")
            with period_col:
                period = st.radio("차트 주기", ["일봉", "주봉"], horizontal=True,
                                  format_func=lambda p: "일" if p == "일봉" else "주",
                                  key=period_key, label_visibility="collapsed")
            with axis_col:
                st.markdown('<div class="radar-axis-host"></div>', unsafe_allow_html=True)
        memory[period_key] = period
        if not bool(row.get("price_available", True)):
            st.info(f"현재 가격 데이터가 없습니다. 마지막 확인: {str(date)[:10] if date else '기록 없음'}. 관심 등록은 유지됩니다.")
        else:
            fig = make_chart(symbol, compact=compact, period_is_weekly=period == "주봉", chart_period=period)
            if fig is None:
                st.info("표시할 가격 이력이 없습니다. 관심 등록은 유지됩니다.")
            else:
                fig.update_layout(title=None, margin_t=8, meta={"asset_symbol": symbol, "asset_id": asset_id(row)})
                st.plotly_chart(fig, use_container_width=True, key=chart_key,
                                config={"scrollZoom": True, "displayModeBar": True})
        if below is not None:
            below(row)
