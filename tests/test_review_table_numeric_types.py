"""Check actual Arrow-rendered review values, not just the CSV loader's dtype."""
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest


def test_review_tables_keep_numeric_missing_values_and_search_behavior(monkeypatch):
    def reject_network(*args, **kwargs):
        raise AssertionError('Review tables must use stored snapshots')
    monkeypatch.setattr('requests.sessions.Session.request', reject_network)
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    original_read = pd.read_csv
    def read(path, *args, **kwargs):
        frame = original_read(path, *args, **kwargs)
        column = {'data/provisional_candidate_stage_report.csv': 'close',
                  'data/yahoo_market_cap_reconciliation.csv': 'candidate_cap_usd_b'}.get(str(path))
        if column:
            frame = frame.copy()
            frame.loc[frame.index[0], column] = float('nan')
            frame.loc[frame.index[1], column] = 123.45
        return frame
    monkeypatch.setattr(pd, 'read_csv', read)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=45).run()
    assert not app.exception

    def table_with(column):
        return next(table.value for table in app.dataframe if column in table.value.columns)

    provisional = table_with('최근 주봉 종가')
    reconciliation = table_with('candidate_cap_usd_b')
    for table, column in ((provisional, '최근 주봉 종가'),
                          (reconciliation, 'candidate_cap_usd_b')):
        assert pd.api.types.is_numeric_dtype(table[column]), table[column].dtype
        assert table[column].isna().any()
        assert table[column].notna().any()
    # Filtering and a subsequent rerun must preserve numeric chart observations.
    symbol = str(provisional.loc[provisional['최근 주봉 종가'].first_valid_index(), '심볼'])
    app.text_input(key='provisional_candidate_stage_search').set_value(symbol).run()
    assert not app.exception
    filtered = table_with('최근 주봉 종가')
    assert not filtered.empty
    assert filtered['심볼'].astype(str).str.contains(symbol, regex=False).all()
    assert pd.api.types.is_numeric_dtype(filtered['최근 주봉 종가'])
    app.run()
    assert not app.exception
    assert pd.api.types.is_numeric_dtype(table_with('최근 주봉 종가')['최근 주봉 종가'])
