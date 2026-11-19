"""Reviewed issuer-to-ETF fit decisions corroborated by public SEC filings.

Nasdaq provides the current classification. The public filings below corroborate
individual issuers in ambiguous Nasdaq industry groups. The mapped KIS sector
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
