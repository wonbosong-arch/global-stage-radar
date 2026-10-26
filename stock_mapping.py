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
        # Explicit review-only assignments for symbols found in the current discovery queue.
        "CCEP": "Consumer Staples",
        "SPOT": "Communication Services",
        "SYK": "Health Care",
        "SNOW": "Information Technology",
        "EQNR": "Energy",
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
    # KRX mappings use the separate provisional ETF candidate list. These are
    # suggestions only: the candidate ETFs' observed prices do not approve a mapping.
    # Leave weak or structurally mismatched proxies blank rather than forcing them.
    krx_sector_by_symbol = {
        "005930": "Semiconductors", "000660": "Semiconductors",
        "373220": "Industrials", "009150": "Information Technology",
        "207940": "Health Care", "005380": "Consumer Discretionary",
        "105560": "Financials", "032830": "Financials",
        "068270": "Health Care", "055550": "Financials",
        "000270": "Consumer Discretionary", "006400": "Industrials",
        "012450": "Industrials", "034020": "Industrials",
        "086790": "Financials", "329180": "Industrials",
        "012330": "Consumer Discretionary", "000810": "Financials",
        "035420": "Internet",
        "402340": "Semiconductors",
        "028260": "Holding Companies", "034730": "Holding Companies",
        "138040": "Financials", "066570": "Information Technology",
        "096770": "Energy", "010120": "Industrials",
        "316140": "Financials", "005490": "Materials",
        "011200": "Industrials",
    }
    krx_sector_benchmark_by_symbol = {
        "005930": "091160", "000660": "091160", "402340": "091160",
        "373220": "305720", "006400": "305720",
        "009150": "266370", "066570": "266370",
        "207940": "266420", "068270": "266420",
        "005380": "091180", "000270": "091180", "012330": "091180",
        "105560": "091170", "055550": "091170", "086790": "091170", "316140": "091170",
        "032830": "140700", "000810": "140700", "138040": "140700",
        "012450": "102960", "034020": "102960", "329180": "102960", "010120": "102960",
        "096770": "117460", "005490": "117680", "011200": "140710",
    }
    if exchange == "KRX":
        sector = krx_sector_by_symbol.get(symbol, "")
        benchmark = krx_sector_benchmark_by_symbol.get(symbol, "")
        if symbol == "035420":
            mapping_note = (
                "NAVER is provisionally classified as Internet per user-directed classification. "
                "No close-fit sector ETF is assigned; keep the proposed sector benchmark blank "
                "until an internet-platform benchmark is reviewed. This is not mapping approval."
            )
        elif symbol in {"028260", "034730"}:
            mapping_note = (
                "User-directed provisional classification as a holding company. The diversified "
                "holding-company structure does not support a sufficiently close single-sector ETF; "
                "keep the sector benchmark blank pending review. Not approved or activated."
            )
        elif symbol == "138040":
            mapping_note = (
                "User-directed provisional Financials classification for Meritz Financial Group. "
                "The available bank ETF is not a close-fit proxy and insurance classification is "
                "an alternative for review; leave the sector benchmark blank pending review."
            )
        elif benchmark:
            mapping_note = (
                f"Provisional KRX sector ETF proxy {benchmark}; verify index constituents and fit "
                "for this issuer before approval. Price coverage is not mapping approval."
            )
        elif sector:
            mapping_note = (
                "Sector classification is provisional, but no sufficiently close KRX sector ETF "
                "proxy is assigned; keep the benchmark blank until reviewed."
            )
        else:
            mapping_note = (
                "KRX sector classification and benchmark remain unassigned; do not infer a sector "
                "from the broad-market benchmark."
            )
        return {
            "proposed_market": "South Korea",
            "proposed_sector": sector,
            "proposed_asset_type": "stock",
            "proposed_market_benchmark": "069500",
            "proposed_sector_benchmark": benchmark,
            "mapping_status": "first_pass_review_required" if sector else "sector_mapping_missing",
            "mapping_note": mapping_note,
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
