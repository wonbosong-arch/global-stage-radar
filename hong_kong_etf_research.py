"""Read-only HKD ETF research using KIS adjusted prices and the China Stage rules."""
import argparse
from datetime import datetime, time
from io import BytesIO
import json
import os
from tempfile import NamedTemporaryFile
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd
import requests

from china_kis_stage import private_root
from china_stage import stage_readiness
from kis_provider import KISError, KISOverseasPrices

MASTER_URL = "https://new.real.download.dws.co.kr/common/master/hksmst.cod.zip"
CALENDAR = "XHKG"
HONG_KONG = ZoneInfo("Asia/Hong_Kong")
REPORT_FILE = "hong_kong_etf_stage.json"

# One HKD counter per fund and one representative per tracked index.
# The master uses five-digit symbols. Tokens check the expected fund identity.
CANDIDATES = {
    "02800": ("항셍지수", "Hang Seng Index", ("TRACKER", "HONG KONG")),
    "02828": ("홍콩 상장 중국 대형주", "Hang Seng China Enterprises Index", ("HANG SENG", "CHINA ENTERPRISES")),
    "03033": ("홍콩 상장 기술주", "Hang Seng TECH Index", ("CSOP", "HANG SENG TECH")),
    "03102": ("역외 중국 인터넷", "CSI Overseas China Internet Index", ("KRANESHARES", "CHINA INTERNET")),
    "03069": ("홍콩 상장 바이오", "Hang Seng Biotech Index", ("CHINAAMC", "HONG KONG BIOTECH")),
    "02806": ("중국 소비 브랜드", "Solactive China Consumer Brand Index", ("GLOBAL X", "CHINA CONSUMER BRAND")),
    "03448": ("중국 핵심 기술주", "Mirae Asset China Tech Top 30 Index", ("GLOBAL X", "CHINA CORE TECH")),
    "02820": ("중국 바이오", "Solactive China Biotech Index", ("GLOBAL X", "CHINA BIOTECH")),
    "03191": ("중국 반도체", "FactSet China Semiconductor Index", ("GLOBAL X", "CHINA SEMICONDUCTOR")),
    "02845": ("중국 전기차·배터리", "Solactive China Electric Vehicle and Battery Index", ("GLOBAL X", "ELECTRIC VEHICLE", "BATTERY")),
    "03456": ("홍콩 상장 기술주 100", "HKEX Tech 100 Index", ("HKEX TECH 100",)),
    "02826": ("중국 클라우드", "Solactive China Cloud Computing Index", ("GLOBAL X", "CHINA CLOUD COMPUTING")),
}


def master_identities(content):
    """Match KIS ETF type, HKD currency and names to the official selections."""
    with ZipFile(BytesIO(content)) as archive:
        with archive.open("HKSMST.COD") as source:
            rows = [line.decode("cp949").rstrip("\r\n").split("\t") for line in source]
    if not rows or any(len(row) != 24 for row in rows):
        raise ValueError("Unexpected KIS Hong Kong master schema")
    names = {}
    for row in rows:
        country, _, exchange, _, symbol, _, name, _, kind, currency = row[:10]
        symbol = symbol.strip()
        if symbol not in CANDIDATES:
            continue
        if symbol in names:
            raise ValueError("Duplicate KIS Hong Kong master symbol")
        names[symbol] = ""
        if (country, exchange, kind, currency) == ("HK", "HKS", "3", "HKD"):
            names[symbol] = name.upper().strip()
    return {symbol for symbol, (_, _, tokens) in CANDIDATES.items()
            if all(token in names.get(symbol, "") for token in tokens)}


def completed_session(now):
    now = now.astimezone(HONG_KONG)
    # Use a conservative end time after the closing auction. The existing
    # weekly engine independently excludes incomplete weeks.
    cutoff = pd.Timestamp(now.date())
    if now.time() < time(16, 15):
        cutoff -= pd.Timedelta(days=1)
    session = xcals.get_calendar(CALENDAR).date_to_session(cutoff, direction="previous")
    return pd.Timestamp(session).tz_localize(None)


def observe(client, identities, now):
    """Return research classifications and a public-safe observation summary."""
    now = now.astimezone(HONG_KONG)
    expected = completed_session(now)

    results, observations = [], []
    for symbol, (sector, index, _) in CANDIDATES.items():
        observation = {"symbol": symbol, "master_verified": symbol in identities}
        observations.append(observation)
        if symbol not in identities:
            observation["status"] = "master_unverified"
            continue
        try:
            daily = client.daily_bars(
                symbol, exchange="HKS", end_date=expected.strftime("%Y%m%d"), max_pages=3
            )
        except KISError:
            observation["status"] = "provider_error"
            continue
        if daily.empty:
            observation["status"] = "no_history"
            continue
        if "symbol" not in daily or not daily.symbol.eq(symbol).all():
            observation["status"] = "symbol_mismatch"
            continue
        daily = daily[daily.date.le(expected)]
        if daily.empty:
            observation["status"] = "no_completed_bars"
            continue
        latest = daily.date.max()
        result = stage_readiness(
            daily, as_of_date=now.date(), price_basis="KIS_ADJUSTED", calendar_name=CALENDAR
        )
        if latest != expected and result["input_valid"]:
            result.update(stage_ready=False, stage_label="데이터 오래됨 · 판정 보류",
                          stage2_new_entry=None, stage_reason="최신 홍콩 거래일 일봉 부족")
        results.append({"symbol": symbol, "sector": sector, "index": index, **result})
        if not result["input_valid"]:
            status = "invalid_history"
        elif latest != expected:
            status = "stale_history"
        elif result["stage_ready"]:
            status = "stage_ready"
        else:
            status = "insufficient_weeks"
        observation.update(status=status, daily_rows=len(daily),
                           latest_session=latest.date().isoformat(),
                           completed_weeks=result["completed_weeks"])
    return results, {"exchange": "HKS", "currency": "HKD", "as_of": now.date().isoformat(),
                     "latest_expected_session": str(expected.date()),
                     "master_verified": len(identities), "requested": len(CANDIDATES),
                     "stage_ready": sum(row["stage_ready"] for row in results),
                     "operational_eligible": 0, "observations": observations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master-only", action="store_true")
    parser.add_argument("--private-report-dir", help="Existing private directory outside a Git checkout")
    args = parser.parse_args()
    output_dir = private_root(args.private_report_dir) if args.private_report_dir else None
    if output_dir is not None and not output_dir.is_dir():
        parser.error("--private-report-dir must already exist")
    try:
        response = requests.get(MASTER_URL, timeout=25)
        response.raise_for_status()
        identities = master_identities(response.content)
        if args.master_only:
            print(json.dumps({"master_verified": sorted(identities), "requested": len(CANDIDATES)}))
            return 0
        rows, summary = observe(KISOverseasPrices(), identities, datetime.now(HONG_KONG))
    except Exception:
        # The KIS exceptions can contain upstream response text.
        print("KIS master or price probe could not run.")
        return 1
    if output_dir is not None:
        # Commit a complete report atomically so the private viewer never reads
        # a partially written or half-refreshed set of classifications.
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_dir, delete=False) as stream:
            temporary = stream.name
            json.dump({"summary": summary, "results": rows}, stream, ensure_ascii=False, default=str)
        os.replace(temporary, output_dir / REPORT_FILE)
    print(json.dumps(summary, indent=2))
    return int(not summary["stage_ready"])


if __name__ == "__main__":
    raise SystemExit(main())
