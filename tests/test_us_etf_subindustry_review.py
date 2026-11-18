"""Specialist ETF candidates are evidence for review, never automatic replacements."""
import pandas as pd
import pytest

from us_etf_subindustry_review import ETF_CANDIDATES, find_etf_alternative


@pytest.mark.parametrize("native,industry,etf", [
    ("Technology", "Computer Software: Prepackaged Software", "IGV"),
    ("Health Care", "Biotechnology: Biological Products (No Diagnostic Substances)", "XBI"),
    ("Real Estate", "Real Estate Investment Trusts", "IYR"),
    ("Finance", "Major Banks", "KBE"),
    ("Finance", "Property-Casualty Insurers", "KIE"),
    ("Finance", "Life Insurance", "KIE"),
    ("Consumer Discretionary", "Air Freight/Delivery Services", "JETS"),
])
def test_issuer_sourced_candidate_catalog_keeps_current_etf(native, industry, etf):
    universe = pd.DataFrame([{"symbol": "XLK", "provider": "KIS",
                               "asset_type": "sector_etf", "active": "true"}])
    packet = {"native_classification_join_pass": True,
              "native_sector": native, "native_industry": industry}
    before = universe.copy(deep=True)
    out = find_etf_alternative(packet, "XLK", universe)
    assert out["preferred_sector_etf_review"] == etf
    assert out["preferred_etf_existing_benchmark_preserved"] == "XLK"
    assert out["preferred_etf_official_source"].startswith("https://")
    assert out["preferred_etf_approved"] is False
    assert "미검증" in out["preferred_etf_review_status"]
    assert out["preferred_etf_fit_note"]
    assert find_etf_alternative(packet, etf, universe) == {}
    assert ETF_CANDIDATES[(native, industry)][0] == etf
    pd.testing.assert_frame_equal(universe, before)


def test_ambiguous_or_nonmatching_native_classification_is_not_an_etf_signal():
    universe = pd.DataFrame(columns=["symbol", "provider", "asset_type", "active"])
    packet = {"native_classification_join_pass": False,
              "native_sector": "Technology",
              "native_industry": "Computer Software: Prepackaged Software"}
    assert find_etf_alternative(packet, "XLK", universe) == {}
    packet["native_classification_join_pass"] = True
    packet["native_industry"] = "EDP Services"  # includes non-software businesses
    assert find_etf_alternative(packet, "XLK", universe) == {}
    packet["native_sector"] = "Real Estate"
    packet["native_industry"] = "Other Consumer Services"
    assert find_etf_alternative(packet, "XLRE", universe) == {}


def test_kis_metadata_alone_does_not_approve_or_promote_a_new_etf():
    packet = {"native_classification_join_pass": True,
              "native_sector": "Technology",
              "native_industry": "Computer Software: Prepackaged Software"}
    for active, provider, kind in [
        ("true", "KIS", "sector_etf"),
        ("false", "KIS", "sector_etf"),
        ("true", "Yahoo", "sector_etf"),
        ("true", "KIS", "stock"),
    ]:
        universe = pd.DataFrame([{"symbol": "IGV", "provider": provider,
                                  "asset_type": kind, "active": active}])
        out = find_etf_alternative(packet, "XLK", universe)
        assert out["preferred_etf_approved"] is False
        assert out["preferred_etf_existing_benchmark_preserved"] == "XLK"
        if provider == "KIS" and active == "true" and kind == "sector_etf":
            assert "가격 이력 검토 필요" in out["preferred_etf_review_status"]
        else:
            assert "미검증" in out["preferred_etf_review_status"]
