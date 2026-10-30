"""Presentation helpers; the Stage engine remains the source of all metrics."""
import math


def _finite_return(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def absolute_return_text(value):
    number = _finite_return(value)
    return '수익률 없음' if number is None else f'{number:+.2f}%'


def return_tile_color(value):
    number = _finite_return(value)
    if number is None or number == 0:
        return 'rgba(148,163,184,0.18)'
    alpha = .12 + .24 * min(abs(number) / 50, 1)
    rgb = '22,163,74' if number > 0 else '220,38,38'
    return f'rgba({rgb},{alpha:.3f})'


def heatmap_tile_label(row):
    symbol = str(row.get('symbol', ''))
    kind = row.get('asset_type_norm', row.get('asset_type', ''))
    if kind == 'market_etf':
        name = row.get('market') or row.get('name') or symbol
        if row.get('sector') not in ('Market', '', None):
            name = f"{name} · {row['sector']}"
    elif kind in ('commodity_etf', 'commodity'):
        name = row.get('sector') or row.get('name') or symbol
    else:
        name = row.get('name') or symbol
    return f"{name} ({symbol}) · {absolute_return_text(row.get('ret26_pct'))} · {row.get('stage_label', '판정 대기')}"


def candidate_entry_text(row):
    if row.get('stage_label') != 'Stage 2 후보':
        return '신규 진입 —'
    previous = str(row.get('previous_stage_label', ''))
    if not previous or previous in ('이전 주 데이터 부족', 'None', 'nan', '<NA>'):
        return '신규 여부 미확인'
    return '🆕 신규 진입' if str(row.get('stage2_new_entry', False)).lower() == 'true' else '기존 후보'


def compact_asset_label(row):
    symbol = str(row.get('symbol', ''))
    name = row.get('name') or symbol
    if row.get('asset_type_norm') == 'sector_etf' and row.get('sector'):
        name = f"{row['sector']} · {row.get('market', '')}"
    name = str(name)
    if len(name) > 14:
        name = name[:13] + '…'
    return f"{name} ({symbol}) · 26주 {absolute_return_text(row.get('ret26_pct'))}"
