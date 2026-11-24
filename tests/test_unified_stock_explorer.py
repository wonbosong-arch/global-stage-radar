"""Read-only unified stocks: retained price charts, held identity, no promotion."""
import pandas as pd

from unified_stock_explorer import ResearchStockSnapshot, unified_stock_rows


def test_snapshot_reads_only_the_selected_symbol_and_isolates_returned_bars():
    prices = pd.DataFrame({
        "symbol": ["AAA", "BBB", "AAA"],
        "date": pd.to_datetime(["2026-11-20", "2026-11-19", "2026-11-18"]),
        "close": [102.0, 200.0, 100.0],
    }, index=[5, 12, 30])
    report = pd.DataFrame({"symbol": ["AAA", "BBB", "HOLD"],
                           "review_note": ["", "", "identity_conflict"]})
    snapshot = ResearchStockSnapshot(report, prices)

    selected = snapshot.daily_for("AAA")
    assert selected.close.tolist() == [100.0, 102.0]
    selected.loc[5, "close"] = 999.0
    copied_report, copied_prices = snapshot.copy_frames()
    copied_report.loc[0, "symbol"] = "OTHER"
    copied_prices.loc[5, "close"] = 888.0
    assert snapshot.daily_for("AAA").close.tolist() == [100.0, 102.0]
    assert snapshot.daily_for("HOLD").empty
    assert snapshot.chart_count == 2
    assert snapshot.identity_conflicts == ("HOLD",)
    assert snapshot.copy_frames()[0].symbol.tolist() == ["AAA", "BBB", "HOLD"]


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


def test_native_nasdaq_sector_is_browsable_without_approving_an_etf_or_stage():
    active = pd.DataFrame([{"symbol": "OPER", "sector": "Industrials", "stage_label": "Stage 1"}])
    report = pd.DataFrame([
        {"symbol": "SOFT", "proposed_sector": "", "native_sector": "Technology",
         "native_industry": "Computer Software: Prepackaged Software",
         "research_eligible": False, "provisional_stage_label": "Stage 2 후보",
         "suggested_sector_benchmark": "", "activation_status": "pending_review_not_activated"},
        {"symbol": "REIT", "proposed_sector": "", "native_sector": "Real Estate",
         "native_industry": "Real Estate Investment Trusts",
         "research_eligible": False, "provisional_stage_label": "Stage 2 후보",
         "suggested_sector_benchmark": "", "activation_status": "pending_review_not_activated"},
        {"symbol": "CURATED", "proposed_sector": "Information Technology",
         "native_sector": "Technology", "native_industry": "Semiconductors",
         "research_eligible": True, "provisional_stage_label": "Stage 2 후보",
         "suggested_sector_benchmark": "XLK", "activation_status": "pending_review_not_activated"},
        {"symbol": "UNJOINED", "proposed_sector": "", "native_sector": "Finance",
         "native_industry": "", "research_eligible": False,
         "provisional_stage_label": "연구 판정 보류",
         "suggested_sector_benchmark": "", "activation_status": "pending_review_not_activated"},
    ])
    prices = pd.DataFrame({"symbol": report.symbol})
    before_report = report.copy(deep=True)
    before_active = active.copy(deep=True)
    result, research = unified_stock_rows(active, report, prices)
    by_symbol = result.set_index("symbol")
    assert research == set(report.symbol)
    assert by_symbol.loc["SOFT", "sector"] == "Nasdaq · Technology"
    assert by_symbol.loc["REIT", "sector"] == "Nasdaq · Real Estate"
    assert by_symbol.loc["CURATED", "sector"] == "Information Technology"
    assert by_symbol.loc["UNJOINED", "sector"] == ""
    assert by_symbol.loc["SOFT", "stage_label"] == "연구 판정 보류"
    assert by_symbol.loc["REIT", "stage_label"] == "연구 판정 보류"
    assert by_symbol.loc["CURATED", "stage_label"] == "Stage 2 후보"
    assert by_symbol.loc["SOFT", "suggested_sector_benchmark"] == ""
    assert by_symbol.loc["SOFT", "activation_status"] == "pending_review_not_activated"
    assert by_symbol.loc["OPER", "sector"] == "Industrials"
    pd.testing.assert_frame_equal(report, before_report)
    pd.testing.assert_frame_equal(active, before_active)


def test_missing_native_fields_and_identity_held_prices_do_not_fabricate_groups():
    active = pd.DataFrame(columns=["symbol"])
    report = pd.DataFrame([
        {"symbol": "SAFE", "proposed_sector": "", "research_eligible": False,
         "provisional_stage_label": "연구 판정 보류"},
        {"symbol": "HELD", "proposed_sector": "", "research_eligible": False,
         "provisional_stage_label": "연구 판정 보류"},
    ])
    result, symbols = unified_stock_rows(active, report, pd.DataFrame({"symbol": ["SAFE"]}))
    assert symbols == {"SAFE"}
    assert list(result.symbol) == ["SAFE"]
    assert result.iloc[0].sector == ""

