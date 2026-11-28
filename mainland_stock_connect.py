"""Broker-supported China A-share ETF research metadata and KIS identities."""
from dataclasses import dataclass
from io import BytesIO
from zipfile import ZipFile

import requests


@dataclass(frozen=True)
class ResearchETF:
    exchange: str
    name: str
    sector: str
    market_label: str = ""


# Each entry is listed in the Meritz overseas master and in HKEX's
# buy-and-sell list of 2026-11-27. These are private research ETFs.
RESEARCH_ETFS = {
    "510500": ResearchETF("SHS", "China Southern CSI 500 ETF", "시장", "중국 CSI 500"),
    "512100": ResearchETF("SHS", "China Southern CSI 1000 ETF", "시장", "중국 CSI 1000"),
    "159915": ResearchETF("SZS", "E Fund ChiNext ETF", "시장", "중국 ChiNext"),
    "588000": ResearchETF("SHS", "ChinaAMC STAR 50 ETF", "시장", "중국 STAR 50"),
    "159352": ResearchETF("SZS", "China Southern CSI A500 ETF", "시장", "중국 CSI A500"),
    "159526": ResearchETF("SZS", "Harvest CSI Robot ETF", "로봇"),
    "560780": ResearchETF("SHS", "GF CSI Semiconductor Materials and Equipment ETF", "반도체 소재·장비"),
    "561380": ResearchETF("SHS", "Guotai Hang Seng China A Power Grid Equipment ETF", "전력망 장비"),
    "159755": ResearchETF("SZS", "GF CNI New Energy Vehicle Battery ETF", "배터리"),
    "516110": ResearchETF("SHS", "Guotai CSI 800 Autos and Components ETF", "자동차·부품"),
    "159667": ResearchETF("SZS", "Guotai CSI Machine Tool ETF", "공작기계"),
    "159996": ResearchETF("SZS", "Guotai CSI All Share Household Appliances ETF", "가전"),
    "159883": ResearchETF("SZS", "Maxwealth CSI All Share Health Care Devices ETF", "의료기기"),
    "561560": ResearchETF("SHS", "Huatai-PineBridge CSI Electric Utilities ETF", "전력 유틸리티"),
    "516020": ResearchETF("SHS", "Hwabao CSI Subdivision Chemical Industry ETF", "화학"),
    "512630": ResearchETF("SHS", "GF CSI Satellite Industry ETF", "위성 산업"),
    "560280": ResearchETF("SHS", "GF CSI Construction Machinery ETF", "건설기계"),
    "159745": ResearchETF("SZS", "Guotai CSI All Share Construction Materials ETF", "건축자재"),
    "561360": ResearchETF("SHS", "Guotai CSI Oil and Gas Industry ETF", "석유·가스"),
    "562800": ResearchETF("SHS", "Harvest CSI Rare Metals Industry ETF", "희소금속"),
    "517520": ResearchETF("SHS", "Maxwealth CSI SH-SZ-HK Gold Industry Equity ETF", "금광주"),
    "159766": ResearchETF("SZS", "Fullgoal CSI Tourism ETF", "관광"),
    "159732": ResearchETF("SZS", "ChinaAMC CSI Consumer Electronics ETF", "소비자 전자기기"),
    "159852": ResearchETF("SZS", "ChinaAMC CSI All Share Software ETF", "소프트웨어"),
    "516510": ResearchETF("SHS", "E Fund CSI Cloud Computing and Big Data ETF", "클라우드·빅데이터"),
    "159851": ResearchETF("SZS", "ChinaAMC CSI Fintech ETF", "핀테크"),
    "560080": ResearchETF("SHS", "China Universal CSI Traditional Chinese Medicine ETF", "중의약"),
    "159828": ResearchETF("SZS", "Guotai CSI Medical Services ETF", "의료 서비스"),
    "510230": ResearchETF("SHS", "Guotai SSE 180 Financial ETF", "종합 금융"),
}


def kis_research_symbols(exchange):
    response = requests.get(
        f"https://new.real.download.dws.co.kr/common/master/{exchange.lower()}mst.cod.zip",
        timeout=25,
    )
    response.raise_for_status()
    with ZipFile(BytesIO(response.content)) as archive:
        raw = archive.read(f"{exchange}MST.COD")
    candidates = {symbol for symbol, fund in RESEARCH_ETFS.items() if fund.exchange == exchange}
    counts = dict.fromkeys(candidates, 0)
    for line in raw.decode("cp949").splitlines():
        row = line.split("\t")
        if (len(row) == 24 and (row[0], row[2], row[8], row[9]) == ("CN", exchange, "3", "CNY")
                and row[4] in counts and row[5] == exchange + row[4]):
            counts[row[4]] += 1
    return {symbol for symbol, count in counts.items() if count == 1}
