"""Quality guards and private KIS Stage analysis; never authorizes activation."""
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


def stage_readiness(daily, *, as_of_date=None, price_basis=None):
    """Report prerequisites and classify explicitly sourced KIS adjusted history.

    30 completed weeks support MA30; 34 support its four-week slope; 35
    support the previous bar's slope for a comparable prior Stage decision.
    KIS_ADJUSTED uses provider trust policy, not independent reconciliation.
    Legacy/unidentified inputs remain diagnostics only. Operational eligibility
    is always false; adjusted_history_verified means independent evidence only.
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
        if price_basis == 'KIS_ADJUSTED' and frame.close.pct_change().abs().gt(0.5).any():
            raise ValueError('조정주가 일간 변동 50% 초과 · 이상치 조사 필요')
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
    if price_basis == 'KIS_ADJUSTED' and not missing:
        from stage_engine import classify_stage, is_stale_daily_data
        # Absolute momentum screen: ret26 is NOT market-relative strength.
        # Reuse the common trend thresholds without inventing a benchmark.
        def classify(bar):
            return classify_stage(bar.close, bar.ma30, bar.slope4_pct,
                                  bar.ret26_pct, np.nan, 'sector_etf')
        last, previous = weeks.iloc[-1], weeks.iloc[-2]
        comparable = (last.date - previous.date == pd.Timedelta(days=7))
        label = classify(last)
        prior = classify(previous) if comparable else '이전 주 데이터 부족'
        stale = is_stale_daily_data(frame.date.max(), as_of_date=as_of_date)
        if stale:
            label = '데이터 오래됨 · 판정 보류'
        result.update(ma30=float(last.ma30), slope4_pct=float(last.slope4_pct),
                      ret26_pct=float(last.ret26_pct), close=float(last.close),
                      last_date=last.date, last_daily_date=frame.date.max(),
                      previous_stage_label=prior, previous_stage_verified=comparable,
                      stage_label=label, stage_ready=not stale,
                      price_basis=price_basis, adjustment_basis='KIS 제공 조정주가 신뢰',
                      classification_basis='MA30·4주 기울기·절대 26주 수익률 (시장 RS 아님)',
                      stage2_new_entry=(not stale and comparable and label == 'Stage 2 후보'
                                        and prior != 'Stage 2 후보'),
                      stage_reason='데이터 오래됨' if stale else '기본 품질·완료 주봉 검사 통과')
        return result
    missing.extend(['조정 기준 미검증', '이전 Stage 미검증'] if price_basis != 'KIS_ADJUSTED' else [])
    result['stage_reason'] = ' · '.join(missing)
    return result
