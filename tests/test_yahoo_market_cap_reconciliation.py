import unittest

import pandas as pd

from yahoo_market_cap_reconciliation import build_reconciliation


def _candidate(symbol="AAPL", **overrides):
    row = {
        "symbol": symbol, "name": symbol, "instrument_type": "common_stock_candidate", "exchange": "NYS",
        "market_cap_usd_b_secondary": 100.0, "market_cap_asof": "2026-10-23",
        "market_cap_source_url": "https://example.com/candidate",
    }
    row.update(overrides)
    return row


def _yahoo(symbol="AAPL", **overrides):
    row = {
        "symbol": symbol, "market_cap_usd_b_secondary": 103.0,
        "market_cap_asof": "2026-10-23", "market_cap_asof_basis": "source_provided_market_cap_date",
        "fetched_at_utc": "2026-10-26T00:00:00+00:00",
        "source_url": "https://finance.yahoo.com/quote/AAPL/",
        "market_cap_currency": "USD", "observation_status": "observed_usd",
        "market_cap_status": "not_verified", "error": "",
    }
    row.update(overrides)
    return row


class YahooMarketCapReconciliationTests(unittest.TestCase):
    def test_close_values_are_triage_only(self):
        report = build_reconciliation(pd.DataFrame([_candidate()]), pd.DataFrame([_yahoo()]))
        self.assertEqual(report.loc[0, "comparison_status"], "close_values_manual_review")
        self.assertFalse(bool(report.loc[0, "market_cap_verified"]))
        self.assertFalse(bool(report.loc[0, "activation_allowed"]))

    def test_material_difference_is_prioritized(self):
        report = build_reconciliation(
            pd.DataFrame([_candidate()]),
            pd.DataFrame([_yahoo(market_cap_usd_b_secondary=125.0)]),
        )
        self.assertEqual(report.loc[0, "comparison_status"], "material_difference_review")

    def test_effective_date_mismatch_is_flagged(self):
        report = build_reconciliation(
            pd.DataFrame([_candidate()]),
            pd.DataFrame([_yahoo(market_cap_asof="2026-10-01")]),
        )
        self.assertEqual(report.loc[0, "comparison_status"], "effective_date_mismatch")

    def test_yahoo_fetch_time_is_not_treated_as_market_cap_effective_date(self):
        yahoo = _yahoo(market_cap_asof="", market_cap_asof_basis="not_provided_by_yahoo")
        report = build_reconciliation(pd.DataFrame([_candidate()]), pd.DataFrame([yahoo]))
        self.assertEqual(report.loc[0, "comparison_status"], "effective_date_mismatch")
        self.assertEqual(report.loc[0, "yahoo_cap_asof"], "")
        self.assertEqual(report.loc[0, "yahoo_fetched_at_utc"], "2026-10-26T00:00:00+00:00")
        self.assertFalse(bool(report.loc[0, "market_cap_verified"]))

    def test_single_source_does_not_become_verified(self):
        report = build_reconciliation(
            pd.DataFrame([_candidate()]),
            pd.DataFrame(columns=["symbol", "market_cap_usd_b_secondary", "market_cap_asof",
                                  "source_url", "market_cap_currency", "observation_status",
                                  "market_cap_status", "error"]),
        )
        self.assertEqual(report.loc[0, "comparison_status"], "single_source_only")
        self.assertFalse(bool(report.loc[0, "market_cap_verified"]))

    def test_adr_candidates_are_not_in_yahoo_common_stock_reconciliation(self):
        candidates = pd.DataFrame([_candidate(instrument_type="adr_candidate")])
        report = build_reconciliation(candidates, pd.DataFrame([_yahoo()]))
        self.assertTrue(report.empty)

    def test_unverified_equity_candidates_are_included_but_adr_evidence_is_excluded(self):
        candidates = pd.DataFrame([
            _candidate("UNV", instrument_type="equity_candidate_unverified"),
            _candidate("ADR", instrument_type="equity_candidate_unverified", discovery_dr_country_code="KR"),
            _candidate("RATIO", instrument_type="equity_candidate_unverified", depositary_ratio_status="verified"),
        ])
        yahoo = pd.DataFrame([
            _yahoo("UNV"),
            _yahoo("ADR"),
            _yahoo("RATIO"),
        ])
        report = build_reconciliation(candidates, yahoo)
        self.assertEqual(report["symbol"].tolist(), ["UNV"])
        self.assertFalse(bool(report.loc[0, "market_cap_verified"]))
        self.assertFalse(bool(report.loc[0, "activation_allowed"]))

    def test_krx_candidates_are_outside_initial_yahoo_us_scope(self):
        candidates = pd.DataFrame([_candidate(symbol="005930", exchange="KRX", market="South Korea")])
        report = build_reconciliation(candidates, pd.DataFrame([_yahoo(symbol="005930")]))
        self.assertTrue(report.empty)


if __name__ == "__main__":
    unittest.main()
