"""Cross-file audit of the 30 mainland China ETF review candidates.

Run: python -m unittest tests.test_china_sector_review_audit
No API calls; no activation changes.
"""
import csv
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def records(path):
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def mainland():
    return [r for r in records("data/monitoring_universe.csv")
            if r["country"] == "China" and r["exchange"] == "SHS"]


def review_rows():
    return [r for r in records("data/country_sector_proxy_candidates.csv")
            if r["country"] == "China" and
            "Shanghai Stock Exchange" in r["listing_market"]]


class MainlandChinaAuditTest(unittest.TestCase):
    def test_mainland_symbols_are_unique_and_inactive(self):
        rows = mainland()
        self.assertEqual(30, len(rows))
        self.assertEqual(30, len({r["symbol"] for r in rows}))
        self.assertTrue(all(r["active"].lower() == "false" for r in rows))

    def test_registered_review_symbols_belong_to_universe(self):
        symbols = {r["symbol"] for r in mainland()}
        registered = review_rows()
        self.assertEqual(len(registered), len({r["symbol"] for r in registered}))
        self.assertFalse({r["symbol"] for r in registered} - symbols)

    def test_all_mainland_candidates_have_market_benchmark(self):
        for row in mainland():
            with self.subTest(symbol=row["symbol"]):
                self.assertEqual("MCHI", row["market_benchmark"])
                self.assertEqual("ETF", row["instrument_type"])

    def test_review_metadata_is_explicitly_non_activating(self):
        for row in review_rows():
            with self.subTest(symbol=row["symbol"]):
                self.assertEqual(
                    "provider_price_history_confirmed_activation_pending",
                    row["dashboard_status"],
                )
                self.assertTrue(
                    "activation" in row["current_provider_compatibility"].lower()
                    or "inactive" in row["decision_note"].lower()
                )

    def test_512620_is_listed_only_as_inactive_review_candidate(self):
        records_by_symbol = {row["symbol"]: row for row in mainland()}
        review_by_symbol = {row["symbol"]: row for row in review_rows()}
        self.assertEqual("false", records_by_symbol["512620"]["active"].lower())
        self.assertEqual(
            records_by_symbol["512620"]["name"],
            review_by_symbol["512620"]["instrument_scope"],
        )

    def test_primary_sse_review_names_match_inactive_universe(self):
        universe = {row["symbol"]: row for row in mainland()}
        reviews = {row["symbol"]: row for row in review_rows()}
        for symbol in ("512480", "512700", "512170", "512580", "512660", "512690", "515050", "515220"):
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    universe[symbol]["name"], reviews[symbol]["instrument_scope"]
                )
                self.assertEqual("false", universe[symbol]["active"].lower())
                self.assertIn("www.sse.com.cn", reviews[symbol]["evidence_url"])
                if symbol != "512580":
                    self.assertIn("CNY", reviews[symbol]["decision_note"])

    def test_515050_split_event_is_explicitly_flagged_before_activation(self):
        reviews = {row["symbol"]: row for row in review_rows()}
        row = reviews["515050"]
        self.assertIn("2026-05-12", row["current_provider_compatibility"])
        self.assertIn("1:3", row["current_provider_compatibility"])
        self.assertIn("adjusted", row["current_provider_compatibility"].lower())
        self.assertIn("inactive", row["decision_note"].lower())

    def test_all_mainland_review_records_have_primary_evidence_urls(self):
        for row in review_rows():
            with self.subTest(symbol=row["symbol"]):
                self.assertTrue(row["evidence_url"].startswith("https://"))
                self.assertTrue(
                    "sse.com.cn" in row["evidence_url"]
                    or "hkex.com.hk" in row["evidence_url"]
                )
                self.assertEqual(
                    "provider_price_history_confirmed_activation_pending",
                    row["dashboard_status"],
                )

    def test_no_delisted_china_etfs_active(self):
        rejected = {r["symbol"] for r in records("data/country_sector_proxy_candidates.csv")
                    if r["country"] == "China" and
                    r["dashboard_status"] == "rejected_delisted"}
        active = {r["symbol"] for r in records("data/monitoring_universe.csv")
                  if r["active"].lower() == "true"}
        self.assertFalse(rejected & active)

    def test_review_registry_gap_is_explicitly_known(self):
        # Deliberately document a review-only gap; don't equate it with missing OHLCV.
        known = {
            "515120",
            "515070", "515210", "516150", "516160", "516970",
            "515880", "512290", "515170", "515650", "515790",
        }
        observed = {r["symbol"] for r in mainland()} - {
            r["symbol"] for r in review_rows()
        }
        self.assertEqual(known, observed)


if __name__ == "__main__":
    unittest.main()
