"""Show already mapped US research stocks first without hiding retained charts."""
from pathlib import Path
import ast

import pandas as pd

from unified_stock_explorer import mapped_research_mask, mapped_stock_view, unified_stock_rows


def test_default_mapped_view_keeps_operating_and_excludes_unready_research():
    active = pd.DataFrame([
        {"symbol": "OPER", "stage_label": "Stage 2 후보", "sector": "Industrials",
         "sector_benchmark": "XLI", "asset_type_norm": "stock"},
    ])
    research = pd.DataFrame([
        {"symbol": "READY", "research_eligible": True, "provisional_stage_label": "Stage 2 후보",
         "proposed_sector": "Health Care", "suggested_sector_benchmark": "XLV",
         "sector_rs_26w_pct": 5.0, "market_rs_26w_pct": 3.0, "weekly_bars": 83},
        {"symbol": "NOBENCH", "research_eligible": True, "provisional_stage_label": "Stage 2 후보",
         "proposed_sector": "Health Care", "suggested_sector_benchmark": "",
         "sector_rs_26w_pct": 2.0},
        {"symbol": "NORSS", "research_eligible": True, "provisional_stage_label": "Stage 2 후보",
         "proposed_sector": "Health Care", "suggested_sector_benchmark": "XLV",
         "sector_rs_26w_pct": float("nan")},
        {"symbol": "HELD", "research_eligible": False, "provisional_stage_label": "Stage 2 후보",
         "proposed_sector": "Health Care", "suggested_sector_benchmark": "XLV",
         "sector_rs_26w_pct": 6.0},
    ])
    prices = pd.DataFrame({"symbol": research.symbol})
    active_before, research_before = active.copy(deep=True), research.copy(deep=True)
    all_rows, chart_symbols = unified_stock_rows(active, research, prices)
    mapped = mapped_stock_view(all_rows)

    assert len(chart_symbols) == 4
    assert set(all_rows.symbol) == {"OPER", "READY", "NOBENCH", "NORSS", "HELD"}
    assert set(mapped.symbol) == {"OPER", "READY"}
    assert mapped_research_mask(all_rows).sum() == 1
    assert mapped.set_index("symbol").loc["READY", "stage_label"] == "Stage 2 후보"
    pd.testing.assert_frame_equal(active, active_before)
    pd.testing.assert_frame_equal(research, research_before)


def test_mapped_scope_does_not_truncate_prices_or_promote_research_to_operations():
    count = 2335
    nready = 1410
    report = pd.DataFrame({
        "symbol": [f"T{x:04d}" for x in range(count)],
        "research_eligible": [x < nready for x in range(count)],
        "provisional_stage_label": ["Stage 2 후보"] * count,
        "proposed_sector": ["Information Technology"] * count,
        "suggested_sector_benchmark": ["XLK"] * count,
        "sector_rs_26w_pct": [1.25] * count,
        "activation_status": ["pending_review_not_activated"] * count,
    })
    prices = pd.DataFrame({"symbol": report.symbol})
    all_rows, chart_symbols = unified_stock_rows(pd.DataFrame(columns=["symbol"]), report, prices)
    ready = mapped_stock_view(all_rows)

    assert len(all_rows) == count
    assert len(chart_symbols) == count
    assert len(ready) == nready
    assert set(ready.symbol).issubset(chart_symbols)
    assert ready.activation_status.eq("pending_review_not_activated").all()
    assert all_rows.activation_status.eq("pending_review_not_activated").all()


def test_missing_columns_fail_closed_for_research_and_preserve_operating():
    rows = pd.DataFrame([
        {"symbol": "OPER", "analysis_scope": "운영"},
        {"symbol": "UNKNOWN", "analysis_scope": "연구"},
    ])
    assert list(mapped_stock_view(rows).symbol) == ["OPER"]
    assert mapped_research_mask(pd.DataFrame()).empty


def test_stock_tab_defaults_to_mapped_and_shows_approved_vs_research_separation():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    area = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "render_asset_area")
    drilldown = next(n for n in tree.body
                     if isinstance(n, ast.FunctionDef) and n.name == "render_asset_drilldown")
    area_code = ast.get_source_segment(source, area)
    drilldown_code = ast.get_source_segment(source, drilldown)
    assert '"US_MAPPED_RESEARCH"' in area_code
    assert '"미국 · 매핑 완료"' in area_code
    assert '"미국 · 전체 가격 차트"' in area_code
    assert "mapped_stock_view(subset)" in area_code
    assert "mapped_research_mask(subset)" in area_code
    assert "연구 Stage는 운영 승인·매수 신호가 아닙니다" in area_code
    assert "ETF 대비 26주 RS" in drilldown_code
    assert "연구용 미승인" in drilldown_code
