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
    # Use a saved candidate that passes the KIS identity and market-cap chart gates.
    selected = 'ALAB'
    clock = datetime(2026, 10, 28, 20, 30, tzinfo=ZoneInfo('Asia/Seoul'))
    original_cutoff = market_data.completed_bar_cutoff_date
    monkeypatch.setattr(market_data, 'completed_bar_cutoff_date',
                        lambda exchange, now_kst=None: original_cutoff(exchange, now_kst or clock))

    def read(path, *args, **kwargs):
        frame = original_read(path, *args, **kwargs)
        symbol = {'data/daily_prices.csv': 'SPY', 'data/candidate_daily_prices.csv': selected}.get(Path(path).as_posix())
        if symbol:
            frame = frame[~(frame.symbol.eq(symbol) & frame.date.eq('2026-10-28'))].copy()
            # The research reader requests dtype=str; keep the fault fixture
            # assignable under pandas' strict string dtype on every platform.
            marker = frame[frame.symbol.eq(symbol)].iloc[-1].astype(object).copy()
            marker['date'] = '2026-10-28'
            for column in ('open', 'high', 'low', 'close'):
                marker[column] = 999999
            frame = pd.concat([frame, marker.to_frame().T], ignore_index=True)
        return frame
    monkeypatch.setattr(pd, 'read_csv', read)
    def reject_network(*args, **kwargs):
        raise AssertionError('Read-time guards must not request providers')
    monkeypatch.setattr('requests.sessions.Session.request', reject_network)
    def unavailable_classification():
        raise OSError('Offline saved-price regression')
    monkeypatch.setattr('us_research_dashboard.approved_classification', unavailable_classification)
    from us_research_dashboard import build_research
    def replay_at_session(*args, **kwargs):
        kwargs.update(now=clock, as_of=clock.date())
        return build_research(*args, **kwargs)
    monkeypatch.setattr('us_research_dashboard.build_research', replay_at_session)
    original_chart = st.plotly_chart
    rendered = {}
    def render_chart(figure, *args, **kwargs):
        if kwargs.get('key') == 'stocks_selected_chart':
            rendered['pending'] = figure
        return original_chart(figure, *args, **kwargs)
    monkeypatch.setattr(st, 'plotly_chart', render_chart)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=180)
    app.secrets['APP_PASSWORD'] = 'local-us-session-regression'
    app.run()
    next(widget for widget in app.radio if widget.label == '모드').set_value('KIS API · 미국·한국').run()
    next(widget for widget in app.text_input if widget.label == 'KIS 모드 비밀번호').set_value('local-us-session-regression')
    next(widget for widget in app.button if widget.label == '잠금 해제').click().run()
    assert not app.exception
    spy = app.session_state['kis_prices'].query('symbol == "SPY"')
    assert pd.to_datetime(spy.date).max() == pd.Timestamp('2026-10-27')
    app.radio(key='analysis_navigation_choice').set_value('stocks').run()
    assert not app.exception
    assert app.selectbox(key='stocks_market').value == 'United States'
    # Select the same saved candidate through the normal stock table and
    # retain the completed-session guard.
    app.text_input(key='stocks_search').set_value(selected).run()
    app.button(key=f'stocks_selected_symbol_pick_{selected}').click().run()
    app.button(key=f'stocks_selected_period_{selected}_pick_toggle').click().run()
    assert not app.exception
    assert pd.to_datetime(rendered['pending'].data[0].x).max() == pd.Timestamp('2026-10-27')

    ma = rendered['pending'].data[1]
    assert ma.name == '50일 이동평균'
    import numpy as np
    np.testing.assert_allclose(ma.y,pd.Series(rendered['pending'].data[0].close).rolling(50).mean(),equal_nan=True)
