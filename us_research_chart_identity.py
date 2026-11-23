"""Reviewed common-equity listings for the saved US KIS candidate charts.

The source in each entry identifies the listed security by class, venue and
ticker. Each entry was matched to the candidate registry and a saved KIS
response from that venue. Keep issuer names in the key check to guard reuse
of a ticker. This evidence is scoped to charts from the candidate snapshot.
"""

REVIEWED_CHART_LISTINGS = {
    ("NYS", "AAT"): (
        "AMERICAN ASSETS TRUST INC", "AMERICAN ASSETS TRUST INC",
        "https://www.sec.gov/Archives/edgar/data/1500217/000150021726000052/aat-20260930.htm",
    ),
    ("NAS", "ADBE"): (
        "Adobe Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/796343/000079634326000003/adbe-20251128.htm",
    ),
    ("NAS", "AEP"): (
        "American Electric Power Company Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/81027/000000490426000072/aep-20260930.htm",
    ),
    ("NYS", "AKR"): (
        "ACADIA REALTY TRUST", "ACADIA REALTY TRUST",
        "https://www.sec.gov/Archives/edgar/data/899629/000119312526443763/akr-20260930.htm",
    ),
    ("NAS", "AMGN"): (
        "Amgen Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/318154/000031815426000155/amgn-20260930.htm",
    ),
    ("NYS", "ANET"): (
        "Arista Networks Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/1596532/000159653226000175/anet-20260630.htm",
    ),
    ("NYS", "BAC"): (
        "Bank of America Corporation", None,
        "https://www.sec.gov/Archives/edgar/data/70858/000007085826000353/bac-20260714.htm",
    ),
    ("NYS", "BXMT"): (
        "BLACKSTONE MORTGAGE TRUST INC", "BLACKSTONE MORTGAGE TRUST INC",
        "https://www.sec.gov/Archives/edgar/data/1061630/000106163026000097/bxmt-20260930.htm",
    ),
    ("NYS", "CAT"): (
        "Caterpillar Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/18230/000001823026000046/cat-20260630.htm",
    ),
    ("NAS", "CEG"): (
        "Constellation Energy Corporation", None,
        "https://www.sec.gov/Archives/edgar/data/1168165/000186827526000119/ceg-20260930.htm",
    ),
    ("NYS", "COLD"): (
        "AMERICOLD REALTY TRUST INC", "AMERICOLD REALTY TRUST INC",
        "https://www.sec.gov/Archives/edgar/data/1455863/000162828026061151/art-20260909.htm",
    ),
    ("NYS", "COP"): (
        "ConocoPhillips", None,
        "https://www.sec.gov/Archives/edgar/data/1163165/000116316526000045/cop-20260930.htm",
    ),
    ("NAS", "COST"): (
        "Costco Wholesale Corporation", None,
        "https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/cost-20260830.htm",
    ),
    ("NYS", "CPT"): (
        "CAMDEN PROPERTY TRUST", "CAMDEN PROPERTY TRUST",
        "https://www.sec.gov/Archives/edgar/data/906345/000162828026071470/cpt-20260930.htm",
    ),
    ("NYS", "CRM"): (
        "Salesforce Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/1108524/000110852426000190/crm-20260731.htm",
    ),
    ("NAS", "CSCO"): (
        "Cisco Systems Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/858877/000085887726000185/csco-20261024.htm",
    ),
    ("NAS", "CTBI"): (
        "COMMUNITY TRUST BANCORP INC", "COMMUNITY TRUST BANCORP INC",
        "https://www.sec.gov/Archives/edgar/data/350852/000035085226000072/ctb0926invpres8k.htm",
    ),
    ("NYS", "CVX"): (
        "Chevron Corporation", None,
        "https://www.sec.gov/Archives/edgar/data/93410/000009341026000200/cvx-20260930.htm",
    ),
    ("NYS", "DE"): (
        "Deere & Company", None,
        "https://www.sec.gov/Archives/edgar/data/315189/000110465926102213/de-20260802x10q.htm",
    ),
    ("NAS", "DHC"): (
        "DIVERSIFIED HEALTHCARE TRUST", "DIVERSIFIED HEALTHCARE TRUST",
        "https://www.sec.gov/Archives/edgar/data/1075415/000107541526000039/dhc-20260930.htm",
    ),
    ("NYS", "DIS"): (
        "Walt Disney Company", None,
        "https://www.sec.gov/Archives/edgar/data/1744489/000174448926000067/dis-20261117.htm",
    ),
    ("NYS", "DLR"): (
        "DIGITAL REALTY TRUST INC", "DIGITAL REALTY TRUST INC",
        "https://www.sec.gov/Archives/edgar/data/1494877/000110465926089296/dlr-20260630x10q.htm",
    ),
    ("NYS", "ENB"): (
        "ENBRIDGE INC", None,
        "https://www.sec.gov/Archives/edgar/data/895728/000119312526450714/enb-20260930.htm",
    ),
    ("NYS", "ESS"): (
        "ESSEX PROPERTY TRUST INC", "ESSEX PROPERTY TRUST INC",
        "https://www.sec.gov/Archives/edgar/data/1053059/000092052226000025/ess-20260911.htm",
    ),
    ("NYS", "ETN"): (
        "Eaton Corporation plc", None,
        "https://www.sec.gov/Archives/edgar/data/1551182/000155118226000040/etn-20260930.htm",
    ),
    ("NYS", "FCPT"): (
        "FOUR CORNERS PROPERTY TRUST INC", "FOUR CORNERS PROPERTY TRUST INC",
        "https://www.sec.gov/Archives/edgar/data/1650132/000119312526437877/fcpt-20260930.htm",
    ),
    ("NYS", "FR"): (
        "FIRST INDUSTRIAL REALTY TRUST", "FIRST INDUSTRIAL REALTY TRUST",
        "https://www.sec.gov/Archives/edgar/data/921825/000092182526000075/fr-20260930.htm",
    ),
    ("NYS", "FRT"): (
        "FEDERAL REALTY INVESTMENT TRUST", "FEDERAL REALTY INVESTMENT TRUST",
        "https://www.sec.gov/Archives/edgar/data/34903/000119312526443777/d159063d8k.htm",
    ),
    ("NYS", "GM"): (
        "GENERAL MOTORS CO", None,
        "https://www.sec.gov/Archives/edgar/data/1467858/000146785826000059/gm-20260930.htm",
    ),
    ("NYS", "HD"): (
        "Home Depot Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/354950/000162828026058715/hd-20260802.htm",
    ),
    ("NYS", "HLT"): (
        "HILTON WORLDWIDE HOLDINGS INC", None,
        "https://www.sec.gov/Archives/edgar/data/1585689/000158568926000054/hlt-20260930.htm",
    ),
    ("NYS", "IBM"): (
        "International Business Machines Corporation", None,
        "https://www.sec.gov/Archives/edgar/data/51143/000005114326000095/ibm-20260930.htm",
    ),
    ("NAS", "IDXX"): (
        "IDEXX LABORATORIES INC", None,
        "https://www.sec.gov/Archives/edgar/data/874716/000087471626000135/idxx-20260930.htm",
    ),
    ("NYS", "IRT"): (
        "INDEPENDENCE REALTY TRUST INC", "INDEPENDENCE REALTY TRUST INC",
        "https://www.sec.gov/Archives/edgar/data/1466085/000143774926034667/irt20260930_10q.htm",
    ),
    ("NAS", "KDP"): (
        "KEURIG DR PEPPER INC", None,
        "https://www.sec.gov/Archives/edgar/data/1418135/000141813526000066/kdp-20260930.htm",
    ),
    ("NAS", "KMB"): (
        "KIMBERLY CLARK CORP", None,
        "https://www.sec.gov/Archives/edgar/data/55785/000162828026070754/kmb-20260930.htm",
    ),
    ("NYS", "KO"): (
        "Coca-Cola Company", None,
        "https://www.sec.gov/Archives/edgar/data/21344/000162828026067844/ko-20261002.htm",
    ),
    ("NYS", "KRG"): (
        "KITE REALTY GROUP TRUST", "KITE REALTY GROUP TRUST",
        "https://www.sec.gov/Archives/edgar/data/1286043/000128604326000058/krg-20260930.htm",
    ),
    ("NAS", "LIN"): (
        "Linde plc", None,
        "https://www.sec.gov/Archives/edgar/data/1707925/000162828026068079/lin-20260930.htm",
    ),
    ("NYS", "LOW"): (
        "LOWE S COMPANIES INC", None,
        "https://www.sec.gov/Archives/edgar/data/60667/000006066726000072/low-20260501.htm",
    ),
    ("NYS", "LXP"): (
        "LXP INDUSTRIAL TRUST", "LXP INDUSTRIAL TRUST",
        "https://www.sec.gov/Archives/edgar/data/910108/000091010826000045/lxp-20260630.htm",
    ),
    ("NYS", "MCD"): (
        "McDonald's Corporation", None,
        "https://www.sec.gov/Archives/edgar/data/63908/000006390826000083/mcd-20260930.htm",
    ),
    ("NYS", "MPT"): (
        "MEDICAL PROPERTIES TRUST INC", "MEDICAL PROPERTIES TRUST INC",
        "https://www.sec.gov/Archives/edgar/data/1524607/000119312526451995/mpt-20260930.htm",
    ),
    ("NAS", "NFLX"): (
        "Netflix Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/1065280/000106528026000291/nflx-20260930.htm",
    ),
    ("NAS", "NTRS"): (
        "NORTHERN TRUST CORP", "NORTHERN TRUST CORP",
        "https://www.sec.gov/Archives/edgar/data/73124/000007312426000057/ntrs-20260928.htm",
    ),
    ("NYS", "ORCL"): (
        "Oracle Corporation", None,
        "https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm",
    ),
    ("NYS", "PDM"): (
        "PIEDMONT REALTY TRUST INC.", "PIEDMONT REALTY TRUST INC.",
        "https://www.sec.gov/Archives/edgar/data/1042776/000104277626000071/pdm-20260930.htm",
    ),
    ("NYS", "PEB"): (
        "PEBBLEBROOK HOTEL TRUST", "PEBBLEBROOK HOTEL TRUST",
        "https://www.sec.gov/Archives/edgar/data/1474098/000147409826000072/peb-20260930.htm",
    ),
    ("NAS", "PFBC"): (
        "PREFERRED BK LOS ANGELES CALIFORNIA", "PREFERRED BK LOS ANGELES CALIFORNIA",
        "https://s1.q4cdn.com/312270857/files/doc_downloads/Regulatory_Filings_Updated/2025/2025-Form-10-K_FINAL-w-Exhibit.pdf",
    ),
    ("NYS", "PG"): (
        "Procter & Gamble Company", None,
        "https://www.sec.gov/Archives/edgar/data/80424/000119312526372220/pg_ars_2026.pdf",
    ),
    ("NAS", "PLTR"): (
        "Palantir Technologies Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/1321655/000132165526000048/pltr-20260930.htm",
    ),
    ("NAS", "PSKY"): (
        "PARAMOUNT SKYDANCE CORP", None,
        "https://www.sec.gov/Archives/edgar/data/2041610/000204161026000054/psky-20260630.htm",
    ),
    ("NAS", "SBUX"): (
        "Starbucks Corporation", None,
        "https://www.sec.gov/Archives/edgar/data/829224/000082922426000162/sbux-20260927.htm",
    ),
    ("NYS", "SO"): (
        "SOUTHERN CO.", None,
        "https://www.sec.gov/Archives/edgar/data/3153/000009212226000069/so-20260930.htm",
    ),
    ("NYS", "STWD"): (
        "STARWOOD PROPERTY TRUST INC", "STARWOOD PROPERTY TRUST INC",
        "https://www.sec.gov/Archives/edgar/data/1465128/000146512826000031/stwd-20260930.htm",
    ),
    ("NYS", "TJX"): (
        "TJX Companies Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/109198/000010919826000048/tjx-20260801.htm",
    ),
    ("NAS", "TMUS"): (
        "T-Mobile US Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/1283699/000128369926000129/tmus-20260930.htm",
    ),
    ("NYS", "VNO"): (
        "VORNADO REALTY TRUST", "VORNADO REALTY TRUST",
        "https://www.sec.gov/Archives/edgar/data/1040765/000089968926000053/vno-20260930.htm",
    ),
    ("NYS", "WELL"): (
        "Welltower Inc.", None,
        "https://www.sec.gov/Archives/edgar/data/766704/000076670426000046/well-20260930.htm",
    ),
}


def reviewed_chart_identity(row, identity, master_rows):
    """Resolve only a reviewed name heuristic or a missing partial master."""
    listing = REVIEWED_CHART_LISTINGS.get((row["exchange"], row["symbol"]))
    if listing is None:
        return False
    issuer, master_name, _source = listing
    if (
        str(row.get("name", "")).strip().casefold() != issuer.casefold()
        or row.get("instrument_type") not in ("common_stock_candidate", "common_stock_candidate_unverified")
        or row.get("discovery_security_type", "") not in ("", "2", "stock")
        or str(row.get("discovery_dr_country_code", "")).strip().upper() not in ("", "US", "USA", "00", "0")
    ):
        return False
    if master_name is None:
        return identity["identity_basis"] == "missing_kis_master" and not identity["review_reasons"]
    return (
        identity["review_reasons"] == ["non_common_or_fund_signal"]
        and len(master_rows) == 1
        and str(master_rows.iloc[0].get("english_name", "")).strip().casefold() == master_name.casefold()
    )
