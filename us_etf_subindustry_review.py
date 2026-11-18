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
