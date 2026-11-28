"""Read-only rows and chart histories for the common country and sector explorer."""
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from china_kis_stage import load_kis_stage, private_root
from china_stage import stage_readiness, validated_daily
from hong_kong_etf_research import CANDIDATES, HONG_KONG, REPORT_FILE, completed_session
from market_data import completed_bar_cutoff_date
from stage_engine import relative_return_difference, weekly_bars
from unified_stock_explorer import stock_one_year_returns

MAINLAND = "중국 본토"
HK_CHINA = "홍콩 상장 중국기업"
HK_LARGE = "홍콩 상장 대형주"
HK_LOCAL = "홍콩 자체 시장"
CSI300 = "510300"
CSI300_REPORT = "csi300_kis_history.json"
MARKETS = {CSI300: MAINLAND, "02828": HK_CHINA, "02800": HK_LARGE, "EWH": HK_LOCAL}
SECTOR_SCOPES = (MAINLAND, HK_CHINA, HK_LARGE, HK_LOCAL)
HK_EXPOSURES = {
    "03033": "홍콩 상장 기술기업",
    "03102": "해외 상장 중국 인터넷 기업",
    "03069": "홍콩 상장 바이오 기업",
    "02806": "중국 소비 브랜드",
    "03448": "중국 핵심 기술기업",
    "02820": "중국 바이오 기업",
    "03191": "중국 반도체 기업",
    "02845": "중국 전기차·배터리 기업",
    "03456": "홍콩 상장 기술기업",
    "02826": "중국 클라우드 기업",
}
# Hong Kong-listed underlying equities. Funds with an A-share or broader
# offshore mandate are compared in the wider HK-listed ETF scope.
HK_CHINA_SECTORS = {"03033", "03069", "03456"}


def mainland_session(now):
    cutoff = completed_bar_cutoff_date("SHS", now_kst=now)
    return pd.Timestamp(xcals.get_calendar("XSHG").date_to_session(cutoff, direction="previous")).tz_localize(None)


def private_file(directory, filename):
    path = (directory / filename).resolve()
    if path.parent != directory:
        raise PermissionError("개인 스냅샷 경로 오류")
    return path


def _read_json(directory, filename):
    return json.loads(private_file(directory, filename).read_text(encoding="utf-8"))


def _history(data, symbol, expected, today, calendar):
    daily = pd.DataFrame(data)
    if daily.empty:
        return None, {}
    if "symbol" not in daily or not daily.symbol.eq(symbol).all():
        raise ValueError("개인 스냅샷 종목 불일치")
    daily = validated_daily(daily, as_of_date=expected, calendar_name=calendar)
    metrics = stage_readiness(daily, as_of_date=today, price_basis="KIS_ADJUSTED", calendar_name=calendar)
    if not metrics["input_valid"]:
        return None, metrics
    metrics["last_daily_date"] = daily.date.max()
    if daily.date.max() != expected:
        metrics.update(stage_ready=False, stage_label="데이터 오래됨 · 판정 보류",
                       stage2_new_entry=None, ret26_pct=None)
    weekly = weekly_bars(daily, as_of_date=today, calendar_name=calendar, min_bars=1)
    return (daily, weekly), metrics


def _load_hk(root, now, expected):
    report = _read_json(root, REPORT_FILE)
    summary = report["summary"]
    if (summary["exchange"], summary["currency"], summary["operational_eligible"]) != ("HKS", "HKD", 0):
        raise ValueError("홍콩 보고서 시장 정보 불일치")
    observations = {item["symbol"]: item for item in summary["observations"]}
    results = {item["symbol"]: item for item in report["results"]}
    if summary["latest_expected_session"] != expected.date().isoformat():
        return {}, {}, "홍콩 보고서 거래일 " + str(summary["latest_expected_session"])
    metrics, histories = {}, {}
    today = now.astimezone(HONG_KONG).date()
    for symbol, observation in observations.items():
        if (symbol not in CANDIDATES or observation.get("master_verified") is not True
                or observation.get("latest_session") != expected.date().isoformat()):
            continue
        metric = results.get(symbol, {})
        metrics[symbol] = {"completed_weeks": observation.get("completed_weeks"), "last_daily_date": expected}
        if (observation["status"] == "stage_ready" and metric.get("stage_ready") is True
                and metric.get("operational_eligible") is False):
            metrics[symbol] = dict(metric, last_daily_date=expected)
        history = report.get("histories", {}).get(symbol)
        if history and observation["status"] in {"stage_ready", "insufficient_weeks"}:
            try:
                series, metric = _history(history, symbol, expected, today, "XHKG")
            except (ValueError, KeyError, TypeError):
                metrics[symbol] = {"stage_label": "개인 가격 검증 실패", "last_daily_date": expected}
                continue
            metrics[symbol] = metric
            if series is not None:
                histories[symbol] = series
    return metrics, histories, "홍콩 보고서 거래일 " + expected.date().isoformat()


def _usd_returns(daily, quotes, weekly):
    if quotes is None:
        return None, None
    all_closes = daily.set_index("date").close * quotes.reindex(daily.date)
    if pd.isna(all_closes.iloc[-1]):
        return None, None
    # Use FX from the actual end session in each week, including holiday weeks.
    last_sessions = all_closes.groupby(pd.Grouper(freq="W-FRI")).nth(-1)
    week_dates = last_sessions.index.to_period("W-FRI").end_time.normalize()
    weekly_closes = pd.Series(last_sessions.to_numpy(), index=week_dates)
    ret26 = None
    if weekly is not None and len(weekly) >= 27:
        usd = weekly_closes.reindex(weekly.date)
        ret26 = (usd.iloc[-1] / usd.iloc[-27] - 1) * 100
    ret1y = stock_one_year_returns(
        all_closes.rename("close").reset_index().assign(symbol="USD")
    ).get("USD")
    return ret26, ret1y


def _fx_quotes(root):
    fx = pd.read_csv(private_file(root, "china_market_fx.csv"), dtype={"currency": str})
    fx["date"] = pd.to_datetime(fx.date, format="%Y-%m-%d", errors="raise")
    if fx.duplicated(["currency", "date"]).any() or not fx.currency.isin(["CNY", "HKD"]).all():
        raise ValueError("환율 일자 또는 통화 오류")
    fx["usd_per_unit"] = pd.to_numeric(fx.usd_per_unit, errors="raise")
    if not (np.isfinite(fx.usd_per_unit) & fx.usd_per_unit.gt(0)).all():
        raise ValueError("환율 값 오류")
    return {currency: group.set_index("date").usd_per_unit for currency, group in fx.groupby("currency")}


def _research_row(symbol, market, sector, name, exchange, currency, exposure, benchmark, **metrics):
    kind = "market_etf" if symbol in MARKETS else "research_sector_etf"
    return dict(stage_label="개인 자료 연결 대기", stage_ready=False, ret26_pct=None, ret1y_pct=None, close=None, ma30=None, slope4_pct=None,
                last_daily_date=None, stage2_new_entry=None, previous_stage_label=None,
                price_available=False) | metrics | dict(
        symbol=symbol, market=market, sector=sector, name=name, exchange=exchange, currency=currency,
        investment_region=exposure, market_benchmark=benchmark, market_menu_group="국가",
        asset_type=kind, asset_type_norm=kind, china_market_research=True,
    )


def load_explorer(root=None, now=None):
    from china_private_pipeline import current_snapshot

    now = now or datetime.now(ZoneInfo("Asia/Seoul"))
    sh_session, hk_session = mainland_session(now), completed_session(now)
    today = now.astimezone(ZoneInfo("Asia/Shanghai")).date()
    mainland = pd.read_csv(Path(__file__).with_name("data") / "monitoring_universe.csv", dtype=str)
    mainland = mainland[mainland.exchange.eq("SHS") & mainland.asset_type.eq("sector_etf")
                        & mainland.active.eq("false")]
    mainland_metrics, hk_metrics, histories, notes, quotes = {}, {}, {}, [], {}
    if root:
        try:
            root = private_root(root)
        except (ValueError, OSError):
            root = None
    if root:
        try:
            snapshot = current_snapshot(root)
            rows, valid, _ = load_kis_stage(snapshot, as_of_date=today, include_all=True)
            mainland_metrics = rows.set_index("symbol").to_dict("index")
            for symbol, daily in valid.groupby("symbol"):
                metrics = mainland_metrics[symbol]
                if daily.date.max() > sh_session:
                    metrics.update(stage_ready=False, stage_label="미완료 거래일 · 판정 보류",
                                   stage2_new_entry=None, ret26_pct=None)
                    continue
                metrics["last_daily_date"] = daily.date.max()
                if daily.date.max() != sh_session:
                    metrics.update(stage_ready=False, stage_label="데이터 오래됨 · 판정 보류",
                                   stage2_new_entry=None, ret26_pct=None)
                histories[symbol] = (
                    daily, weekly_bars(daily, as_of_date=today, calendar_name="XSHG", min_bars=1)
                )
        except (OSError, ValueError, KeyError, TypeError):
            notes.append("본토 개인 스냅샷 미확인")
        try:
            report = _read_json(root, CSI300_REPORT)
            if (report["exchange"], report["currency"], report["price_basis"], report["master_verified"]) != (
                "SHS", "CNY", "KIS_ADJUSTED", True
            ):
                raise ValueError("CSI 300 보고서 출처 불일치")
            history, metrics = _history(report["history"], CSI300, sh_session, today, "XSHG")
            mainland_metrics[CSI300] = metrics
            if history is not None:
                histories[CSI300] = history
        except (OSError, ValueError, KeyError, TypeError):
            notes.append("CSI 300 개인 가격 미확인")
        try:
            hk_metrics, hk_histories, report_note = _load_hk(root, now, hk_session)
            histories.update(hk_histories)
            notes.append(report_note)
        except (OSError, ValueError, KeyError, TypeError):
            notes.append("홍콩 개인 보고서 미확인")
        try:
            quotes = _fx_quotes(root)
        except (OSError, ValueError, KeyError, TypeError):
            pass
    rows = [_research_row(CSI300, MAINLAND, "시장", "Huatai-PineBridge CSI 300 ETF",
                          "SHS", "CNY", MAINLAND, CSI300, **mainland_metrics.get(CSI300, {}))]
    for item in mainland.itertuples():
        metrics = {k: v for k, v in mainland_metrics.get(item.symbol, {}).items()
                   if k not in {"name", "sector", "exchange", "currency"}}
        rows.append(_research_row(item.symbol, MAINLAND, item.sector, item.name,
                                  "SHS", "CNY", MAINLAND, CSI300, **metrics))
    for symbol, (sector, name, _) in CANDIDATES.items():
        market = MARKETS.get(symbol, HK_CHINA if symbol in HK_CHINA_SECTORS else HK_LARGE)
        exposure = HK_EXPOSURES.get(symbol, market)
        metrics = {k: v for k, v in hk_metrics.get(symbol, {}).items()
                   if k not in {"symbol", "sector", "index"}}
        rows.append(_research_row(symbol, market, "시장" if symbol in MARKETS else sector, name,
                                  "HKS", "HKD", exposure, "02828" if market == HK_CHINA else "02800", **metrics))
    for row in rows:
        symbol = row["symbol"]
        if symbol in histories:
            daily, weekly = histories[symbol]
            row["price_available"] = True
            if row["asset_type"] == "market_etf":
                if row.get("stage_ready"):
                    row["ret26_pct"], row["ret1y_pct"] = _usd_returns(daily, quotes.get(row["currency"]), weekly)
                else:
                    row["ret26_pct"] = None
            elif row.get("stage_ready"):
                row["ret1y_pct"] = stock_one_year_returns(daily).get(symbol)
        elif row["asset_type"] == "market_etf":
            row["ret26_pct"] = None
        if symbol == "03456" and not row.get("stage_ready"):
            row["stage_label"] = "연구 관찰 · 이력 부족"
    return pd.DataFrame(rows), histories, notes


def sectors_for(rows, histories, scope):
    sectors = rows.loc[rows.asset_type_norm.eq("research_sector_etf")].copy()
    if scope == HK_LARGE:
        sectors = sectors.loc[sectors.exchange.eq("HKS")].copy()
        sectors["market"] = HK_LARGE
        sectors["market_benchmark"] = "02800"
    else:
        sectors = sectors.loc[sectors.market.eq(scope)].copy()

    def relative(row):
        benchmark = row.market_benchmark
        if row.symbol not in histories or benchmark not in histories or not row.stage_ready:
            return None
        benchmark_row = rows.loc[rows.symbol.eq(benchmark)].iloc[0]
        if row.currency != benchmark_row.currency or not benchmark_row.stage_ready:
            return None
        asset, reference = histories[row.symbol][1], histories[benchmark][1]
        if asset is not None and reference is not None:
            return relative_return_difference(asset, reference).iloc[-1]

    if not sectors.empty:
        sectors["rs_market_26w_pct"] = sectors.apply(relative, axis=1)
    return sectors


def related_stocks(stocks, exchange, benchmark):
    exchanges = {"SHS", "SZS"} if exchange == "SHS" else {"HKS"}
    return stocks.loc[stocks.exchange.isin(exchanges) & stocks.sector_benchmark.eq(benchmark)]
