"""Conservative, review-only sector and benchmark suggestions for stock candidates."""
def proposed_stock_mapping(symbol: str, exchange: str, issuer_country_code: str = "") -> dict:
    """Return an explicitly unverified first-pass sector/benchmark suggestion."""
    groups = {
        "Semiconductors": """NVDA AVGO AMD ASML INTC LRCX AMAT TXN MRVL ARM MU ADI QCOM STX WDC MPWR NXPI TER ALAB TSM SNDK SKHY KLAC""",
        "Information Technology": """AAPL MSFT CSCO PLTR PANW CRWD FTNT SHOP ADP ADBE DDOG CDNS INTU SNPS ADSK ORCL SAP IBM ANET CRM ACN NOW DELL EQIX TRI GLW LITE MSTR""",
        "Communication Services": """GOOGL GOOG META NFLX TMUS CMCSA WBD NTES DIS VZ T SONY VOD APP""",
        "Consumer Discretionary": """AMZN TSLA COST BKNG SBUX PDD MAR MELI EBAY DASH ROST ABNB ORLY HD MCD TJX UBER TM BABA BUD UL NVO""",
        "Consumer Staples": """WMT PEP KO PG MDLZ MNST PM BTI MO UL BUD""",
        "Health Care": """AMGN GILD ISRG VRTX MRNA SNY NTRA ARGX REGN LLY JNJ ABBV UNH MRK NVS AZN TMO ABT PFE DHR NVO BMY CVS MDT MCK NVO""",
        "Financials": """CME HOOD JPM V MA BAC HSBC SMFG MS RY GS AXP TD C BLK NDAQ SCHW UBS BBVA MUFG MFG BMO BNS COF CB PGR CBOE SPGI BRK/A BRK/B SAN HDB WFC""",
        "Energy": """XOM CVX SHEL COP BKR FANG IMO TTE MPC BP VLO ET""",
        "Industrials": """CSX CTAS HON PCAR FAST GE HONA GEV CAT RTX BA LMT DE UNP ETN PH SPCX""",
        "Materials": """LIN BHP SCCO NEM APH""",
        "Utilities": """CEG AEP NEE""",
        "Real Estate": """WELL PLD EQIX""",
    }
    sector_by_symbol = {}
    for sector, symbols in groups.items():
        for item in symbols.split():
            sector_by_symbol[item] = sector
    # Correct commonly ambiguous assignments and ticker-specific sector proxies.
    sector_by_symbol.update({
        "NVDA": "Semiconductors", "AVGO": "Semiconductors", "MU": "Semiconductors",
        "AMD": "Semiconductors", "QCOM": "Semiconductors", "TSM": "Semiconductors",
        "SNDK": "Semiconductors", "STX": "Information Technology", "WDC": "Information Technology",
        "SHOP": "Information Technology", "PLTR": "Information Technology", "MSTR": "Information Technology", "APP": "Communication Services",
        "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
        "COST": "Consumer Staples", "SBUX": "Consumer Discretionary",
        "BABA": "Consumer Discretionary", "UL": "Consumer Staples", "BUD": "Consumer Staples",
        "NVO": "Health Care", "GE": "Industrials", "GEV": "Industrials",
        "EQIX": "Real Estate", "APH": "Information Technology", "GLW": "Information Technology",
        "SPGI": "Financials", "MCK": "Health Care", "ET": "Energy",
        "SMFG": "Financials", "MFG": "Financials", "HSBC": "Financials",
        "TM": "Consumer Discretionary", "SONY": "Consumer Discretionary",
        "TRI": "Industrials", "ACN": "Information Technology", "ADP": "Industrials",
        "FAST": "Industrials", "CTAS": "Industrials", "ORLY": "Consumer Discretionary",
        "WMT": "Consumer Staples", "MDLZ": "Consumer Staples", "MNST": "Consumer Staples",
    })
    symbol = str(symbol).strip().upper()
    exchange = str(exchange).strip().upper()
    issuer_country_code = str(issuer_country_code).strip().upper()
    # Minimal KRX sector suggestions; the starter universe only has a Korean
    # broad-market proxy and a semiconductor ETF, so avoid inventing other sector proxies.
    krx_sector_by_symbol = {
        "005930": "Semiconductors", "000660": "Semiconductors",
    }
    if exchange == "KRX":
        sector = krx_sector_by_symbol.get(symbol, "")
        return {
            "proposed_market": "South Korea",
            "proposed_sector": sector,
            "proposed_asset_type": "stock",
            "proposed_market_benchmark": "069500",
            "proposed_sector_benchmark": "091160" if sector == "Semiconductors" else "",
            "mapping_status": "first_pass_review_required" if sector else "sector_mapping_missing",
            "mapping_note": "KRX first-pass suggestion; verify ordinary-share status, sector and benchmark before approval."
            if sector else "KRX sector benchmark not mapped; verify manually and do not infer from the market benchmark.",
        }
    sector = sector_by_symbol.get(symbol, "")
    sector_benchmark_by_sector = {
        "Semiconductors": "SOXX",
        "Information Technology": "XLK",
        "Communication Services": "XLC",
        "Consumer Discretionary": "XLY",
        "Consumer Staples": "XLP",
        "Energy": "XLE",
        "Financials": "XLF",
        "Health Care": "XLV",
        "Industrials": "XLI",
        "Materials": "XLB",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
    }
    adr_market_proxies = {
        "CA": ("Canada", "EWC"),
        "CN": ("China", "MCHI"),
        "HK": ("Hong Kong", "EWH"),
        "IN": ("India", "INDA"),
        "JP": ("Japan", "EWJ"),
        "KR": ("South Korea", "EWY"),
        "TW": ("Taiwan", "EWT"),
        "BR": ("Brazil", "EWZ"),
        "AU": ("Australia", "EWA"),
        "MX": ("Mexico", "EWW"),
        "GB": ("Europe / United Kingdom", "VGK"),
        "DE": ("Europe / Germany", "VGK"),
        "FR": ("Europe / France", "VGK"),
        "NL": ("Europe / Netherlands", "VGK"),
        "CH": ("Europe / Switzerland", "VGK"),
        "SE": ("Europe / Sweden", "VGK"),
        "DK": ("Europe / Denmark", "VGK"),
        "ES": ("Europe / Spain", "VGK"),
        "IT": ("Europe / Italy", "VGK"),
    }
    if issuer_country_code in adr_market_proxies:
        issuer_market, market_benchmark = adr_market_proxies[issuer_country_code]
        proposed_market = f"{issuer_market} (ADR issuer; proxy)"
        market_note = (
            "ADR issuer-country/region proxy suggested from KIS depositary metadata; "
            "verify issuer domicile and suitability before approval."
        )
    else:
        proposed_market = "United States (US-listed instrument)"
        market_benchmark = "SPY"
        market_note = (
            "No supported issuer-country proxy identified; SPY is a US-listed-market fallback. "
            "Verify issuer, sector, security type and benchmark before approval."
        )
    return {
        "proposed_market": proposed_market,
        "proposed_sector": sector,
        "proposed_asset_type": "stock",
        "proposed_market_benchmark": market_benchmark,
        "proposed_sector_benchmark": sector_benchmark_by_sector.get(sector, ""),
        "mapping_status": "first_pass_review_required" if sector else "sector_mapping_missing",
        "mapping_note": market_note + (
            " Curated sector suggestion also requires verification."
            if sector else " No ticker sector mapping; verify sector manually."
        ),
    }
