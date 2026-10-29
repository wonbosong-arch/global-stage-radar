from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

import market_data


def test_active_cache_and_pending_daily_chart_reject_saved_us_partial_bars(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    original_read = pd.read_csv
    registry = original_read('data/stock_universe_candidates.csv', dtype={'symbol': str})
    report = original_read('data/provisional_candidate_stage_report.csv', dtype={'symbol': str})
    stored = original_read('data/candidate_daily_prices.csv', dtype={'symbol': str})
    us = registry[registry.exchange.isin(['NAS', 'NYS', 'AMS'])].symbol
    selected = next(symbol for symbol in us if symbol in set(report.symbol) & set(stored.symbol))
    clock = datetime(2026, 10, 28, 20, 30, tzinfo=ZoneInfo('Asia/Seoul'))
    original_cutoff = market_data.completed_bar_cutoff_date
    monkeypatch.setattr(market_data, 'completed_bar_cutoff_date',
                        lambda exchange, now_kst=None: original_cutoff(exchange, now_kst or clock))

    def read(path, *args, **kwargs):
        frame = original_read(path, *args, **kwargs)
        symbol = {'data/daily_prices.csv': 'SPY', 'data/candidate_daily_prices.csv': selected}.get(str(path))
        if symbol:
            frame = frame[~(frame.symbol.eq(symbol) & frame.date.eq('2026-10-28'))].copy()
            marker = frame[frame.symbol.eq(symbol)].iloc[-1].copy()
            marker['date'] = '2026-10-28'
            for column in ('open', 'high', 'low', 'close'):
                marker[column] = 999999
            frame = pd.concat([frame, marker.to_frame().T], ignore_index=True)
        return frame
    monkeypatch.setattr(pd, 'read_csv', read)
    def reject_network(*args, **kwargs):
        raise AssertionError('Read-time guards must not request providers')
    monkeypatch.setattr('requests.sessions.Session.request', reject_network)
    original_chart = st.plotly_chart
    rendered = {}
    def render_chart(figure, *args, **kwargs):
        if kwargs.get('key') == 'pending_candidate_review_chart':
            rendered['pending'] = figure
        return original_chart(figure, *args, **kwargs)
    monkeypatch.setattr(st, 'plotly_chart', render_chart)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=45)
    app.secrets['APP_PASSWORD'] = 'local-us-session-regression'
    app.run()
    next(widget for widget in app.radio if widget.label == '모드').set_value('KIS API · 미국·한국').run()
    next(widget for widget in app.text_input if widget.label == 'KIS 모드 비밀번호').set_value('local-us-session-regression')
    next(widget for widget in app.button if widget.label == '잠금 해제').click().run()
    assert not app.exception
    spy = app.session_state['kis_prices'].query('symbol == "SPY"')
    assert pd.to_datetime(spy.date).max() == pd.Timestamp('2026-10-27')
    app.radio(key='active_analysis_area').set_value('stocks').run()
    app.selectbox(key='pending_candidate_chart_symbol').set_value(selected).run()
    app.radio(key='pending_candidate_chart_period').set_value('일봉').run()
    assert not app.exception
    assert pd.to_datetime(rendered['pending'].data[0].x).max() == pd.Timestamp('2026-10-27')
