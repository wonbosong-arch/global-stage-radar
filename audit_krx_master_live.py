"""Live audit of public KIS KRX master files; never changes the active universe."""
from __future__ import annotations

import json

from krx_master import download_krx_master


EXPECTED_SYMBOLS = {
    "KOSPI": {"005930", "005935", "069500", "091160"},
    "KOSDAQ": {"086520", "247540"},
}


def main() -> None:
    report = {}
    for market, expected in EXPECTED_SYMBOLS.items():
        frame = download_krx_master(market, timeout=30, max_bytes=25_000_000)
        frame["symbol"] = frame["symbol"].astype(str).str.zfill(6)
        missing = sorted(expected - set(frame["symbol"]))
        if missing:
            raise RuntimeError(f"{market} master missing expected symbols: {missing}")
        sample = frame[frame["symbol"].isin(expected)][
            ["symbol", "standard_code", "name_ko", "group_code", "preferred_share", "spac", "etp",
             "is_etp_candidate", "is_preferred_share", "is_spac_candidate",
             "instrument_class", "approval_status"]
        ].to_dict(orient="records")
        report[market] = {
            "row_count": int(len(frame)),
            "duplicate_symbol_count": int(frame["symbol"].duplicated().sum()),
            "instrument_class_counts": {
                str(k): int(v) for k, v in frame["instrument_class"].value_counts(dropna=False).items()
            },
            "raw_flag_value_counts": {
                column: {str(k): int(v) for k, v in frame[column].fillna("").astype(str).str.strip().value_counts().items()}
                for column in ["preferred_share", "spac", "etp"]
            },
            "sample_known_symbols": sample,
            "all_rows_require_manual_review": bool(
                frame["approval_status"].eq("manual_review_required").all()
            ),
        }
        if frame.empty or frame["symbol"].duplicated().any():
            raise RuntimeError(f"{market} master is empty or contains duplicate symbols")
        if not report[market]["all_rows_require_manual_review"]:
            raise RuntimeError(f"{market} contains a row that bypasses manual review")
    print("KIS KRX MASTER LIVE AUDIT")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
