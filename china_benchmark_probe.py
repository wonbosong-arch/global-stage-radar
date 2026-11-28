"""Read-only identity and price probe for the selected Shanghai CSI 300 ETF."""
from datetime import datetime
from io import BytesIO
import json
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import requests

from china_market_explorer import CSI300, CSI300_REPORT, mainland_session
from china_stage import stage_readiness
from hong_kong_etf_research import write_private_report
from kis_provider import KISOverseasPrices

MASTER_URL = "https://new.real.download.dws.co.kr/common/master/shsmst.cod.zip"


def benchmark_identity(content):
    with ZipFile(BytesIO(content)) as archive:
        with archive.open("SHSMST.COD") as source:
            rows = (line.decode("cp949").rstrip("\r\n").split("\t") for line in source)
            matches = [row for row in rows if len(row) == 24 and row[4].strip() == CSI300]
    if len(matches) != 1:
        return False
    row = matches[0]
    return ((row[0], row[2], row[8], row[9]) == ("CN", "SHS", "3", "CNY")
            and "HUATAI-PINEBRIDGE" in row[7].upper() and "CSI 300 INDEX ETF" in row[7].upper())


def run_benchmark_probe(output_dir, *, master_only=False):
    try:
        response = requests.get(MASTER_URL, timeout=25)
        response.raise_for_status()
        if not benchmark_identity(response.content):
            raise ValueError("KIS master identity mismatch")
        summary = dict(symbol=CSI300, exchange="SHS", currency="CNY", master_verified=True)
        if not master_only:
            now = datetime.now(ZoneInfo("Asia/Shanghai"))
            expected = mainland_session(now)
            daily = KISOverseasPrices().daily_bars(CSI300, exchange="SHS",
                                                   end_date=expected.strftime("%Y%m%d"), max_pages=3)
            daily = daily.loc[daily.date.le(expected)]
            if daily.empty or not daily.symbol.eq(CSI300).all():
                raise ValueError("KIS returned no matching prices")
            metrics = stage_readiness(daily, as_of_date=now.date(), price_basis="KIS_ADJUSTED")
            if not metrics["stage_ready"] or daily.date.max() != expected:
                raise ValueError("CSI 300 price history is short, stale, or invalid")
            summary.update(latest_session=expected.date().isoformat(), completed_weeks=metrics["completed_weeks"])
            if output_dir is not None:
                write_private_report(output_dir / CSI300_REPORT, {
                    **summary, "price_basis": "KIS_ADJUSTED", "history": daily.to_dict("records"),
                })
        print(json.dumps(summary))
        return 0
    except Exception:
        print("CSI 300 KIS identity or adjusted price probe failed.")
        return 1
