"""Read-only unified stocks: retained price charts, held identity, no promotion."""
import pandas as pd

from unified_stock_explorer import unified_stock_rows


def test_safe_research_charts_and_stage_status_without_activation():
    active = pd.DataFrame([{
        "symbol": "OPER", "name": "Operating", "market": "South Korea",
        "exchange": "KRX", "stage_label": "Stage 1", "asset_type_norm": "stock"}])
    report = pd.DataFrame([
        {"symbol": "ANAL", "name": "Analyzed", "exchange": "NYS",
         "research_eligible": True, "provisional_stage_label": "Stage 2 후보",
         "proposed_sector": "Tech", "ret26_pct": 12.0,
         "activation_status": "pending_review_not_activated", "review_note": ""},
        {"symbol": "HELD", "name": "Held", "exchange": "NAS",
         "research_eligible": False, "provisional_stage_label": "Stage 2 후보",
         "proposed_sector": "Tech", "review_note": "market_cap_below_1b_or_missing",
         "activation_status": "pending_review_not_activated"},
        {"symbol": "CFR", "name": "Conflicted", "exchange": "",
         "research_eligible": False, "provisional_stage_label": "연구 판정 보류",
         "proposed_sector": "", "review_note": "candidate_identity_conflict"},
    ])
    prices = pd.DataFrame([{"symbol": "ANAL"}, {"symbol": "HELD"}])
    combined, chart_symbols = unified_stock_rows(active, report, prices)
    assert list(combined.symbol) == ["OPER", "ANAL", "HELD"]
    assert chart_symbols == {"ANAL", "HELD"}
    assert combined.set_index("symbol").loc["ANAL", "stage_label"] == "Stage 2 후보"
    held = combined.set_index("symbol").loc["HELD"]
    assert held["stage_label"] == "연구 판정 보류"
    assert "market_cap" in held["review_note"]
    assert held["analysis_scope"] == "연구"
    assert held["activation_status"] == "pending_review_not_activated"
    assert list(active.symbol) == ["OPER"]


def test_same_symbol_and_duplicate_research_report_never_double_join():
    active = pd.DataFrame([{"symbol": "SPY", "exchange": "AMS", "stage_label": "Stage 1"}])
    report = pd.DataFrame([
        {"symbol": "SPY", "research_eligible": True, "proposed_sector": "ETF"},
        {"symbol": "DUPE", "research_eligible": True, "proposed_sector": "Finance"},
        {"symbol": "DUPE", "research_eligible": True, "proposed_sector": "Finance"},
        {"symbol": "GOOD", "research_eligible": True, "proposed_sector": "Health",
         "provisional_stage_label": "Stage 2A 관찰 후보"},
    ])
    prices = pd.DataFrame({"symbol": ["SPY", "DUPE", "GOOD"]})
    merged, source = unified_stock_rows(active, report, prices)
    assert list(merged.symbol) == ["SPY", "GOOD"]
    assert source == {"GOOD"}
    assert merged.iloc[0].analysis_scope == "운영"


def test_large_snapshot_is_not_truncated_to_a_display_page():
    count = 2335
    report = pd.DataFrame({
        "symbol": [f"TEST{x:04d}" for x in range(count)],
        "research_eligible": [x < 1410 for x in range(count)],
        "provisional_stage_label": ["Stage 2 후보"] * count,
        "proposed_sector": ["Tech"] * count,
        "review_note": [""] * count,
    })
    prices = pd.DataFrame({"symbol": report.symbol})
    operating = pd.DataFrame(columns=["symbol", "name", "market", "stage_label"])
    merged, source = unified_stock_rows(operating, report, prices)
    assert len(merged) == count and len(source) == count
    assert merged.stage_label.eq("연구 판정 보류").sum() == count - 1410
    assert set(merged.loc[merged.symbol.str.contains("TEST2334"), "symbol"]) == {"TEST2334"}
