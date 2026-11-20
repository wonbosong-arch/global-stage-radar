"""Reviewed issuer-to-ETF fit decisions corroborated by public SEC filings.

Nasdaq provides the current classification. The public filings below corroborate
individual issuers whose names or industry groups need additional review. The mapped KIS sector
ETF provides prices for Stage calculations.

Vanguard sector index portfolios, May 31, 2026
XLK https://www.sec.gov/Archives/edgar/data/52848/000005284826000893/vg_infotech.htm
XLC https://www.sec.gov/Archives/edgar/data/52848/000005284826000894/vg_communservices.htm
XLI https://www.sec.gov/Archives/edgar/data/52848/000005284826000895/vg_industrialsindx.htm
XLY https://www.sec.gov/Archives/edgar/data/52848/000005284826000882/vg_consumerdiscret.htm
XLV https://www.sec.gov/Archives/edgar/data/52848/000005284826000886/vg_healthcare.htm
XLE https://www.sec.gov/Archives/edgar/data/52848/000005284826000902/vg_energyindex.htm
XLF https://www.sec.gov/Archives/edgar/data/52848/000005284826000900/vg_financialsindex.htm
XLP https://www.sec.gov/Archives/edgar/data/52848/000005284826000896/vg_consumerstaples.htm
XLB https://www.sec.gov/Archives/edgar/data/52848/000005284826000881/vg_materialsindex.htm
XLU https://www.sec.gov/Archives/edgar/data/52848/000005284826000899/vg_utilitiesindex.htm

XLRE: iShares Core U.S. REIT ETF, equity REIT sections, July 31, 2026
https://www.sec.gov/Archives/edgar/data/1100663/000094040026038481/252021BR073126.htm
XLRE: Vanguard Real Estate Index Fund, property managers and developers, April 30, 2026
https://www.sec.gov/Archives/edgar/data/734383/000073438326000215/vg_realestateindex.htm
CNK / XLC: Cinemark 10-K, theatrical exhibition, December 31, 2025
https://www.sec.gov/Archives/edgar/data/1385280/000119312526056015/cnk-20251231.htm

Additional issuer review
- XLI distributors: https://www.sec.gov/Archives/edgar/data/915092/000141036826054543/NPORT_0CML_57433799_0326.htm
- XLI services, staffing and contractors: Vanguard Industrials Index Fund above and
  https://www.sec.gov/Archives/edgar/data/52848/000175272425016033/vg_industrialsindex.htm
- XLI equipment leasing: https://www.sec.gov/Archives/edgar/data/822977/000141036825027894/NPORT_58CI_70373214_0925.htm
  plus SUNB https://www.sec.gov/Archives/edgar/data/2083785/000162828026061146/snblt-20260731.htm
  and EQPT https://www.sec.gov/Archives/edgar/data/1693736/000162828025055961/eqpt-sx1.htm
- XLI auctions and waste: https://www.sec.gov/Archives/edgar/data/745467/000119312524051724/d792579dncsrs.htm
  and https://www.sec.gov/Archives/edgar/data/1780232/000110465926016748/gfl-20251231x40f.htm
- XLI transport: freight carriers in SEC SIC 4412 and issuer fleet disclosures.
  https://www.sec.gov/Archives/edgar/data/1815779/000114036126037698/ny20082382x2_424b5.htm
  https://www.sec.gov/Archives/edgar/data/1649313/000110465926037215/bwlp-20251231x20f.htm
  https://www.sec.gov/Archives/edgar/data/1964954/000110465926005645/tm263617-2_424b5.htm
  https://www.sec.gov/Archives/edgar/data/1392326/000119312526342613/d104403dex99i.htm
- XLK software and IT: Vanguard Information Technology Index Fund above and
  https://www.sec.gov/Archives/edgar/data/2110/000141036826055049/NPORT_601_74464583_0326.htm
  https://www.sec.gov/Archives/edgar/data/1075065/000175272425100349/NPORT_B8Y1_64039678_0325.htm
  https://www.sec.gov/Archives/edgar/data/1552740/000094040026032719/659012FT063026.htm
  https://www.sec.gov/Archives/edgar/data/916620/000206657826003179/equity.htm
  https://www.sec.gov/Archives/edgar/data/1851112/000185111226000007/R9.htm
- XLRE equity REITs and property services: real estate filings above and
  https://www.sec.gov/Archives/edgar/data/899148/000091318126000330/fp0096642-1_nportex.htm
- XLC operators: https://www.sec.gov/Archives/edgar/data/320351/000032035126000237/filing11606.htm
  https://www.sec.gov/Archives/edgar/data/1064046/000094040026023116/GUR0850GH033126.htm
  https://www.sec.gov/Archives/edgar/data/2062440/000162828026059605/formf-32026.htm
  https://www.sec.gov/Archives/edgar/data/2020795/000162828026013196/R10.htm
- XLE energy infrastructure: https://www.sec.gov/Archives/edgar/data/2019061/000201906126000006/soboaif-12312025.htm
  https://www.sec.gov/Archives/edgar/data/2007855/000200785526000091/vgincq32026earningsrelease.htm
  https://www.sec.gov/Archives/edgar/data/1207179/000162828026021198/glng-20251231.htm
- XLY leisure: Vanguard Consumer Discretionary Index Fund above and
  https://www.sec.gov/Archives/edgar/data/1860434/000141036826099289/NPORT_GBB6_45217818_0726.htm
- XLV hospital operations: https://www.sec.gov/Archives/edgar/data/1479681/000162828026054268/R7.htm
- XLU gas distribution and XLP household products: Vanguard sector filings above.
- XLI additional issuer and industry evidence:
  https://www.sec.gov/Archives/edgar/data/1717393/000110465926098141/tm2623166d2_ex99-1.htm
  https://www.sec.gov/Archives/edgar/data/1709682/000170968226000046/ctos-20260930.htm
  https://www.sec.gov/Archives/edgar/data/2032966/000121390026060063/ea0290439-04.pdf
  https://www.sec.gov/Archives/edgar/data/1944285/000119312526323019/nasa.htm
  https://www.sec.gov/Archives/edgar/data/315754/000031575426000173/partf.htm
  https://www.sec.gov/Archives/edgar/data/1592900/000159290026004593/ck0001592900-20260731.htm
  https://www.sec.gov/Archives/edgar/data/230382/000094040026035002/BRFVOF0BR063026.htm
  https://www.sec.gov/Archives/edgar/data/1592900/000159290026002782/STXD03312026.htm
  https://www.sec.gov/Archives/edgar/data/1679049/000114036126017661/ny20066968x2_def14a.htm
  https://www.sec.gov/Archives/edgar/data/1341170/000117184324002343/esea20231231_20f.htm
- XLY cruises and powersports:
  https://www.sec.gov/Archives/edgar/data/1745201/000174520126000007/vik-20251231.htm
  https://www.sec.gov/Archives/edgar/data/1748797/000119312525129973/d945897dex992.htm
- XLC digital entertainment:
  https://www.sec.gov/Archives/edgar/data/1997859/000199785926000089/wbtn-20260630.htm
- XLK networking hardware and security:
  https://www.sec.gov/Archives/edgar/data/875186/000100371526000258/d38408d8k.htm
  https://www.sec.gov/Archives/edgar/data/1094366/000117891326004865/exhibit_99-1.htm
"""

REVIEWED_INDUSTRIES = {
    "Consumer Discretionary": {
        "Advertising",
        "Building Products",
        "Business Services",
        "Construction/Ag Equipment/Trucks",
        "Consumer Specialties",
        "Diversified Commercial Services",
        "Electronics Distribution",
        "Engineering & Construction",
        "General Bldg Contractors - Nonresidential Bldgs",
        "Industrial Machinery/Components",
        "Industrial Specialties",
        "Marine Transportation",
        "Metal Fabrications",
        "Miscellaneous manufacturing industries",
        "Movies/Entertainment",
        "Newspapers/Magazines",
        "Office Equipment/Supplies/Services",
        "Other Consumer Services",
        "Professional Services",
        "Publishing",
        "Telecommunications Equipment",
        "Tobacco",
        "Transportation Services",
    },
    "Consumer Staples": {
        "Consumer Electronics/Appliances",
    },
    "Energy": {
        "Electric Utilities: Central",
        "Electrical Products",
        "Industrial Machinery/Components",
        "Natural Gas Distribution",
    },
    "Finance": {
        "Real Estate",
    },
    "Health Care": {
        "Industrial Specialties",
    },
    "Industrials": {
        "Building Materials",
        "Building Products",
        "Electric Utilities: Central",
        "Farming/Seeds/Milling",
        "Other Specialty Stores",
        "Plastic Products",
        "Telecommunications Equipment",
        "Wholesale Distributors",
    },
    "Miscellaneous": {
        "Industrial Machinery/Components",
        "Multi-Sector Companies",
        "Office Equipment/Supplies/Services",
    },
    "Real Estate": {
        "Other Consumer Services",
        "Real Estate Investment Trusts",
    },
    "Technology": {
        "Computer Software: Prepackaged Software",
        "Consumer Electronics/Appliances",
        "EDP Services",
        "Electrical Products",
        "Industrial Machinery/Components",
        "Radio And Television Broadcasting And Communications Equipment",
    },
    "Telecommunications": {
        "Computer Communications Equipment",
        "Telecommunications Equipment",
    },
    "Utilities": {
        "Environmental Services",
        "Oil & Gas Production",
        "Oil/Gas Transmission",
        "Telecommunications Equipment",
    },
}

# Reviewed ticker and normalized public issuer name by research ETF.
ISSUERS_BY_PROXY = {
    "XLB": {
        "AMCR": "amcor",
        "ATR": "aptargroup",
        "EXP": "eagle materials",
        "MYE": "myers industries",
    },
    "XLC": {
        "AMC": "amc entertainment holdings",
        "ASTS": "ast spacemobile",
        "ATEX": "anterix",
        "CARG": "cargurus",
        "GSAT": "globalstar",
        "GTM": "zoominfo technologies",
        "IDT": "idt",
        "IMAX": "imax",
        "IRDM": "iridium communications",
        "LION": "lionsgate studios",
        "NWS": "news",
        "NWSA": "news",
        "NYT": "york times",
        "OMC": "omnicom group",
        "RBLX": "roblox",
        "RDDT": "reddit",
        "STGW": "stagwell",
        "TDS": "telephone and data systems",
        "YELP": "yelp",
        "ZD": "ziff davis",
    },
    "XLE": {
        "DINO": "hf sinclair",
        "EE": "excelerate energy",
        "INSW": "international seaways",
        "LNG": "cheniere energy",
        "LPG": "dorian lpg",
        "NEXT": "nextdecade",
        "OKE": "oneok",
        "TDW": "tidewater",
    },
    "XLF": {
        "AGNC": "agnc investment",
        "ARR": "armour residential",
        "CPAY": "corpay",
        "DFIN": "donnelley financial solutions",
        "DX": "dynex",
        "EFC": "ellington financial",
        "EVTC": "evertec",
        "FISV": "fiserv",
        "FLYW": "flywire",
        "FOUR": "shift4 payments",
        "GPN": "global payments",
        "LADR": "ladder",
        "MQ": "marqeta",
        "MSCI": "msci",
        "NATL": "ncr atleos",
        "NLY": "annaly management",
        "PAYO": "payoneer global",
        "PRG": "prog holdings",
        "RELY": "remitly global",
        "RITM": "rithm",
        "TOST": "toast",
        "WEX": "wex",
        "WU": "western union",
        "XYZ": "block",
    },
    "XLI": {
        "ABM": "abm industries",
        "AGX": "argan",
        "ALLE": "allegion",
        "AMPX": "amprius technologies",
        "AMSC": "american superconductor",
        "APG": "api group",
        "AWI": "armstrong world industries",
        "AYI": "acuity",
        "BE": "bloom energy",
        "BLBD": "blue bird",
        "BRC": "brady",
        "CTRI": "centuri holdings",
        "CW": "curtiss wright",
        "CWST": "casella waste systems",
        "DLX": "deluxe",
        "ENS": "enersys",
        "EPAC": "enerpac tool group",
        "ESE": "esco technologies",
        "FELE": "franklin electric",
        "FLNC": "fluence energy",
        "GFF": "griffon",
        "GXO": "gxo logistics",
        "HLMN": "hillman solutions",
        "HNI": "hni",
        "HUBB": "hubbell",
        "KEX": "kirby",
        "LGN": "legence",
        "LYFT": "lyft",
        "MATX": "matson",
        "MLKN": "millerknoll",
        "MRCY": "mercury systems",
        "MSA": "msa safety",
        "OTIS": "otis worldwide",
        "PBI": "pitney bowes",
        "PLUG": "plug power",
        "POWL": "powell industries",
        "REZI": "resideo technologies",
        "ROL": "rollins",
        "RUN": "sunrun",
        "RXO": "rxo",
        "SNA": "snap on",
        "SWK": "stanley black and decker",
        "TPC": "tutor perini",
        "UNF": "unifirst",
        "VICR": "vicor",
        "VSTS": "vestis",
        "VVX": "v2x",
        "WWD": "woodward",
        "XPO": "xpo",
    },
    "XLK": {
        "ACIW": "aci worldwide",
        "ACLS": "axcelis technologies",
        "ACMR": "acm research",
        "AEIS": "advanced energy industries",
        "AI": "c3 ai",
        "AKAM": "akamai technologies",
        "ALKT": "alkami technology",
        "ALRM": "alarm com holdings",
        "AMPL": "amplitude",
        "APLD": "applied digital",
        "APPF": "appfolio",
        "APPN": "appian",
        "APPS": "digital turbine",
        "ARLO": "arlo technologies",
        "ASAN": "asana",
        "ATEN": "a10 networks",
        "AUR": "aurora innovation",
        "AVPT": "avepoint",
        "BDC": "belden",
        "BHE": "benchmark electronics",
        "BILL": "bill holdings",
        "BL": "blackline",
        "BLKB": "blackbaud",
        "BOX": "box",
        "BSY": "bentley systems",
        "CALX": "calix",
        "CIEN": "ciena",
        "CRWV": "coreweave",
        "CTS": "cts",
        "CTSH": "cognizant technology solutions",
        "CVLT": "commvault systems",
        "CXM": "sprinklr",
        "DBD": "diebold nixdorf",
        "DBX": "dropbox",
        "DGII": "digi international",
        "DLB": "dolby laboratories",
        "DOCU": "docusign",
        "DT": "dynatrace",
        "DXC": "dxc technology",
        "ENTG": "entegris",
        "EXTR": "extreme networks",
        "FFIV": "f5",
        "FICO": "fair isaac",
        "FIG": "figma",
        "FIVN": "five9",
        "FLEX": "flex",
        "FN": "fabrinet",
        "FROG": "jfrog",
        "FRSH": "freshworks",
        "GDDY": "godaddy",
        "GTLB": "gitlab",
        "GWRE": "guidewire software",
        "HLIT": "harmonic",
        "HUBS": "hubspot",
        "IDCC": "interdigital",
        "INTA": "intapp",
        "IONQ": "ionq",
        "IOT": "samsara",
        "IT": "gartner",
        "JBL": "jabil",
        "KN": "knowles",
        "LFUS": "littelfuse",
        "LIF": "life360",
        "MANH": "manhattan associates",
        "MDB": "mongodb",
        "NCNO": "ncino",
        "NOVT": "novanta",
        "NSSC": "napco security technologies",
        "NTCT": "netscout systems",
        "NTNX": "nutanix",
        "NTSK": "netskope",
        "OKTA": "okta",
        "OLED": "universal display",
        "ONDS": "ondas",
        "PATH": "uipath",
        "PCOR": "procore technologies",
        "PD": "pagerduty",
        "PDFS": "pdf solutions",
        "PEGA": "pegasystems",
        "PI": "impinj",
        "PLXS": "plexus",
        "PRCH": "porch group",
        "PTC": "ptc",
        "QLYS": "qualys",
        "QUBT": "quantum computing",
        "RBRK": "rubrik",
        "RDVT": "red violet",
        "RGTI": "rigetti computing",
        "RNG": "ringcentral",
        "RPD": "rapid7",
        "S": "sentinelone",
        "SANM": "sanmina",
        "SOUN": "soundhound ai",
        "SPSC": "sps commerce",
        "TDC": "teradata",
        "TEAM": "atlassian",
        "TENB": "tenable holdings",
        "TTAN": "servicetitan",
        "TTMI": "ttm technologies",
        "TWLO": "twilio",
        "TYL": "tyler technologies",
        "U": "unity software",
        "VECO": "veeco instruments",
        "VERX": "vertex",
        "VIA": "via transportation",
        "VRNS": "varonis systems",
        "VRSN": "verisign",
        "VSAT": "viasat",
        "VSH": "vishay intertechnology",
        "VYX": "ncr voyix",
        "WDAY": "workday",
        "WK": "workiva",
        "YOU": "clear secure",
        "ZS": "zscaler",
    },
    "XLP": {
        "ANDE": "andersons",
        "CART": "maplebear",
        "CENT": "central garden and pet",
        "ENR": "energizer holdings",
        "ODC": "oil dri america",
        "SPB": "spectrum brands holdings",
        "TPB": "turning point brands",
    },
    "XLRE": {
        "ADC": "agree realty",
        "AHR": "american healthcare",
        "APLE": "apple hospitality",
        "ARE": "alexandria real estate equities",
        "BFS": "saul centers",
        "BNL": "broadstone net lease",
        "BRX": "brixmor property group",
        "BXP": "bxp",
        "CBL": "cbl and associates properties",
        "CTRE": "caretrust",
        "CUBE": "cubesmart",
        "CUZ": "cousins properties",
        "DEA": "easterly government properties",
        "DEI": "douglas emmett",
        "DOC": "healthpeak properties",
        "DRH": "diamondrock hospitality",
        "EGP": "eastgroup properties",
        "ELS": "equity lifestyle properties",
        "EPR": "epr properties",
        "EXR": "extra space storage",
        "GNL": "global net lease",
        "GTY": "getty realty",
        "HIW": "highwoods properties",
        "HST": "host hotels and resorts",
        "INVH": "invitation homes",
        "JAN": "janus living",
        "KRC": "kilroy realty",
        "LAMR": "lamar advertising",
        "LINE": "lineage",
        "LTC": "ltc properties",
        "MAA": "mid america apartment communities",
        "MAC": "macerich",
        "MRP": "millrose properties",
        "NHI": "national health investors",
        "NNN": "nnn",
        "NTST": "netstreit",
        "OHI": "omega healthcare investors",
        "OUT": "outfront media",
        "PECO": "phillips edison and",
        "REG": "regency centers",
        "REXR": "rexford industrial realty",
        "SBRA": "sabra health care",
        "SKT": "tanger",
        "SMA": "smartstop self storage",
        "STAG": "stag industrial",
        "SUI": "sun communities",
        "TRNO": "terreno realty",
        "UDR": "udr",
        "VICI": "vici properties",
    },
    "XLU": {
        "AES": "aes",
        "ATO": "atmos energy",
        "CPK": "chesapeake utilities",
        "MGEE": "mge energy",
        "NFG": "national fuel gas",
        "NWN": "northwest natural holding",
        "OGS": "one gas",
        "SR": "spire",
    },
    "XLV": {
        "ALGN": "align technology",
        "AMN": "amn healthcare services",
        "ASTH": "astrana health",
        "AZTA": "azenta",
        "CERT": "certara",
        "DOCS": "doximity",
        "ENOV": "enovis",
        "EW": "edwards lifesciences",
        "HNGE": "hinge health",
        "HQY": "healthequity",
        "VEEV": "veeva systems",
        "ZBH": "zimmer biomet holdings",
    },
    "XLY": {
        "ADT": "adt",
        "CCL": "carnival",
        "COUR": "coursera",
        "CRCT": "cricut",
        "CVSA": "covista",
        "DUOL": "duolingo",
        "ETSY": "etsy",
        "EXPE": "expedia group",
        "FTDR": "frontdoor",
        "GHC": "graham holdings",
        "GME": "gamestop",
        "GOLD": "gold com",
        "LAUR": "laureate education",
        "LOPE": "grand canyon education",
        "MBLY": "mobileye global",
        "NWL": "newell brands",
        "PII": "polaris",
        "POOL": "pool",
        "PRDO": "perdoceo education",
        "QS": "quantumscape",
        "SBET": "sharplink",
        "SCI": "service international",
        "SIG": "signet jewelers",
        "SONO": "sonos",
        "STRA": "strategic education",
        "UTI": "universal technical institute",
    },
}

REVIEWED_ISSUERS = {
    symbol: (name, etf)
    for etf, issuers in ISSUERS_BY_PROXY.items()
    for symbol, name in issuers.items()
}

# Additional reviewed issuers use a separate industry allowlist so the first
# batch cannot acquire a new match when a classification changes.
# Evidence is business or industry classification, independent of ETF holdings.
ADDITIONAL_REVIEWED_INDUSTRIES = {
    "Consumer Discretionary": {
        "Aerospace",
        "Business Services",
        "Consumer Specialties",
        "Diversified Commercial Services",
        "Durable Goods",
        "Electronic Components",
        "Industrial Machinery/Components",
        "Industrial Specialties",
        "Marine Transportation",
        "Other Consumer Services",
        "Professional Services",
        "Professional and commerical equipment",
        "Publishing",
        "Telecommunications Equipment",
        "Transportation Services",
    },
    "Energy": {
        "Natural Gas Distribution",
    },
    "Finance": {
        "Real Estate",
    },
    "Miscellaneous": {
        "Miscellaneous",
    },
    "Real Estate": {
        "Real Estate Investment Trusts",
    },
    "Technology": {
        "Computer Software: Prepackaged Software",
        "EDP Services",
        "Electrical Products",
        "Radio And Television Broadcasting And Communications Equipment",
    },
    "Telecommunications": {
        "Telecommunications Equipment",
    },
    "Utilities": {
        "Environmental Services",
        "Oil & Gas Production",
        "Oil/Gas Transmission",
    },
}

ADDITIONAL_REVIEWED_ISSUERS = {
    # XLI
    "AER": ("aercap holdings n v", "XLI"),
    "AIT": ("applied industrial technologies", "XLI"),
    "AMTM": ("amentum holdings", "XLI"),
    "BWLP": ("bw lpg", "XLI"),
    "CAAP": ("corporacion america airports sa", "XLI"),
    "CACI": ("caci international", "XLI"),
    "CCEC": ("clean energy carriers", "XLI"),
    "CMRE": ("costamare", "XLI"),
    "CNM": ("core and main", "XLI"),
    "CRAI": ("cra international", "XLI"),
    "CTOS": ("custom truck one source", "XLI"),
    "CXW": ("corecivic", "XLI"),
    "DAC": ("danaos", "XLI"),
    "DHT": ("dht holdings", "XLI"),
    "ECO": ("okeanis eco tankers", "XLI"),
    "EQPT": ("equipmentshare com", "XLI"),
    "EXPO": ("exponent", "XLI"),
    "FA": ("first advantage", "XLI"),
    "FCN": ("fti consulting", "XLI"),
    "FERG": ("ferguson enterprises", "XLI"),
    "FRO": ("frontline", "XLI"),
    "G": ("genpact", "XLI"),
    "GATX": ("gatx", "XLI"),
    "GFL": ("gfl environmental no", "XLI"),
    "GNK": ("genco shipping and trading marshall islands", "XLI"),
    "HAFN": ("hafnia", "XLI"),
    "HURN": ("huron consulting group", "XLI"),
    "ICFI": ("icf international", "XLI"),
    "KFRC": ("kforce", "XLI"),
    "KFY": ("korn ferry", "XLI"),
    "LDOS": ("leidos holdings", "XLI"),
    "MAN": ("manpowergroup", "XLI"),
    "MDA": ("mda space", "XLI"),
    "MGRC": ("mcgrath rentcorp", "XLI"),
    "MMS": ("maximus", "XLI"),
    "NAT": ("nordic american tankers", "XLI"),
    "NSP": ("insperity", "XLI"),
    "NVGS": ("navigator holdings marshall islands", "XLI"),
    "PSN": ("parsons", "XLI"),
    "RBA": ("rb global", "XLI"),
    "RHI": ("robert half", "XLI"),
    "SBLK": ("star bulk carriers", "XLI"),
    "SFL": ("sfl", "XLI"),
    "SITE": ("siteone landscape supply", "XLI"),
    "STNG": ("scorpio tankers", "XLI"),
    "SUNB": ("sunbelt rentals holdings", "XLI"),
    "TEN": ("tsakos energy navigation", "XLI"),
    "TGLS": ("tecnoglass holdings", "XLI"),
    "TIC": ("tic solutions", "XLI"),
    "TNET": ("trinet group", "XLI"),
    "TRMD": ("torm", "XLI"),
    "UPWK": ("upwork", "XLI"),
    "VRSK": ("verisk analytics", "XLI"),
    "WCC": ("wesco international", "XLI"),
    "WSO": ("watsco", "XLI"),
    # XLK
    "BB": ("blackberry", "XLK"),
    "CHKP": ("check point software technologies", "XLK"),
    "CLBT": ("cellebrite di", "XLK"),
    "CLS": ("celestica", "XLK"),
    "DOX": ("amdocs", "XLK"),
    "DSGX": ("descartes systems group", "XLK"),
    "ESTC": ("elastic n v", "XLK"),
    "EVCM": ("evercommerce", "XLK"),
    "GEN": ("gen digital", "XLK"),
    "GIB": ("cgi", "XLK"),
    "KARO": ("karooooo", "XLK"),
    "MNDY": ("monday com", "XLK"),
    "OTEX": ("open text", "XLK"),
    "PAYC": ("paycom software", "XLK"),
    "PCTY": ("paylocity holding", "XLK"),
    "PRGS": ("progress software de", "XLK"),
    "RDWR": ("radware", "XLK"),
    "RSKD": ("riskified", "XLK"),
    "SAIL": ("sailpoint", "XLK"),
    "SSNC": ("ss and c technologies holdings", "XLK"),
    "UI": ("ubiquiti", "XLK"),
    # XLRE
    "AMH": ("american homes rent beneficial interest", "XLRE"),
    "CCI": ("crown castle", "XLRE"),
    "CDP": ("copt defense properties beneficial interest", "XLRE"),
    "COMP": ("compass", "XLRE"),
    "CSGP": ("costar group", "XLRE"),
    "CWK": ("cushman and wakefield", "XLRE"),
    "FSV": ("firstservice", "XLRE"),
    "IRM": ("iron mountain delaware", "XLRE"),
    "JLL": ("jones lang lasalle", "XLRE"),
    "KIM": ("kimco realty hc", "XLRE"),
    "MMI": ("marcus and millichap", "XLRE"),
    "NMRK": ("newmark group", "XLRE"),
    "RYN": ("rayonier", "XLRE"),
    "SBAC": ("sba communications", "XLRE"),
    "UE": ("urban edge properties beneficial interest", "XLRE"),
    "WY": ("weyerhaeuser", "XLRE"),
    "Z": ("zillow group", "XLRE"),
    "ZG": ("zillow group", "XLRE"),
    # XLC
    "BCE": ("bce", "XLC"),
    "KYIV": ("kyivstar group", "XLC"),
    "TIGO": ("millicom international cellular s a", "XLC"),
    "TU": ("telus", "XLC"),
    "UNIT": ("uniti group", "XLC"),
    "WBTN": ("webtoon entertainment", "XLC"),
    # XLE
    "GLNG": ("golar lng", "XLE"),
    "SOBO": ("south bow", "XLE"),
    "VG": ("venture global", "XLE"),
    # XLY
    "DOO": ("brp", "XLY"),
    "MMYT": ("makemytrip", "XLY"),
    "VAC": ("marriott vacations worldwide", "XLY"),
    "VIK": ("viking holdings", "XLY"),
    # XLV
    "NUTX": ("nutex health", "XLV"),
    # XLU
    "SWX": ("southwest gas holdings de", "XLU"),
    # XLP
    "CENTA": ("central garden and pet nonvoting", "XLP"),
}


# Forgent Power Solutions 10-K: electrical distribution equipment (FPS).
# https://www.sec.gov/Archives/edgar/data/2080126/000208012626000035/fps-20260630.htm
# Forestar Group 10-K: residential lot development for homebuilders (FOR).
# https://www.sec.gov/Archives/edgar/data/1406587/000162828026074699/for-20260930.htm

# DLocal, PagSeguro Digital and StoneCo 20-Fs: payment and financial services.
# https://www.sec.gov/Archives/edgar/data/1846832/000207097926000113/dlo-20251231.htm
# https://www.sec.gov/Archives/edgar/data/1712807/000155485526001229/pags-20251231.htm
# https://www.sec.gov/Archives/edgar/data/1745431/000207097926000170/stne-20251231.htm

# Issuer names from public SEC holdings and issuer filings. The filings are linked above.
RESIDUAL_REVIEWED_ISSUERS = {
    # XLB
    "PPTA": ("Perpetua Resources Corp.", "NAS", "XLB"),
    # XLC
    "CNK": ("Cinemark Holdings Inc.", "NYS", "XLC"),
    # XLE
    "NESR": ("National Energy Services Reunited Corp.", "NAS", "XLE"),
    # XLF
    "AFRM": ("Affirm Holdings Inc.", "NAS", "XLF"),
    "APAM": ("Artisan Partners Asset Management Inc. Class A", "NYS", "XLF"),
    "ATLC": ("Atlanticus Holdings Corp.", "NAS", "XLF"),
    "BHF": ("Brighthouse Financial Inc.", "NAS", "XLF"),
    "BOW": ("Bowhead Specialty Holdings Inc.", "NYS", "XLF"),
    "BWIN": ("Baldwin Insurance Group Inc.", "NAS", "XLF"),
    "CHCO": ("City Holding Co.", "NAS", "XLF"),
    "CHYM": ("Chime Financial Inc. Class A", "NAS", "XLF"),
    "DLO": ("DLocal Limited", "NAS", "XLF"),
    "FIS": ("Fidelity National Information Services Inc.", "NYS", "XLF"),
    "GABC": ("German American Bancorp Inc.", "NAS", "XLF"),
    "GSHD": ("Goosehead Insurance Inc. Class A", "NAS", "XLF"),
    "HRTG": ("Heritage Insurance Holdings Inc.", "NYS", "XLF"),
    "LPLA": ("LPL Financial Holdings Inc.", "NAS", "XLF"),
    "MKTX": ("MarketAxess Holdings Inc.", "NAS", "XLF"),
    "NP": ("Neptune Insurance Holdings Inc. Class A", "NYS", "XLF"),
    "OMF": ("OneMain Holdings Inc.", "NYS", "XLF"),
    "PAGS": ("PagSeguro Digital Ltd.", "NYS", "XLF"),
    "PAY": ("Paymentus Holdings Inc. Class A", "NYS", "XLF"),
    "SKWD": ("Skyward Specialty Insurance Group Inc.", "NAS", "XLF"),
    "STNE": ("StoneCo Ltd.", "NAS", "XLF"),
    "UPST": ("Upstart Holdings Inc.", "NAS", "XLF"),
    "UWMC": ("UWM Holdings Corp.", "NYS", "XLF"),
    "WABC": ("Westamerica BanCorp", "NAS", "XLF"),
    "WAL": ("Western Alliance Bancorp", "NYS", "XLF"),
    # XLI
    "CDRE": ("Cadre Holdings Inc.", "NYS", "XLI"),
    "CHRW": ("CH Robinson Worldwide Inc.", "NAS", "XLI"),
    "CMPR": ("Cimpress plc", "NAS", "XLI"),
    "CNH": ("CNH Industrial NV", "NYS", "XLI"),
    "FPS": ("Forgent Power Solutions, Inc.", "NYS", "XLI"),
    "HAYW": ("Hayward Holdings Inc.", "NYS", "XLI"),
    "KNX": ("Knight-Swift Transportation Holdings Inc.", "NYS", "XLI"),
    "LECO": ("Lincoln Electric Holdings Inc.", "NAS", "XLI"),
    "LHX": ("L3Harris Technologies Inc.", "NYS", "XLI"),
    "LQDT": ("Liquidity Services Inc.", "NAS", "XLI"),
    "MYRG": ("MYR Group Inc.", "NAS", "XLI"),
    "PSIX": ("Power Solutions International Inc.", "NAS", "XLI"),
    "SSD": ("Simpson Manufacturing Co. Inc.", "NYS", "XLI"),
    "WAB": ("Westinghouse Air Brake Technologies Corp.", "NYS", "XLI"),
    # XLK
    "AGYS": ("Agilysys Inc.", "NAS", "XLK"),
    "CCC": ("CCC Intelligent Solutions Holdings Inc.", "NAS", "XLK"),
    "DOCN": ("DigitalOcean Holdings Inc.", "NYS", "XLK"),
    "EPAM": ("EPAM Systems Inc.", "NYS", "XLK"),
    "QTWO": ("Q2 Holdings Inc.", "NYS", "XLK"),
    "ZETA": ("Zeta Global Holdings Corp. Class A", "NYS", "XLK"),
    # XLP
    "LW": ("Lamb Weston Holdings Inc.", "NYS", "XLP"),
    # XLRE
    "ALX": ("Alexander’s, Inc.", "NYS", "XLRE"),
    "CURB": ("Curbline Properties Corp.", "NYS", "XLRE"),
    "EPRT": ("Essential Properties Realty Trust, Inc.", "NYS", "XLRE"),
    "IVT": ("InvenTrust Properties Corp.", "NYS", "XLRE"),
    "RHP": ("Ryman Hospitality Properties, Inc.", "NYS", "XLRE"),
    "SLG": ("SL Green Realty Corp.", "NYS", "XLRE"),
    "UMH": ("UMH Properties, Inc.", "NYS", "XLRE"),
    # XLV
    "ATEC": ("Alphatec Holdings Inc.", "NAS", "XLV"),
    "COO": ("Cooper Cos. Inc.", "NAS", "XLV"),
    "ESTA": ("Establishment Labs Holdings Inc.", "NAS", "XLV"),
    "GDRX": ("GoodRx Holdings Inc. Class A", "NAS", "XLV"),
    "GMED": ("Globus Medical Inc. Class A", "NYS", "XLV"),
    "HRMY": ("Harmony Biosciences Holdings Inc.", "NAS", "XLV"),
    "LMRI": ("Lumexa Imaging Holdings Inc.", "NAS", "XLV"),
    "MRVI": ("Maravai LifeSciences Holdings Inc. Class A", "NAS", "XLV"),
    "NAMS": ("Newamsterdam Pharma Co. NV", "NAS", "XLV"),
    "NHC": ("National HealthCare Corp.", "AMS", "XLV"),
    "USPH": ("US Physical Therapy Inc.", "NYS", "XLV"),
    "WAY": ("Waystar Holding Corp.", "NAS", "XLV"),
    "XERS": ("Xeris Biopharma Holdings Inc.", "NAS", "XLV"),
    "ZYME": ("Zymeworks Inc.", "NAS", "XLV"),
    # XLY
    "BWA": ("BorgWarner Inc.", "NYS", "XLY"),
    "DHI": ("DR Horton Inc.", "NYS", "XLY"),
    "FOR": ("Forestar Group Inc.", "NYS", "XLY"),
    "HZO": ("MarineMax Inc.", "NYS", "XLY"),
    "LIND": ("Lindblad Expeditions Holdings Inc.", "NAS", "XLY"),
    "LTH": ("Life Time Group Holdings Inc.", "NYS", "XLY"),
    "NCLH": ("Norwegian Cruise Line Holdings Ltd.", "NYS", "XLY"),
    "OLLI": ("Ollie's Bargain Outlet Holdings Inc.", "NAS", "XLY"),
    "PHM": ("PulteGroup Inc.", "NYS", "XLY"),
    "TOL": ("Toll Brothers Inc.", "NYS", "XLY"),
}

# Reviewed cash-stock aliases. ETF evidence is the corresponding SEC portfolio
# linked above. Individual listing evidence for the truncated GLPI label and
# the similarly named FBNC and FBP issuers:
# https://www.sec.gov/Archives/edgar/data/1575965/000157596526000072/glpi-20260930.htm
# https://www.sec.gov/Archives/edgar/data/811589/000081158926000051/fbnc-20251231.htm
# https://www.sec.gov/Archives/edgar/data/1057706/000105770626000007/fbp-20251231.htm
# Each entry binds the venue, ETF, and digest of the reviewed KIS/Nasdaq labels
# and native classification. Keep the privately supplied source rows out of Git.
REVIEWED_LISTING_ALIASES = {
    # XLE
    "NOG": ("NYS", "XLE", "4b0f67770dd26496aa9b2a18c0def6fb2eaecac6edc14f4c24de0d60283143ff"),
    "OVV": ("NYS", "XLE", "ed09851cde8e10232d45b638f01eb662867b89d9b082dd4e2fab71f755562503"),
    # XLF
    "AFG": ("NYS", "XLF", "3d343525ded9d1b54a6ce2a4f3c511793ea45363ba9ae15e81a590feb97b07a9"),
    "BHRB": ("NAS", "XLF", "8f79b947a614b199f9c65808904c5de893638b1a24b3652492eb0faecded39eb"),
    "CBU": ("NYS", "XLF", "40db9f13a9693352f2d2772b872946c778b2d806d76c35d822a7b0e52c442210"),
    "CCNE": ("NAS", "XLF", "844bb5f74bf279979c9bb62dcce44f73c2211de30007297bcb997149204d8827"),
    "COLB": ("NAS", "XLF", "04d5039bbbeeca00d55d7cc56a8d469fb27670b0dcd5f7fdc65b67777a0913d9"),
    "FBNC": ("NAS", "XLF", "0607f3650ef06756997611aaa46aa3c6fae99416956996ec0fa11e4293367692"),
    "FBP": ("NYS", "XLF", "1c251d4f8220418ad1215d7b8ed1358710be9cbd2aae4c48210a984e375404cb"),
    "FCF": ("NYS", "XLF", "b2c6f2fd8ea6f2770a91e9ad77dcab101236b38f3911131996f7d265f36589d3"),
    "FSUN": ("NAS", "XLF", "69b254bfc18a0a353ec4f1a31d88824897735fe78ec043b64521b03990d5185e"),
    "HASI": ("NYS", "XLF", "046d11fde3dcdfb84c63c6e1ff5fb90f5c237c3dab3948762e808cdcb3d078e7"),
    "INDB": ("NAS", "XLF", "7ba2667a9a241d75be0b19ea978fd90692ba5791422f089cbcce48adeb80d04e"),
    "JKHY": ("NAS", "XLF", "6ac4e8fdf9074b485c5cd3dcccae19ae1af2e0f2b1f985ddcc9c372dc5144e46"),
    "NBN": ("NAS", "XLF", "310c923814d48d887b39e221ed99c59704121e9de9e7f4557480cb35978ff0ca"),
    "ONB": ("NAS", "XLF", "275b3be3481bc3040d316e85ff6d2d4055575de146b05c397102d4cabbdca224"),
    "RLI": ("NYS", "XLF", "009707de09145feee5c523b9f4a7619123d9b96128fc8ae169e6b0825983d58a"),
    "SEIC": ("NAS", "XLF", "d12829e87200cc4ec4e03d9b6034a366fcd0be9271a26786ecce695ffd410e78"),
    "TBBK": ("NAS", "XLF", "12af5a7806e4ad375a2375897df7a98d237427300b7c9acd9b36171acd206bed"),
    "TROW": ("NAS", "XLF", "af317d73b52d3cf5ba6e9f1c8a566fadca01fd8feefa07d05735ad4d6d8f2ba7"),
    "UCB": ("NYS", "XLF", "8b445801a4a4581dd51ed6ea50dd901b6cf53a7daf01ea52e6d38a31b6ad1ff7"),
    "WRB": ("NYS", "XLF", "7e2d791cd6c93550264973cae9a90bed7cb3830562b2e9c5a4532c999143cc06"),
    # XLI
    "BCO": ("NYS", "XLI", "9a25c9300a5563e658a9bf6feb373f5fbce767d8533687bc178a1356329b9de7"),
    "EXPD": ("NYS", "XLI", "76581dfcf4d1be48b7b5a76972b07ca205ca1886d30ac3789b29c024923d64a0"),
    "ZWS": ("NYS", "XLI", "e6e03897efa0b76e9b446551bf18e6e579fcb640ff9cb551ab5d787e72f4c5f9"),
    # XLK
    "BBAI": ("NYS", "XLK", "aa69e408e403fcb25fc2147f4038e9d35b2530033c7a73f33049c61e54e0260f"),
    "DAKT": ("NAS", "XLK", "80fe472f6758cbd66f8b734671d2f951da8b76d5ed6c98f9ea60238c37dfb90f"),
    "HPQ": ("NYS", "XLK", "117ea17b0b865fec9c49344389683f7e63450aa6c0bca1b90737640cb813d771"),
    # XLP
    "SFM": ("NAS", "XLP", "4afa0f10f391ba7372d85466b44fe6bba216301b99dce140569edaacab0cea36"),
    "SJM": ("NYS", "XLP", "da2f1a6d4d408967d024fff7500f54f51fe795c777162b98bfef201950425b17"),
    # XLRE
    "CSR": ("NYS", "XLRE", "c196a0425ea9a5161f6b0f3a9c8a39887aa6ae0bb54c9f93570c42aea61f16fa"),
    "GLPI": ("NAS", "XLRE", "a3ce5017946ec72933830dfa0ac3c815338e7b8ea6567255a5a0e833841cef51"),
    "IIPR": ("NYS", "XLRE", "954c847b5cada3b5872c239c9572afc1e60e2adea44d129b77ea59b7973775e3"),
    "WPC": ("NYS", "XLRE", "232e9fceb81e94af19cb3f857a7748de62c9bb89840fd3689190b167993857d4"),
    # XLU
    "NJR": ("NYS", "XLU", "dd69ccdc2ebf132f74ca858981d0d295f123b93a6a9654f2682a0fe8bd7fb801"),
    # XLV
    "LGND": ("NAS", "XLV", "b27b287cd7b26c28d073a1b552ecd95d8ee50e0016c5cd9916318daadd2eccaf"),
    "STE": ("NYS", "XLV", "565f47f425fe1ca3362fddd99503a2ff0e395a0ae93c67037f1fca67dfeaee93"),
    # XLY
    "BFAM": ("NYS", "XLY", "6d827923c806c9a2590ed86424af5f3eb9bf2cf99e83529f5f9cce643cfcb7f1"),
    "DORM": ("NAS", "XLY", "70f830624ddf9bbf484e1a9b722f5378bafedd03edf8c335595f30ccc4d5898f"),
    "HRB": ("NYS", "XLY", "547f48c7d3a6dc35400ea92dad388f872eb79b211b7f67948429b3f2a6b2d6d8"),
    "M": ("NYS", "XLY", "aa73415842fc22de3a4e9260dd3fdee03f6b12c2c7498806cfc83bbab90a03e6"),
    "PRSU": ("NYS", "XLY", "214aad62cd4100f51a425e799860f17b853984ebe181587d4327241e1c91aa3b"),
    "SHOO": ("NAS", "XLY", "396803a2bf74dbc97e34c0cc5b06a33564a647b6e1c9f40762d5ab9bd248d82f"),

    # US listings reviewed against SEC filings and the existing ETF rules.
    # Each digest binds the exact source instrument and native classification.
    # https://www.sec.gov/Archives/edgar/data/1845097/000110465926024068/R1.htm
    "AMBP": ("NYS", "XLB", "2d9ae4cd2bbb95281ca396d03ecd61158dde167053a1d439fff09a34dcfb4e1e"),
    # https://www.sec.gov/Archives/edgar/data/2035989/000203598926000017/R1.htm
    "AMRZ": ("NYS", "XLB", "9e14644940de3218e119c6d48cfb1400f6b1980232712f8e0fc7188141e42166"),
    # https://www.sec.gov/Archives/edgar/data/1468642/000117184326002127/exh_21.htm
    "AUGO": ("NAS", "XLB", "afff23cc2debf9783df79a4a3958b6de1ec664d24aee8b3ef7814a73d70639dd"),
    # https://www.sec.gov/Archives/edgar/data/1429937/000142993726000010/exhibit991-63026.htm
    "BTG": ("AMS", "XLB", "6e981ea8f6b8413903a3fab631a0024f3fbacfe525b5bf72fb5ec808396003a3"),
    # https://www.sec.gov/edgar/browse/?CIK=1627223
    "CC": ("NYS", "XLB", "86bba99d82fbc185e29d6874213a22fcbfb164a92ce3496715c2e3b437b31520"),
    # https://www.sec.gov/Archives/edgar/data/1955520/000087666123000384/KNF050923.pdf
    "KNF": ("NYS", "XLB", "8244a92a3fe5965e60a05fe8056315244c92708782c5ee6561e772aae4c3eb6a"),
    # https://www.sec.gov/Archives/edgar/data/1489393/000148939326000061/lyb-20260630.htm
    "LYB": ("NYS", "XLB", "911470fa886bf6820cba1981ce2062ab2aa4c7c35ac188793fa38f6007c00a05"),
    # https://www.sec.gov/Archives/edgar/data/821130/000082113026000012/ad-20251231.htm
    "AD": ("NYS", "XLC", "b32d801c63ab5f65b78d7e5c874eec30403d1f140082e1300d1c98ef0321da0f"),
    # https://www.sec.gov/Archives/edgar/data/1514416/000151441626000017/band-20251231.htm
    "BAND": ("NAS", "XLC", "f3f2335232b77be74e4d06f2d6d0720151eb13d05d833ff0bc31d42ecaae85b6"),
    # https://www.sec.gov/Archives/edgar/data/1415404/000110465926121675/sats-20260930x10q.htm
    "ECHO": ("NAS", "XLC", "82c9a76b0fe925e2f43325f96622c4a5ede20a8cd96538911a718a2adaae782d"),
    # https://www.sec.gov/Archives/edgar/data/1538379/000162828026011838/ibta-20251231.htm
    "IBTA": ("NYS", "XLC", "c964e5a2834f6136e451bc69565b5f37f5710961d4e61ed36e1dca03b53aaea1"),
    # https://www.sec.gov/Archives/edgar/data/18926/000094787126000891/ss6865668_ex9901.htm
    "LUMN": ("NAS", "XLC", "8edeabbd080797cf7b7936ed9657d4cc46c967026b29c2c201ce8086d3c9b90e"),
    # https://www.sec.gov/Archives/edgar/data/107140/000162828026045111/jwa-20260430.htm
    "WLY": ("NYS", "XLC", "be0d5d2822a581e796e05f158363bc5bf5f40e41265266ecd831fb13ee971b7f"),
    # https://www.sec.gov/Archives/edgar/data/107140/000162828026045111/jwa-20260430.htm
    "WLYB": ("NYS", "XLC", "be0d5d2822a581e796e05f158363bc5bf5f40e41265266ecd831fb13ee971b7f"),
    # https://www.sec.gov/Archives/edgar/data/1509991/000150999126000049/kos-20260630.htm
    "KOS": ("NYS", "XLE", "401bc57daa3f2ce57b607a3aa4a4977de8b8bf8ba62c5e00c43d99c17e317329"),
    # https://www.sec.gov/Archives/edgar/data/1895262/000189526226000150/R1.htm
    "NE": ("NYS", "XLE", "6c1c0fd92ba0f6cbecb6851072860aec015887683cae88c2783df7698da8d378"),
    # https://www.sec.gov/Archives/edgar/data/1525221/000152522126000074/a2026bristowars-final.pdf
    "VTOL": ("NYS", "XLE", "90919c3ef80ce855a970f2599e9cde0c75a5925b50deac4ab79f5677dbda334e"),
    # https://www.sec.gov/Archives/edgar/data/1823529/000182352926000188/act-20260630.htm
    "ACT": ("NAS", "XLF", "d358287cc5007b4a6e4abba5a042938702366bd3bf8693a2e74996130e060d0f"),
    # https://www.sec.gov/Archives/edgar/data/2040491/000162828026060740/asic-20260904.htm
    "ASIC": ("NYS", "XLF", "e4faf5cdaf4ecea334587b62f48b0897afbc87639f3dab84fb1586b5e1e69a6e"),
    # https://www.sec.gov/Archives/edgar/data/1472787/000119312526314255/faf-20260630.htm
    "FAF": ("NYS", "XLF", "43b925a33bdb743924d0f4eb4e5df300ca92ac8e44a280bc63363e571327d2a4"),
    # https://www.sec.gov/Archives/edgar/data/910073/000091007326000068/fbc-20260630.htm
    "FLG": ("NYS", "XLF", "4ffab5394dcd9ab8cc75233be468179e27dd04d2c09d39987a26a06d1db0b2e2"),
    # https://www.sec.gov/Archives/edgar/data/1794338/000121390026046896/ea0287447-20fa1_inter.htm
    "IGIC": ("NAS", "XLF", "9d93e1c1c53ac83cba279a6bec7602f4df261124f60d8cfd7fd98bff594fbc49"),
    # https://www.sec.gov/Archives/edgar/data/34782/000003478226000055/source-20260930.htm
    "SRCE": ("NAS", "XLF", "f0dd3b4dcc83745f8e7864f9f8862f1ca9f39b215655547f14d161d147865518"),
    # https://www.sec.gov/Archives/edgar/data/740971/000110465925050070/tm2514521-1_prem14a.htm
    "TOWN": ("NAS", "XLF", "dfb3f08cdc212c1e672cb746acd567c14b687e7ce65fbb1936dbd3a00f632edf"),
    # https://www.sec.gov/Archives/edgar/data/2105139/000121390026084882/ea0300190-8k_adiglobal.htm
    "ADIG": ("NYS", "XLI", "8d09e8132c711b915ee6e6b890a56ba5e4cce673d1fbf6117e8a6ca2f1962169"),
    # https://www.sec.gov/Archives/edgar/data/1394832/000139483226000015/R1.htm
    "ATS": ("NYS", "XLI", "bcca15d449158adccd81458da4dde0b81c33ced64c7fb542115bd9bfcabe124b"),
    # https://www.sec.gov/Archives/edgar/data/1173382/000117338226000029/caelistingtransfertonasd.htm
    "CAE": ("NAS", "XLI", "3ebeaa1ffa878357b53c7fe96e3022fa16d8d8ef4f5c5491fc17fa350098eaec"),
    # https://www.sec.gov/Archives/edgar/data/1468522/000162828026011789/R1.htm
    "FER": ("NAS", "XLI", "48e05f68bf089c2e3ef0d7289499824a239262e4336f3bf7ebada58e111b386d"),
    # https://www.sec.gov/Archives/edgar/data/1474735/000143774926025669/gnrc20260630_10q.htm
    "GNRC": ("NYS", "XLI", "5ed96adfd307f2f01d2faf079e800e3224aa14275ca025443dab2bd674b25cdb"),
    # https://www.sec.gov/Archives/edgar/data/728535/000143774926024397/jbht20260630_10q.htm
    "JBHT": ("NAS", "XLI", "835c336850eae076d4f242b8400d3aeb0cef600f8a3ffeefa5a1606f678a9a44"),
    # https://www.sec.gov/Archives/edgar/data/1670076/000167007626000103/fron-20260930.htm
    "ULCC": ("NAS", "XLI", "8f7ad001bd7ba9bdbc05111e4e157c371538508678877c0ee16810f8898b08c3"),
    # https://www.sec.gov/Archives/edgar/data/1318220/000110465926117943/wcn-20260930x10q.htm
    "WCN": ("NYS", "XLI", "20927623e67c20aa442a253982989d6a125b04d461c876f9e46416b4fd10e7d1"),
    # https://www.sec.gov/Archives/edgar/data/1676238/000167623826000039/brz-20260908.htm
    "BRZE": ("NAS", "XLK", "419abfcfaf2a2d5b8c3df55314676a1bf8575623a706286fa3e1e369ff2e751d"),
    # https://www.sec.gov/Archives/edgar/data/890564/000089056426000037/asgn-20260331.htm
    "EFOR": ("NYS", "XLK", "817ba6e3305d56515a78b49a807df2b8878653ea517230fe5315f2f9a8a7fbd3"),
    # https://www.sec.gov/Archives/edgar/data/1517413/000151741326000345/fsly-20260930.htm
    "FSLY": ("NAS", "XLK", "b63dabf8e32e370b84aedad1855f5f125657cc985b26783871b6fc2b1a7e82b6"),
    # https://www.sec.gov/Archives/edgar/data/1557860/000162828026012910/R1.htm
    "GLOB": ("NYS", "XLK", "d9a82bccd9f9dd69bc28b13e144b46521e713edc7dba66ff5bf870779e332c34"),
    # https://www.sec.gov/Archives/edgar/data/1867072/000110465926067881/kd-20260331x10k.htm
    "KD": ("NYS", "XLK", "55741c99b16fcc103c9b42e0aab811c5e547eec6acd407579fc2ddf7286ccf2a"),
    # https://www.sec.gov/Archives/edgar/data/1032975/000103297526000053/logi-20260908.htm
    "LOGI": ("NAS", "XLK", "07b2f63faa869e226322d3774051701bdee4a163394704078a0c7c91cf2e075d"),
    # https://www.sec.gov/Archives/edgar/data/1823306/000182330626000025/R1.htm
    "LSPD": ("NYS", "XLK", "c2c8e1747f8e3ab1a7bd97e45505c1f507a2214f393dd9403cec77f8249581fb"),
    # https://www.sec.gov/Archives/edgar/data/1907982/000190798226000186/R1.htm
    "QBTS": ("NAS", "XLK", "5cc5b61e80c1a2e3fd04006bd84a2d8242d249507da9b36d2079d439e7ece504"),
    # https://www.sec.gov/Archives/edgar/data/1517228/000119312526448579/visn-20260930.htm
    "VISN": ("NAS", "XLK", "f2e37a5b66fe9306c1d60a4f044b2d588ee771d705618784ef5865d10b919c57"),
    # https://www.sec.gov/Archives/edgar/data/1996862/000162828026009842/R32.htm
    "BG": ("NYS", "XLP", "f503a6e11e098478bf63ccf9d15e64c9ec5042a1a04551cc1fb072ed0a607499"),
    # https://www.sec.gov/Archives/edgar/data/50493/000005049326000020/R1.htm
    "IMKTA": ("NAS", "XLP", "1abafe48ba953e99efde1a1c53d838983fb8931fe333fe20674eb986dae19596"),
    # https://www.sec.gov/Archives/edgar/data/2071668/000110465926029805/micc-20251231xex2d1.htm
    "MICC": ("NYS", "XLP", "3142ba959ad54e9341f9ea8a25357e42cf377cdb78e9b118cc579f7a9229e0db"),
    # https://www.sec.gov/Archives/edgar/data/88121/000008812126000054/seb-20260704x10q.htm
    "SEB": ("AMS", "XLP", "89cb38463e7ec5a5a70b4c4f67f3e2ec61f68254f9a08226145a6583a146ce65"),
    # https://www.sec.gov/Archives/edgar/data/913353/000117184326000984/cigi20251231_40f.htm
    "CIGI": ("NAS", "XLRE", "02f946c967e6ff930e83043ad9a028d9f9e11eac46483aed224ef9c3a7c55984"),
    # https://www.sec.gov/Archives/edgar/data/1541401/000154140126000008/esrt-20251231.htm
    "ESRT": ("NYS", "XLRE", "5410c4e970c2964347d2c3193d6bf1da722b4317a4f09f659299d8d287b4bd86"),
    # https://www.sec.gov/Archives/edgar/data/1561032/000156103226000075/hct-20260930.htm
    "NHP": ("NAS", "XLRE", "4d1424118defb91a92db9e73b33e685ed88f66809347dfd3c22c12dcd2028283"),
    # https://www.sec.gov/Archives/edgar/data/1511337/000151133726000029/rlj-20260930.htm
    "RLJ": ("NYS", "XLRE", "ad911c5799e5036161546af8754877f241f0ddbe368c7d3c2973088d48ffa5b1"),
    # https://www.sec.gov/Archives/edgar/data/1167379/000116737926000014/alc-20251231.htm
    "ALC": ("NYS", "XLV", "40c8a3cc2b0dc2acd9a5cb2f6c17d8d1d983d91527fb8592176b30953296b01f"),
    # https://www.sec.gov/Archives/edgar/data/1860742/000186074226000111/blco-20260930.htm
    "BLCO": ("NYS", "XLV", "d33f0337473af874ff108bae8adbc8e4a88ff58a1e6596b67419ff91bcdaeddf"),
    # https://www.sec.gov/Archives/edgar/data/1730430/000110465926119186/R1.htm
    "KNSA": ("NAS", "XLV", "fae3217dec352242574948a0f9e887710d04132fb209535e76ad2c390849cf7a"),
    # https://www.sec.gov/Archives/edgar/data/1830487/000183048726000013/phvs-20251231.htm
    "PHVS": ("NAS", "XLV", "3c209f61c54962aa03105226c8a853164a928cd3ac0e8def9148f0ade42e9a6e"),
    # https://www.sec.gov/Archives/edgar/data/1015820/000101582026000018/R1.htm
    "QGEN": ("NYS", "XLV", "b772bbd8eba9705848e06c3cc28c55f3f9f0083e153435459fe8782bf34d7eeb"),
    # https://www.sec.gov/Archives/edgar/data/2085187/000162828026071080/bobs-20260927.htm
    "BOBS": ("NYS", "XLY", "af80a958ac11591be527781ff3cf1739d24f2223dba57e133492b2cfc1d6a8be"),
    # https://www.sec.gov/Archives/edgar/data/1157408/000110465926117480/lrn-20260930x10q.htm
    "LRN": ("NYS", "XLY", "e8b136192858f961c6cffa5706242308b403d3afe94642ba183af23f7195b040"),
    # https://www.sec.gov/Archives/edgar/data/1618756/000161875626000056/R1.htm
    "QSR": ("NYS", "XLY", "7e9d92b39aa356d39bed8f49af1d2cc3b7d0ecdb8aabfcb06fc78f777dba5056"),
    # https://www.sec.gov/Archives/edgar/data/1877787/000187778726000015/zgn-20251231.htm
    "ZGN": ("NYS", "XLY", "05726d6377b1295369b7394b32374b45fc6b6ff0c2124260187be3b32bb50d37"),
}
