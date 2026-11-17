"""Shared analysis presentation; inputs are the existing screened rows."""
from html import escape

import streamlit as st


def analysis_heading(title, *, research=False, show_scope=True, data_source=None):
    source = '가상 데모 · 예시 데이터' if data_source == '가상 데모' else '업로드 데이터' if data_source == 'CSV 업로드' else '운영 유니버스'
    scope = '미국 KIS 연구 후보 · 운영과 별도 집계' if research else source
    st.markdown(
        f'<div class="analysis-heading"><div><div class="analysis-breadcrumb">시장 탐색 / {escape(title)}</div>'
        f'<h2>{escape(title)}</h2></div>' + (f'<span class="analysis-scope">{scope}</span>' if show_scope else '') + '</div>',
        unsafe_allow_html=True,
    )


def analysis_summary(rows, *, research=False, data_source=None):
    counts = rows.stage_label.value_counts()
    values = [('분석 자산', len(rows)), ('Stage 2', counts.get('Stage 2 후보', 0)),
              ('Stage 2A', counts.get('Stage 2A 관찰 후보', 0))]
    if not research and 'stage2_new_entry' in rows:
        values.append(('신규 Stage 2', int(rows.loc[rows.stage_label.eq('Stage 2 후보'), 'stage2_new_entry'].fillna(False).sum())))
    stats = ''.join(f'<span>{label}<b>{value:,}</b></span>' for label, value in values)
    source = '가상 데모 · 예시 데이터' if data_source == '가상 데모' else '업로드 데이터' if data_source == 'CSV 업로드' else '저장된 실제 데이터'
    note = '연구 판정 · 운영 승인·매수 신호와 분리' if research else source + ' · 신규 진입은 이전 완성 주봉과 비교'
    st.markdown(f'<div class="analysis-summary">{stats}<small>{note}</small></div>', unsafe_allow_html=True)
