"""Research-only US subindustry ETF alternatives to the existing broad ETFs.

These are *fund candidates*, not approved or KIS-price-validated benchmarks.
Nasdaq Sector/Industry is only a discovery clue, not proof that every member
belongs to the fund's investment universe. Never assign Stage, update the
operational monitoring CSV, replace a stored ETF, or activate a candidate.
"""
from __future__ import annotations

# Exact native classification -> (ETF, fund issuer's product page, fit caveat).
# Fund issuer evidence supports the ETF's mandate, not individual stock fit.
ETF_CANDIDATES = {
    ("Technology", "Computer Software: Prepackaged Software"): (
        "IGV", "https://www.ishares.com/us/products/239771/ishares-north-american-techsoftware-etf",
        "Software includes fintech, gaming and other mixed business models; issuer fit review required."),
    ("Health Care", "Biotechnology: Biological Products (No Diagnostic Substances)"): (
        "XBI", "https://www.ssga.com/us/en/institutional/etfs/state-street-spdr-sp-biotech-etf-xbi",
        "Biotech-focused index, not a benchmark for all pharmaceutical or CRO businesses."),
    ("Real Estate", "Real Estate Investment Trusts"): (
        "IYR", "https://www.ishares.com/us/products/239520/IYR",
        "Mortgage REITs and non-US REITs may not fit the US equity real-estate index."),
    ("Finance", "Major Banks"): (
        "KBE", "https://www.ssga.com/us/en/institutional/etfs/state-street-spdr-sp-bank-etf-kbe",
        "US bank index; foreign issuers and different bank business models need fit review."),
    ("Finance", "Property-Casualty Insurers"): (
        "KIE", "https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-insurance-etf-kie",
        "US insurance index; verify primary insurance business and issuer geography."),
    ("Finance", "Life Insurance"): (
        "KIE", "https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-insurance-etf-kie",
        "US insurance index; foreign issuers and diversified business models need review."),
    ("Consumer Discretionary", "Air Freight/Delivery Services"): (
        "JETS", "https://usglobaletfs.com/fund/u-s-global-jets-etf/",
        "Only airline-related companies fit; the Nasdaq industry also includes cargo providers."),
}


def find_etf_alternative(packet: dict, current_benchmark: str, universe) -> dict:
    """Return a visible *unapproved* alternative without changing current mapping.

    A unique ticker, KIS security identity, normalized issuer and native
    classification must already have passed the existing Nasdaq join. An ETF
    absent from the active universe is a discovery item, never a valid price
    series or a Stage input. Even an active ETF still needs issuer fit approval.
    """
    if not packet.get("native_classification_join_pass"):
        return {}
    pair = (str(packet.get("native_sector") or "").strip(),
            str(packet.get("native_industry") or "").strip())
    entry = ETF_CANDIDATES.get(pair)
    if entry is None:
        return {}
    ticker, issuer_url, fit_note = entry
    if ticker == str(current_benchmark or "").strip():
        return {}
    etf = universe[universe.symbol.eq(ticker)] if "symbol" in universe else universe.iloc[:0]
    kis_metadata = (
        len(etf) == 1
        and str(etf.iloc[0].get("provider", "")) == "KIS"
        and str(etf.iloc[0].get("asset_type", "")) == "sector_etf"
        and str(etf.iloc[0].get("active", "")).lower() == "true"
    )
    return {
        "preferred_sector_etf_review": ticker,
        "preferred_etf_official_source": issuer_url,
        "preferred_etf_fit_note": fit_note,
        "preferred_etf_review_status": (
            "기존 KIS ETF 등록 확인 · 종목 적합성 및 가격 이력 검토 필요"
            if kis_metadata else "신규 ETF 후보 · KIS 상품 식별·가격 이력·종목 적합성 미검증"),
        "preferred_etf_existing_benchmark_preserved": str(current_benchmark or ""),
        "preferred_etf_approved": False,
    }


# Individually reviewed matches between the 2026-11-18 issuer holdings and
# the identity-checked Nasdaq classifications. These lists select core
# businesses and do not copy the funds' full holdings.
VERIFIED_SPECIALIST_STOCKS = {
    "IGV": (
        "NOW MSFT CRWD INTU DDOG CDNS SNPS ADSK TEAM TTWO RBRK PTC NTNX DT U DOCU TYL GWRE GEN "
        "MANH HUBS BSY ESTC PCOR GTLB S ZETA DBX DSGX TTAN QLYS APPF PATH CVLT BOX VRNS "
        "ACIW TENB BB BRZE BILL WK CCC QTWO FRSH APPN INTA AVPT SPSC TDC ALRM ASAN BLKB "
        "NCNO VERX BL AI PRGS SOUN ALKT CXM LSPD PD ZM PANW FTNT WDAY ZS IOT RNG OTEX PEGA AGYS FIVN"
    ),
    "IHI": (
        "MDT LIVN ITGR TMDX AXGN CNMD CBLL ISRG EW STE ZBH ENOV GEHC BFLY SYK BSX BDX RMD DXCM "
        "BAX PEN GMED GKOS PODD TFX IRTC NVST PLSE ATRC INSP LMAT KMTS ATEC NVCR TNDM AORT PRCT IRMD BBNX"
    ),
    "XHB": "DHI PHM LEN NVR TOL SKY MTH CVCO MHO KBH GRBK CCS",
    "XRT": (
        "ORLY AZO AAP HZO CHWY RVLV ROST GAP URBN VSXY ANF BOOT AEO BKE BBY SIG WMT TGT DG "
        "DLTR BURL FIVE M PSMT OLLI KSS GME KR ACI SFM WMK IMKTA GO WRBY EYE ULTA DKS BBWI "
        "ASO SBH SVV REAL WINA TSCO CVNA PAG MUSA KMX LAD AN ABG GPI SAH"
    ),
    "XOP": "FANG EOG OXY DVN EQT EXE PR OVV APA RRC AR SM CHRD MTDR MGY MUR CNX CRC CRGY CRK TALO NOG GPOR BKV KOS REPX",
}
VERIFIED_SPECIALIST_BY_SYMBOL = {
    symbol: etf for etf, symbols in VERIFIED_SPECIALIST_STOCKS.items() for symbol in symbols.split()
}


def verified_specialist_etf(packet, *, market_cap_usd, has_price):
    if (packet.get("native_classification_join_pass") and has_price
            and market_cap_usd >= 1e9):
        return VERIFIED_SPECIALIST_BY_SYMBOL.get(packet.get("symbol"), "")
    return ""
