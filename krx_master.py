"""Parser for the public KIS KOSPI/KOSDAQ fixed-width security master files.

This module only classifies instrument metadata; it does not approve candidates for the
active Stage universe. Unknown or structurally invalid records must remain unapproved.
"""
from __future__ import annotations

from io import BytesIO, StringIO
from zipfile import BadZipFile, ZipFile

import pandas as pd


KIS_KRX_MASTER_URLS = {
    "KOSPI": "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip",
    "KOSDAQ": "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip",
}

# Field widths and names are from KIS's published sample parser.
_KOSPI_TAIL_WIDTH = 228
_KOSPI_WIDTHS = [
    2, 1, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 9, 5, 5, 1, 1, 1, 2, 1, 1,
    1, 2, 2, 2, 3, 1, 3, 12, 12, 8, 15, 21, 2, 7, 1, 1, 1, 1, 1,
    9, 9, 9, 5, 9, 8, 9, 3, 1, 1, 1,
]
_KOSPI_NAMES = [
    "group_code", "market_cap_size", "sector_large", "sector_mid", "sector_small",
    "manufacturing", "low_liquidity", "governance_index", "kospi200_sector",
    "kospi100", "kospi50", "krx", "etp", "elw_issuer", "krx100", "krx_auto",
    "krx_semiconductor", "krx_bio", "krx_bank", "spac", "krx_energy_chemicals",
    "krx_steel", "short_term_overheat", "krx_media_telecom", "krx_construction",
    "non1", "krx_securities", "krx_shipbuilding", "krx_insurance", "krx_transport",
    "sri", "base_price", "trade_unit", "after_hours_unit", "trading_halt",
    "delisting_trade", "managed_stock", "market_warning", "warning_notice",
    "unfaithful_disclosure", "backdoor_listing", "lock_type", "par_value_change",
    "capital_increase_type", "margin_ratio", "credit_available", "credit_period",
    "previous_volume", "par_value", "listing_date", "listed_shares", "capital",
    "fiscal_month", "ipo_price", "preferred_share", "short_selling_overheat",
    "abnormal_surge", "krx300", "kospi", "revenue", "operating_profit",
    "ordinary_profit", "net_income", "roe", "reference_month", "market_cap",
    "group_company_code", "credit_limit_exceeded", "collateral_loan_available",
    "stock_lending_available",
]
_KOSDAQ_TAIL_WIDTH = 222
_KOSDAQ_WIDTHS = [
    2, 1, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 9, 5, 5, 1, 1, 1, 2, 1, 1, 1, 2, 2, 2, 3, 1, 3,
    12, 12, 8, 15, 21, 2, 7, 1, 1, 1, 1, 9, 9, 9, 5, 9, 8, 9, 3, 1, 1, 1,
]
_KOSDAQ_NAMES = [
    "group_code", "market_cap_size", "sector_large", "sector_mid", "sector_small",
    "venture", "low_liquidity", "krx_stock", "etp", "krx100", "krx_auto",
    "krx_semiconductor", "krx_bio", "krx_bank", "spac", "krx_energy_chemicals",
    "krx_steel", "short_term_overheat", "krx_media_telecom", "krx_construction",
    "investment_caution", "krx_securities", "krx_shipbuilding", "krx_insurance",
    "krx_transport", "kosdaq150", "base_price", "trade_unit", "after_hours_unit",
    "trading_halt", "delisting_trade", "managed_stock", "market_warning",
    "warning_notice", "unfaithful_disclosure", "backdoor_listing", "lock_type",
    "par_value_change", "capital_increase_type", "margin_ratio", "credit_available",
    "credit_period", "previous_volume", "par_value", "listing_date", "listed_shares",
    "capital", "fiscal_month", "ipo_price", "preferred_share", "short_selling_overheat",
    "abnormal_surge", "krx300", "revenue", "operating_profit", "ordinary_profit",
    "net_income", "roe", "reference_month", "market_cap", "group_company_code",
    "credit_limit_exceeded", "collateral_loan_available", "stock_lending_available",
]


def _read_zip_payload(payload: bytes) -> bytes:
    """Return the sole file inside a KIS ZIP, rejecting ambiguous archives."""
    try:
        with ZipFile(BytesIO(payload)) as archive:
            members = [name for name in archive.namelist() if not name.endswith("/")]
            if len(members) != 1:
                raise ValueError(f"Expected one master file in ZIP; found {len(members)}.")
            return archive.read(members[0])
    except BadZipFile as exc:
        raise ValueError("KIS master response is not a valid ZIP archive.") from exc



def download_krx_master(
    market: str,
    session=None,
    timeout: float = 30.0,
    max_bytes: int = 25_000_000,
) -> pd.DataFrame:
    """Download and parse one official KIS KRX master ZIP.

    The caller may pass a requests-compatible session for testing. This helper
    only returns review metadata; it never updates or approves the active universe.
    """
    market = str(market).strip().upper()
    if market not in KIS_KRX_MASTER_URLS:
        raise ValueError("market must be KOSPI or KOSDAQ.")
    if timeout <= 0:
        raise ValueError("timeout must be positive.")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive.")
    if session is None:
        import requests
        session = requests.Session()

    response = session.get(KIS_KRX_MASTER_URLS[market], timeout=timeout)
    response.raise_for_status()
    payload = response.content
    if not isinstance(payload, bytes) or not payload:
        raise ValueError(f"KIS {market} master download returned an empty or invalid payload.")
    if len(payload) > max_bytes:
        raise ValueError(f"KIS {market} master download exceeded the {max_bytes}-byte safety limit.")
    if payload[:2] != b"PK":
        raise ValueError(f"KIS {market} master download was not a ZIP archive.")
    return parse_krx_master_bytes(payload, market)


def parse_krx_master_bytes(payload: bytes, market: str) -> pd.DataFrame:
    """Parse raw ZIP or uncompressed bytes from a KIS KRX master file.

    Codes are normalized to six-character strings. Group/type flags are preserved
    verbatim; inferred eligibility is intentionally conservative.
    """
    market = str(market).strip().upper()
    if market not in {"KOSPI", "KOSDAQ"}:
        raise ValueError("market must be KOSPI or KOSDAQ.")
    raw = _read_zip_payload(payload) if payload[:2] == b"PK" else payload
    tail_width = _KOSPI_TAIL_WIDTH if market == "KOSPI" else _KOSDAQ_TAIL_WIDTH
    widths = _KOSPI_WIDTHS if market == "KOSPI" else _KOSDAQ_WIDTHS
    names = _KOSPI_NAMES if market == "KOSPI" else _KOSDAQ_NAMES
    # KIS's published KOSPI sample reserves 228 bytes for the suffix although
    # its documented fixed-width fields total 227 bytes; the final byte is padding.
    if sum(widths) > tail_width or tail_width - sum(widths) > 1:
        raise RuntimeError(f"Internal KIS {market} schema width mismatch: {sum(widths)} vs {tail_width}")

    prefix_rows: list[dict[str, str]] = []
    suffix_rows: list[str] = []
    for raw_line in raw.splitlines():
        if not raw_line.strip():
            continue
        line = raw_line.rstrip(b"\r")
        if len(line) <= tail_width:
            raise ValueError(f"Invalid KIS {market} record length: {len(line)}")
        prefix = line[:-tail_width]
        suffix = line[-tail_width:]
        code = prefix[:9].decode("cp949").strip()
        standard_code = prefix[9:21].decode("cp949").strip()
        name = prefix[21:].decode("cp949").strip()
        if not code or not name:
            raise ValueError(f"KIS {market} record has a missing code or name.")
        prefix_rows.append({
            "symbol": code[-6:].zfill(6) if code.isdigit() else code,
            "standard_code": standard_code,
            "name_ko": name,
            "market": market,
        })
        suffix_rows.append(suffix.decode("ascii", errors="strict"))

    if not prefix_rows:
        raise ValueError(f"KIS {market} master file is empty.")
    if len({row["symbol"] for row in prefix_rows}) != len(prefix_rows):
        raise ValueError(f"KIS {market} master file contains duplicate short codes.")

    tail = pd.read_fwf(StringIO("\n".join(suffix_rows)), widths=widths, names=names, dtype=str)
    result = pd.concat([pd.DataFrame(prefix_rows).reset_index(drop=True), tail.reset_index(drop=True)], axis=1)
    result["group_code"] = result["group_code"].fillna("").astype(str).str.strip().str.upper()
    result["is_etp_candidate"] = result["group_code"].eq("EF")
    result["is_preferred_share"] = result["preferred_share"].fillna("").astype(str).str.strip().eq("Y")
    result["is_spac_candidate"] = result["spac"].fillna("").astype(str).str.strip().eq("Y")
    result["instrument_class"] = "unknown"
    result.loc[result["is_etp_candidate"], "instrument_class"] = "etp_candidate"
    result.loc[
        result["group_code"].eq("ST") & ~result["is_preferred_share"] & ~result["is_spac_candidate"],
        "instrument_class",
    ] = "stock_candidate"
    result["approval_status"] = "manual_review_required"
    return result
