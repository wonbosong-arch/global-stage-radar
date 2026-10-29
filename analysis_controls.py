"""Analysis-only metrics and selection policy; no Stage/provider changes."""
import pandas as pd


def analysis_metrics(frame):
    result = frame.copy()
    close = pd.to_numeric(result['close'], errors='coerce')
    ma = pd.to_numeric(result['ma30'], errors='coerce')
    result['ma30_distance_pct'] = ((close / ma.where(ma.gt(0))) - 1) * 100
    return result


def new_stage2_rows(frame):
    return frame[frame['stage_label'].eq('Stage 2 후보')
                 & frame['stage2_new_entry'].fillna(False).astype(bool)
                 & frame['previous_stage_label'].fillna('이전 주 데이터 부족').ne('이전 주 데이터 부족')]


def choose_analysis_symbol(current, visible, universe):
    all_symbols = universe['symbol'].astype(str).tolist()
    if current in all_symbols:
        return current
    choices = visible['symbol'].astype(str).tolist() or all_symbols
    return choices[0] if choices else None
