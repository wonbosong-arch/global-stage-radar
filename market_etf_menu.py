"""Display-only grouping for the country and commodity menu."""

GLOBAL_MARKET_ETFS = {
    "ACWI": "전세계",
    "URTH": "선진국",
    "IEMG": "신흥국",
}
# Symbols used by the one-time read-only KIS probe.
GLOBAL_MARKET_RESEARCH_SYMBOLS = ("URTH", "IEMG")
US_EXCHANGES = frozenset({"NAS", "NYS", "AMS"})


COUNTRY_NAMES = {
    "United States": "미국",
    "Canada": "캐나다",
    "Europe": "유럽",
    "Japan": "일본",
    "South Korea": "한국",
    "Taiwan": "대만",
    "Hong Kong": "홍콩",
    "India": "인도",
    "China": "중국",
    "Brazil": "브라질",
    "Australia": "호주",
    "Mexico": "멕시코",
    "United Kingdom": "영국",
    "Germany": "독일",
    "France": "프랑스",
    "Switzerland": "스위스",
    "Singapore": "싱가포르",
    "Indonesia": "인도네시아",
    "South Africa": "남아프리카공화국",
}
COMMODITY_NAMES = {
    "Gold": "금",
    "Silver": "은",
    "Crude Oil": "원유",
    "Natural Gas": "천연가스",
    "Copper": "구리",
    "Agriculture": "농산물",
    "Industrial Metals": "산업금속",
    "Broad Commodities": "종합 원자재",
    "Platinum": "백금",
    "Corn": "옥수수",
    "Wheat": "밀",
    "Soybeans": "대두",
    "Precious Metals": "귀금속",
    "Energy": "에너지",
}


def market_asset_name(row):
    kind = row["asset_type_norm"]
    symbol = row["symbol"]
    if kind == "market_etf":
        if symbol in GLOBAL_MARKET_ETFS:
            return GLOBAL_MARKET_ETFS[symbol]
        if row.get("china_market_research") == True:
            return row["market"]
        if symbol == "EWH":
            return "홍콩 자체 시장"
        if symbol == "QQQ":
            return "미국 나스닥 100"
        market = row["market"]
        return COUNTRY_NAMES.get(market, market or row["name"])
    if kind in ("commodity_etf", "commodity"):
        if kind == "commodity" and symbol in ("GOLD", "OIL"):
            return {"GOLD": "금", "OIL": "원유"}[symbol]
        sector = row["sector"]
        return COMMODITY_NAMES.get(sector, sector or row["name"])
    return None


def market_menu_rows(screen, *, demo=False):
    """Keep listing venue distinct from a fund's country exposure."""
    asset_type = screen["asset_type_norm"]
    market = asset_type.eq("market_etf")
    commodity = asset_type.eq("commodity_etf")
    if demo:
        commodity = commodity | asset_type.eq("commodity")
        rows = screen.loc[market | commodity].copy()
    else:
        rows = screen.loc[(market | commodity) & screen["exchange"].isin(US_EXCHANGES)].copy()

    rows["market_menu_group"] = "국가"
    rows.loc[rows["asset_type_norm"].isin(["commodity_etf", "commodity"]), "market_menu_group"] = "원자재"
    global_market = rows["asset_type_norm"].eq("market_etf") & rows["symbol"].isin(GLOBAL_MARKET_ETFS)
    rows.loc[global_market, "market_menu_group"] = "글로벌 시장"
    return rows
