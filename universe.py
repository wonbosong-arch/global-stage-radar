"""CSV universe loading and validation, kept independent of the Streamlit UI."""
import pandas as pd

UNIVERSE_COLS = {
    "symbol", "name", "market", "sector", "asset_type",
    "market_cap_usd", "market_benchmark", "sector_benchmark",
}


def read_universe(file):
    """Read and validate a universe CSV from a path or file-like object."""
    try:
        d = pd.read_csv(file, encoding="utf-8-sig")
    except UnicodeDecodeError:
        if hasattr(file, "seek"):
            file.seek(0)
        d = pd.read_csv(file, encoding="cp949", encoding_errors="replace")
    d.columns = [str(x).strip().lower() for x in d.columns]
    if d.empty:
        raise ValueError("종목 유니버스 CSV에 종목 데이터가 없습니다.")
    missing = UNIVERSE_COLS - set(d.columns)
    if missing:
        raise ValueError("필수 열 누락: " + ", ".join(sorted(missing)) + " / 실제 읽은 열: " + repr(d.columns.tolist()))

    d["symbol"] = d["symbol"].fillna("").astype(str).str.strip().str.upper()
    d["market_cap_usd"] = pd.to_numeric(d["market_cap_usd"], errors="coerce")
    if "exchange" not in d.columns:
        d["exchange"] = "NAS"
    d["exchange"] = d["exchange"].fillna("NAS").astype(str).str.strip().str.upper()
    d.loc[d["exchange"].eq(""), "exchange"] = "NAS"

    if d["symbol"].eq("").any() or d["symbol"].str.lower().eq("nan").any():
        raise ValueError("종목 유니버스에 비어 있는 symbol 값이 있습니다.")
    duplicates = d.loc[d["symbol"].duplicated(keep=False), "symbol"].drop_duplicates().tolist()
    if duplicates:
        raise ValueError("중복 symbol이 있습니다. 각 종목은 한 번만 입력하세요: " + ", ".join(duplicates[:20]))
    bad_exchanges = sorted(set(d["exchange"]) - {"NAS", "NYS", "AMS"})
    if bad_exchanges:
        raise ValueError("지원하지 않는 KIS 거래소 코드: " + ", ".join(bad_exchanges) + " (NAS/NYS/AMS 사용)")

    allowed_types = {"stock", "market_etf", "sector_etf", "commodity"}
    d["asset_type"] = d["asset_type"].fillna("").astype(str).str.strip().str.lower()
    if d["asset_type"].eq("").any():
        raise ValueError("asset_type 값이 비어 있는 종목이 있습니다. stock / market_etf / sector_etf / commodity 중 하나를 입력하세요.")
    bad_types = sorted(set(d["asset_type"]) - allowed_types)
    if bad_types:
        raise ValueError("지원하지 않는 asset_type: " + ", ".join(bad_types))

    for column in ["name", "market", "sector", "market_benchmark", "sector_benchmark"]:
        d[column] = d[column].fillna("").astype(str).str.strip()
    if d["name"].eq("").any():
        raise ValueError("name 값이 비어 있는 종목이 있습니다.")
    if (d["market_cap_usd"].dropna() < 0).any():
        raise ValueError("market_cap_usd는 음수일 수 없습니다.")
    return d
