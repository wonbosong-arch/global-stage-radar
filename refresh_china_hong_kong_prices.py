"""Collect Shanghai and Hong Kong closes into the existing private S3 snapshot."""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd
import requests

from automation.check_scheduled_daily_prices import china_session_date
from china_benchmark_probe import MASTER_URL as SH_MASTER_URL, benchmark_identity
from china_kis_stage import PRICE_FILE, load_kis_stage, prepare, private_root
from china_market_explorer import CSI300, CSI300_REPORT, mainland_session
from china_market_fx import COLUMNS as FX_COLUMNS, FX_FILE, fetch_quotes, fixing_date, validate_quotes
from china_private_delivery import EXPLORER_FILES, configured_store, publish, sync
from china_stage import stage_readiness, validated_daily
from hong_kong_etf_research import CANDIDATES, MASTER_URL as HK_MASTER_URL, REPORT_FILE, completed_session
from hong_kong_etf_research import master_identities, write_private_report
from kis_provider import KISError, KISOverseasPrices

ROOT = Path(__file__).resolve().parent
PRICE_COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume"]
CALENDARS = {"SHS": "XSHG", "HKS": "XHKG"}
CURRENCIES = {"SHS": "CNY", "HKS": "HKD"}


def target_sessions(now, scheduled_at="", *, catch_up=False):
    if not scheduled_at:
        if catch_up:
            raise ValueError("Catch-up requires a scheduled time")
        return {"SHS": mainland_session(now), "HKS": completed_session(now)}
    day = pd.Timestamp(china_session_date(scheduled_at, catch_up=catch_up))
    return {exchange: day for exchange, name in CALENDARS.items() if xcals.get_calendar(name).is_session(day)}


def verified_symbols(exchange):
    response = requests.get(SH_MASTER_URL if exchange == "SHS" else HK_MASTER_URL, timeout=25)
    response.raise_for_status()
    if exchange == "SHS":
        return {CSI300} if benchmark_identity(response.content) else set()
    return master_identities(response.content)


def saved_inputs(snapshot, today):
    histories = {}
    fx = pd.DataFrame(columns=FX_COLUMNS)
    if snapshot is None:
        return histories, validate_quotes(fx)
    _, mainland, _ = load_kis_stage(snapshot, as_of_date=today, include_all=True)
    histories.update(dict(iter(mainland.groupby("symbol"))))
    hk_path, benchmark_path = snapshot / REPORT_FILE, snapshot / CSI300_REPORT
    if hk_path.is_file():
        report = json.loads(hk_path.read_text(encoding="utf-8"))
        if report.get("rolling"):
            for symbol, rows in report["histories"].items():
                if symbol not in CANDIDATES:
                    raise ValueError("Unexpected Hong Kong symbol")
                frame = validated_daily(pd.DataFrame(rows), as_of_date=today, calendar_name="XHKG")
                if not frame.symbol.eq(symbol).all():
                    raise ValueError("Hong Kong price identity mismatch")
                histories[symbol] = frame
    if benchmark_path.is_file():
        report = json.loads(benchmark_path.read_text(encoding="utf-8"))
        if report["history"]:
            if (report["symbol"], report["exchange"], report["currency"],
                    report["price_basis"], report["master_verified"]) != (CSI300, "SHS", "CNY", "KIS_ADJUSTED", True):
                raise ValueError("Shanghai benchmark identity mismatch")
            frame = validated_daily(pd.DataFrame(report["history"]), as_of_date=today)
            if not frame.symbol.eq(CSI300).all():
                raise ValueError("Shanghai benchmark price identity mismatch")
            histories[CSI300] = frame
    if (snapshot / FX_FILE).is_file():
        fx = pd.read_csv(snapshot / FX_FILE)
    return histories, validate_quotes(fx)


def save_generation(root, histories, fx, mainland, source_commit):
    generation = uuid4().hex
    path = private_root(root / "generations" / generation)
    if path.parent.parent != root:
        raise PermissionError("Private snapshot escaped storage root")
    path.mkdir(parents=True)
    frames = [histories[symbol] for symbol in mainland if symbol in histories]
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=PRICE_COLUMNS)
    combined.to_csv(path / PRICE_FILE, index=False)
    prepare(path, source_commit=source_commit, observed_symbols=combined.symbol.unique())
    hk = {symbol: histories[symbol].to_dict("records") for symbol in CANDIDATES if symbol in histories}
    write_private_report(path / REPORT_FILE, {
        "rolling": True, "summary": {"exchange": "HKS", "currency": "HKD", "operational_eligible": 0,
                                      "observations": []}, "results": [], "histories": hk,
    })
    benchmark = histories.get(CSI300)
    write_private_report(path / CSI300_REPORT, {
        "symbol": CSI300, "exchange": "SHS", "currency": "CNY", "price_basis": "KIS_ADJUSTED",
        "master_verified": benchmark is not None,
        "history": benchmark.to_dict("records") if benchmark is not None else [],
    })
    fx.to_csv(path / FX_FILE, index=False)
    temporary = root / (generation + ".tmp")
    temporary.write_text(json.dumps({"generation": generation}), encoding="utf-8")
    os.replace(temporary, root / "current.json")


def collect(root, store, now, targets, source_commit, *, client_factory=KISOverseasPrices,
            verify=verified_symbols, get_fx=fetch_quotes):
    if not targets:
        return {"sessions": {}, "price_requests": 0, "missing_prices": [], "missing_fx": [], "published": False}
    root = private_root(root)
    today = now.astimezone(ZoneInfo("Asia/Seoul")).date()
    # Read durable state after acquiring the shared queue. Separate Actions
    # runners always resume using the same private object pointer.
    snapshot = sync(root, store, missing_ok=True, as_of_date=today)
    histories, fx = saved_inputs(snapshot, today)
    manifest = pd.read_csv(ROOT / "data/china_candidate_observation_manifest.csv", dtype=str)
    mainland = sorted(manifest.loc[manifest.exchange.eq("SHS"), "symbol"].unique())
    by_market = {"SHS": [CSI300, *mainland], "HKS": list(CANDIDATES)}
    client = None
    changed = False
    requested = 0
    missing = []
    for exchange, target in targets.items():
        pending = [symbol for symbol in by_market[exchange]
                   if symbol not in histories or histories[symbol].date.max() < target]
        if not pending:
            continue
        identity = set(pending)
        needs_master = set(pending) if exchange == "HKS" else set(pending) & {CSI300}
        needs_master -= histories.keys()
        if needs_master:
            try:
                identity -= needs_master - verify(exchange)
            except (requests.RequestException, ValueError, KeyError, OSError):
                identity -= needs_master
        for symbol in pending:
            if symbol not in identity:
                missing.append(symbol)
                continue
            if client is None:
                client = client_factory()
            requested += 1
            try:
                fresh = client.daily_bars(symbol, exchange=exchange, end_date=target.strftime("%Y%m%d"), max_pages=3)
                if fresh.empty or not fresh.symbol.eq(symbol).all():
                    raise ValueError("Missing or mismatched KIS history")
                fresh = validated_daily(fresh, as_of_date=target, calendar_name=CALENDARS[exchange])
                metrics = stage_readiness(fresh, as_of_date=target, price_basis="KIS_ADJUSTED",
                                          calendar_name=CALENDARS[exchange])
                if (not metrics["input_valid"] or fresh.date.max() != target
                        or (symbol in histories and not metrics["stage_ready"]
                            and len(fresh) < len(histories[symbol]))):
                    raise ValueError("Unavailable or incomplete closing history")
            except (KISError, ValueError, TypeError, KeyError, AttributeError):
                missing.append(symbol)
                continue
            histories[symbol] = fresh
            changed = True

    required_fx = {CURRENCIES[exchange]: fixing_date(target.date()) for exchange, target in targets.items()}
    frankfurt = now.astimezone(ZoneInfo("Europe/Berlin"))
    last_published = fixing_date(frankfurt.date() - timedelta(days=int(frankfurt.hour < 16)))
    saved = set(zip(fx.currency, fx.date.dt.date))
    pending_fx = {currency: min(day, last_published) for currency, day in required_fx.items()
                  if (currency, min(day, last_published)) not in saved}
    if pending_fx:
        # Initial download covers the one-year endpoint; future runs request
        # only the gap since the most recent quote and only missing currencies.
        latest = fx.groupby("currency").date.max().dt.date.to_dict()
        start = min(min(latest.get(ccy, day - timedelta(days=400)) + timedelta(days=1), day)
                    for ccy, day in pending_fx.items())
        try:
            new_fx = validate_quotes(get_fx(start, max(pending_fx.values()), sorted(pending_fx)))
            new_fx = new_fx.loc[
                [(currency in pending_fx and start <= day <= pending_fx[currency] and (currency, day) not in saved)
                 for currency, day in zip(new_fx.currency, new_fx.date.dt.date)]
            ]
            if not new_fx.empty:
                fx = pd.concat([fx, new_fx] if not fx.empty else [new_fx], ignore_index=True)
                fx = fx.sort_values(["currency", "date"])
                saved = set(zip(fx.currency, fx.date.dt.date))
                changed = True
        except (requests.RequestException, ValueError, TypeError, KeyError, ArithmeticError):
            pass
    if changed:
        save_generation(root, histories, fx, mainland, source_commit)
        publish(root, store, as_of_date=today, files=EXPLORER_FILES)
    return {"sessions": {exchange: str(target.date()) for exchange, target in targets.items()},
            "price_requests": requested, "missing_prices": missing,
            "missing_fx": [ccy for ccy, day in required_fx.items() if (ccy, day) not in saved],
            "published": changed}


def main():
    try:
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        catch_up = os.environ.get("CHINA_CATCH_UP") == "true"
        scheduled = os.environ.get("SCHEDULED_AT", "")
        targets = target_sessions(now, scheduled, catch_up=catch_up)
        with TemporaryDirectory(prefix="china-close-") as directory:
            result = collect(Path(directory), configured_store("publish"), now, targets,
                             os.environ["GITHUB_SHA"])
        print(json.dumps(result))
        return int(catch_up and bool(result["missing_prices"] or result["missing_fx"]))
    except Exception as error:
        print(json.dumps({"private_collection": "failed", "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
