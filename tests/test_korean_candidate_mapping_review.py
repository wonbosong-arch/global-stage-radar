from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data" / "stock_universe_candidates.csv"


def test_korean_candidate_sector_notes_are_review_only():
    candidates = pd.read_csv(CANDIDATES, dtype={"symbol": str}).fillna("")
    korean = candidates[candidates["market"].astype(str).str.strip().eq("South Korea")]

    # Discovery can append unclassified Korean stocks without changing the 29
    # reviewed proposals. Keep the reviewed set/status checks below fixed.
    assert len(korean) >= 29
    assert korean["activation_status"].eq("pending_review").all()
    assert korean["sector_benchmark"].astype(str).str.strip().eq("").all()

    proposed = korean[korean["proposed_sector"].astype(str).str.strip().ne("")]
    assert len(proposed) == 29
    assert proposed["mapping_status"].isin({"first_pass_review_required", "user_sector_confirmed_benchmark_review_required"}).all()
    assert proposed["mapping_note"].astype(str).str.strip().ne("").all()

    unmapped = korean[korean["proposed_sector"].astype(str).str.strip().eq("")]
    assert unmapped["mapping_status"].eq("sector_mapping_missing").all()
    assert unmapped["proposed_sector_benchmark"].astype(str).str.strip().eq("").all()


def test_new_unmapped_korean_discovery_keeps_review_contract(monkeypatch):
    candidates = pd.read_csv(CANDIDATES, dtype={"symbol": str}).fillna("")
    extra = {column: "" for column in candidates.columns}
    extra.update(symbol="999998", name="SYNTHETIC UNMAPPED KOREAN CANDIDATE",
                 market="South Korea", exchange="KRX", activation_status="pending_review",
                 mapping_status="sector_mapping_missing")
    combined = pd.concat([candidates, pd.DataFrame([extra])], ignore_index=True)
    monkeypatch.setattr(pd, "read_csv", lambda *args, **kwargs: combined.copy())
    test_korean_candidate_sector_notes_are_review_only()


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


