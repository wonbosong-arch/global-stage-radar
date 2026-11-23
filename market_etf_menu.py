"""Display-only grouping for the country and commodity menu."""

GLOBAL_MARKET_ETFS = {
    "ACWI": "전 세계 주식",
    "URTH": "MSCI World · 선진국",
    "IEMG": "MSCI 신흥국",
}
# Symbols used by the one-time read-only KIS probe.
GLOBAL_MARKET_RESEARCH_SYMBOLS = ("URTH", "IEMG")
US_EXCHANGES = frozenset({"NAS", "NYS", "AMS"})


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
