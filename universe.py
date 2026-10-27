"""CSV universe loading and validation, kept independent of the Streamlit UI."""
import pandas as pd

UNIVERSE_COLS = {
    "symbol", "name", "market", "sector", "asset_type",
    "market_cap_usd", "market_benchmark", "sector_benchmark",
}


def read_universe(file):
    """Read and validate a universe CSV from a path or file-like object."""
    try:
        d = pd.read_csv(file, encoding="utf-8-sig", dtype={"symbol": "string"})
    except UnicodeDecodeError:
        if hasattr(file, "seek"):
            file.seek(0)
        d = pd.read_csv(file, encoding="cp949", encoding_errors="replace", dtype={"symbol": "string"})
    d.columns = [str(x).strip().lower() for x in d.columns]
    if d.empty:
        raise ValueError("종목 유니버스 CSV에 종목 데이터가 없습니다.")
    missing = UNIVERSE_COLS - set(d.columns)
    if missing:
        raise ValueError("필수 열 누락: " + ", ".join(sorted(missing)) + " / 실제 읽은 열: " + repr(d.columns.tolist()))

    d["symbol"] = d["symbol"].fillna("").astype(str).str.strip().str.upper()
    raw_cap = d["market_cap_usd"]
    parsed_cap = pd.to_numeric(raw_cap, errors="coerce")
    invalid_cap = raw_cap.notna() & raw_cap.astype(str).str.strip().ne("") & parsed_cap.isna()
    if invalid_cap.any():
        raise ValueError("market_cap_usd에 숫자가 아닌 값이 있습니다.")
    d["market_cap_usd"] = parsed_cap
    def default_exchange(market):
        normalized = str(market).strip().lower()
        if normalized in {"crypto", "cryptocurrency", "암호자산"}:
            return "CRYPTO"
        if normalized in {"south korea", "korea", "republic of korea", "대한민국", "한국"}:
            return "KRX"
        return "NAS"

    if "exchange" not in d.columns:
        d["exchange"] = d["market"].map(default_exchange)
    d["exchange"] = d["exchange"].fillna("").astype(str).str.strip().str.upper()
    for index in d.index[d["exchange"].eq("")]:
        d.loc[index, "exchange"] = default_exchange(d.loc[index, "market"])

    if d["symbol"].eq("").any() or d["symbol"].str.lower().eq("nan").any():
        raise ValueError("종목 유니버스에 비어 있는 symbol 값이 있습니다.")
    duplicates = d.loc[d["symbol"].duplicated(keep=False), "symbol"].drop_duplicates().tolist()
    if duplicates:
        raise ValueError("중복 symbol이 있습니다. 각 종목은 한 번만 입력하세요: " + ", ".join(duplicates[:20]))
    bad_exchanges = sorted(set(d["exchange"]) - {"NAS", "NYS", "AMS", "TSE", "HKS", "SHS", "SZS", "HSX", "HNX", "KRX", "CRYPTO"})
    if bad_exchanges:
        raise ValueError("알 수 없는 거래소 코드: " + ", ".join(bad_exchanges) + " (허용 코드: NAS/NYS/AMS, TSE, HKS, SHS, SZS, HSX, HNX, KRX, CRYPTO). CRYPTO는 별도 암호자산 제공자를 사용하며, TSE/SHS/SZS 등은 해당 시장·자산 유형 조합에서만 조회됩니다.")

    allowed_types = {"stock", "market_etf", "sector_etf", "commodity_etf", "commodity", "crypto_asset"}
    d["asset_type"] = d["asset_type"].fillna("").astype(str).str.strip().str.lower()
    if d["asset_type"].eq("").any():
        raise ValueError("asset_type 값이 비어 있는 종목이 있습니다. stock / market_etf / sector_etf / commodity_etf / commodity / crypto_asset 중 하나를 입력하세요.")
    bad_types = sorted(set(d["asset_type"]) - allowed_types)
    if bad_types:
        raise ValueError("지원하지 않는 asset_type: " + ", ".join(bad_types))

    for column in ["name", "market", "sector", "market_benchmark", "sector_benchmark"]:
        d[column] = d[column].fillna("").astype(str).str.strip()
    if d["name"].eq("").any():
        raise ValueError("name 값이 비어 있는 종목이 있습니다.")
    needs_market_benchmark = ~d["asset_type"].eq("market_etf")
    if (needs_market_benchmark & d["market_benchmark"].eq("")).any():
        raise ValueError("시장 벤치마크가 비어 있는 자산이 있습니다.")
    needs_sector_benchmark = d["asset_type"].eq("stock")
    if (needs_sector_benchmark & d["sector_benchmark"].eq("")).any():
        raise ValueError("주식의 업종 벤치마크가 비어 있습니다.")
    if (d["market_cap_usd"].dropna() < 0).any():
        raise ValueError("market_cap_usd는 음수일 수 없습니다.")
    return d
