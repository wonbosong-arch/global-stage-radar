from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "stock_universe_candidates.csv"


def test_korean_candidate_sector_notes_are_review_only():
    candidates = pd.read_csv(CANDIDATES, dtype={"symbol": str}).fillna("")
    korean = candidates[candidates["market"].astype(str).str.strip().eq("South Korea")]

    assert len(korean) == 29
    assert korean["activation_status"].eq("pending_review").all()
    assert korean["sector_benchmark"].astype(str).str.strip().eq("").all()

    proposed = korean[korean["proposed_sector"].astype(str).str.strip().ne("")]
    assert len(proposed) == 26
    assert proposed["mapping_status"].eq("first_pass_review_required").all()
    assert proposed["mapping_note"].astype(str).str.strip().ne("").all()


def test_complex_korean_holding_companies_are_not_forced_into_sector_etfs():
    candidates = pd.read_csv(CANDIDATES, dtype={"symbol": str}).fillna("")
    korean = candidates[candidates["market"].astype(str).str.strip().eq("South Korea")]
    unresolved = korean[korean["symbol"].isin(["402340", "028260", "034730"])]

    assert set(unresolved["symbol"]) == {"402340", "028260", "034730"}
    assert unresolved["proposed_sector"].astype(str).str.strip().eq("").all()
    assert unresolved["proposed_sector_benchmark"].astype(str).str.strip().eq("").all()
    assert unresolved["mapping_status"].eq("first_pass_review_required").all()
    assert unresolved["mapping_note"].str.contains("단일 업종 ETF|적합한 벤치마크 근거").all()
    assert unresolved["activation_status"].eq("pending_review").all()
