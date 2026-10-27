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
    assert len(proposed) == 29
    assert proposed["mapping_status"].isin({"first_pass_review_required", "user_sector_confirmed_benchmark_review_required"}).all()
    assert proposed["mapping_note"].astype(str).str.strip().ne("").all()


def test_user_directed_korean_sector_classifications_are_recorded_but_not_approved():
    candidates = pd.read_csv(CANDIDATES, dtype={"symbol": str}).fillna("")
    expected = {
        "035420": ("Internet", ""),
        "402340": ("Semiconductors", "091160"),
        "028260": ("Holding Companies", ""),
        "034730": ("Holding Companies", ""),
        "138040": ("Financials", "140700"),
    }
    for symbol, (sector, benchmark) in expected.items():
        row = candidates.loc[candidates["symbol"].eq(symbol)].iloc[0]
        assert row["proposed_sector"] == sector
        assert row["proposed_sector_benchmark"] == benchmark
        assert row["mapping_status"] == "user_sector_confirmed_benchmark_review_required"
        assert row["sector_benchmark"] == ""
        assert row["activation_status"] == "pending_review"
        assert str(row["mapping_note"]).strip()


