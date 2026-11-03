"""Fail-closed readiness diagnostics; never authorizes Stage or activation."""
import numpy as np
import pandas as pd
from stage_engine import weekly_bars

REQUIRED_COMPLETED_WEEKS = 35  # 30 MA + 4 slope + one prior comparable bar


def validated_daily(daily, *, as_of_date=None):
    """Validate the entire supplied interval against actual XSHG sessions.

    No deduplication, forward fill, weekend substitution or partial-week repair.
    Calendar lookup failure is a validation failure, never permission to proceed.
    This checks structure/calendar only, not provenance or adjustment evidence.
    """
    columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    if not isinstance(daily, pd.DataFrame) or not set(columns).issubset(daily.columns) or daily.empty:
        raise ValueError('가격 열 또는 관측값 부족')
    frame = daily.copy()
    dates = pd.to_datetime(frame.date, errors='coerce')
    if (not pd.api.types.is_datetime64_any_dtype(dates.dtype) or dates.isna().any()
            or dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all()):
        raise ValueError('거래일 형식 오류')
    if dates.duplicated().any():
        raise ValueError('중복 거래일')
    as_of = pd.Timestamp(as_of_date).normalize() if as_of_date is not None else pd.Timestamp.today().normalize()
    if pd.isna(as_of) or as_of.tz is not None:
        raise ValueError('기준일 형식 오류')
    if dates.max() > as_of:
        raise ValueError('미래 거래일')
    values = frame[columns[1:]].apply(pd.to_numeric, errors='coerce')
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError('가격·거래량 결측 또는 비유한 값')
    if (not values[['open', 'high', 'low', 'close']].gt(0).all().all()
            or not values.volume.ge(0).all()
            or not values.high.ge(values[['open', 'close', 'low']].max(axis=1)).all()
            or not values.low.le(values[['open', 'close', 'high']].min(axis=1)).all()):
        raise ValueError('OHLC·거래량 구조 오류')
    if 'symbol' in frame and frame.symbol.nunique(dropna=False) != 1:
        raise ValueError('복수 종목 혼합')
    try:
        import exchange_calendars as xcals
        calendar = xcals.get_calendar('XSHG')
        sessions = pd.DatetimeIndex(calendar.sessions_in_range(dates.min(), dates.max())).tz_localize(None)
    except Exception as exc:
        raise ValueError('거래소 달력 검증 실패') from exc
    if set(dates) != set(sessions):
        raise ValueError('비거래일 또는 거래일 누락')
    frame['date'] = dates
    frame[columns[1:]] = values
    return frame.sort_values('date')


def stage_readiness(daily, *, as_of_date=None):
    """Report each prerequisite independently; no trusted adjusted history exists.

    30 completed weeks support MA30; 34 support its four-week slope; 35
    support the previous bar's slope for a comparable prior Stage decision.
    A prior valid Stage label and reviewed adjusted/reconciled history are
    also required. Length alone never satisfies either evidence requirement.
    """
    result = dict(stage_label='판정 보류', completed_weeks=0,
                  required_completed_weeks=REQUIRED_COMPLETED_WEEKS,
                  input_valid=False, ma30_ready=False, slope4_ready=False,
                  prior_comparison_ready=False, adjusted_history_verified=False,
                  previous_stage_verified=False, stage_ready=False,
                  ma30=None, slope4_pct=None, ret26_pct=None,
                  stage2_new_entry=None, operational_eligible=False)
    try:
        frame = validated_daily(daily, as_of_date=as_of_date)
        weeks = weekly_bars(frame, as_of_date=as_of_date, calendar_name='XSHG', min_bars=1)
        # The shared engine excludes trailing partial weeks. A snapshot may
        # also begin midweek; that first bar cannot count as a completed week.
        import exchange_calendars as xcals
        first = frame.date.min()
        monday = first - pd.Timedelta(days=first.weekday())
        try:
            first_sessions = xcals.get_calendar('XSHG').sessions_in_range(
                monday, monday + pd.Timedelta(days=4)).tz_localize(None)
        except Exception as exc:
            raise ValueError('거래소 달력 검증 실패') from exc
        if weeks is not None and len(first_sessions) and first != first_sessions[0]:
            weeks = weekly_bars(frame[frame.date > monday + pd.Timedelta(days=4)],
                                as_of_date=as_of_date, calendar_name='XSHG', min_bars=1)
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        result['stage_reason'] = '가격 검증 실패 · ' + str(exc)
        return result
    result['input_valid'] = True
    count = 0 if weeks is None else len(weeks)
    result['completed_weeks'] = count
    result['ma30_ready'] = count >= 30 and bool(np.isfinite(weeks.iloc[-1].ma30))
    result['slope4_ready'] = count >= 34 and bool(np.isfinite(weeks.iloc[-1].slope4_pct))
    result['prior_comparison_ready'] = count >= 35 and bool(np.isfinite(weeks.iloc[-2].slope4_pct))
    missing = []
    if not result['ma30_ready']:
        missing.append('30개 완료 주봉 부족')
    if not result['slope4_ready']:
        missing.append('4주 MA 기울기 근거 부족(34주 필요)')
    if not result['prior_comparison_ready']:
        missing.append('이전 단계 비교 근거 부족(35주 필요)')
    missing.extend(['조정 기준 미검증', '이전 Stage 미검증'])
    result['stage_reason'] = ' · '.join(missing)
    return result
