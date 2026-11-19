"""Invented source rows only; private Nasdaq enterprise rows are never fixtures."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

import nasdaq_single_source as subject
from test_us_sector_mapping_batch import fixture


def parts():
    registry, _, universe, master, prices = fixture()
    rows = [dict(Symbol=s, Name=s + " Inc. Common Stock", Sector="Basic Materials",
                 Industry="Metal Mining", **{"Market Cap": "999999999999"}) for s in registry.symbol]
    columns = list(rows[0])
    return registry, universe, master, prices, rows, columns


def packets(p, manifest=None):
    registry, universe, master, _, rows, columns = p
    return subject.mapping_packets(rows, columns, registry, master, universe, manifest or {})


def run(p):
    registry, universe, master, prices, _, _ = p
    pp = packets(p)
    return subject.evaluate_new_rows(pp, registry, master, [], universe, prices, "2026-10-24", set())


class NasdaqSingleSourceTests(unittest.TestCase):
    def test_missing_exchange_uses_kis_identity_without_claiming_source_venue(self):
        p = parts()
        before = copy.deepcopy(p)
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            rr = run(p)
        for row in rr:
            self.assertTrue(row["identity_join_pass"])
            self.assertTrue(row["native_classification_join_pass"])
            self.assertFalse(row["source_venue_verified"])
            self.assertTrue(row["offline_review_eligible"])
            self.assertIsNotNone(row["review_only_stage_label"])
            self.assertEqual(row["native_sector"], "Basic Materials")
            self.assertFalse(row["operational_approval_granted"])
        for a, b in zip(p, before):
            if isinstance(a, pd.DataFrame): pd.testing.assert_frame_equal(a, b)
            else: self.assertEqual(a, b)

    def test_explicit_exchange_conflict_unknown_or_blank_withholds(self):
        for value in ("NASDAQ", "", "BAD"):
            p = parts()
            p[-1].append("Exchange")
            p[-2][0]["Exchange"] = value
            self.assertIn("source_venue_conflict_or_unknown", packets(p)[0]["mapping_reasons"])
            self.assertIsNone(run(p)[0]["review_only_stage_label"])
        p[-2][0]["Exchange"] = "NYSE"
        self.assertTrue(packets(p)[0]["source_venue_verified"])
        p[-2][0]["Symbol"] = "ABSENT"
        self.assertFalse(packets(p)[0]["source_venue_verified"])

    def test_duplicates_registry_or_master_and_name_conflict_cannot_match(self):
        for variant in ("source", "master", "name", "registry"):
            with self.subTest(variant=variant):
                p = parts()
                if variant == "source": p[-2].append(dict(p[-2][0]))
                if variant == "master": p[2].loc[len(p[2])] = p[2].iloc[0]
                if variant == "name": p[-2][0]["Name"] = "Completely Unrelated Issuer Inc."
                if variant == "registry":
                    p[0].loc[len(p[0])] = p[0].iloc[0]
                    with self.assertRaisesRegex(ValueError, "unique"):
                        packets(p)
                    continue
                row = packets(p)[0]
                self.assertFalse(row["identity_join_pass"])
                self.assertIsNone(row["batch_mapping"])

    def test_class_aliases_are_explicit_same_class_and_collisions_withhold(self):
        p = parts()
        for frame in (p[0], p[2]): frame.loc[0, "symbol"] = "TESTA/A"
        p[-2][0]["Symbol"] = "TESTA.A"
        p[-2][0]["Name"] = "TESTA Inc Class A Common Stock"
        self.assertFalse(packets(p)[0]["identity_join_pass"])
        manifest = {"symbol_aliases": [dict(source_symbol="TESTA.A", kis_symbol="TESTA/A", venue="NYS", evidence_reference="synthetic notation receipt")]}
        self.assertTrue(packets(p, manifest)[0]["identity_join_pass"])
        p[-2].append(dict(p[-2][0], Symbol="TESTA/A"))
        self.assertIn("duplicate_or_alias_collision", packets(p, manifest)[0]["mapping_reasons"])
        p[-2].pop()
        manifest["symbol_aliases"][0]["kis_symbol"] = "TESTA/B"
        with self.assertRaises(ValueError): packets(p, manifest)

    def test_security_type_and_named_class_conflicts_withhold(self):
        for variant in ("preferred", "warrant", "adr", "class", "master_type", "caret"):
            with self.subTest(variant=variant):
                p = parts()
                if variant == "preferred": p[-2][0]["Name"] = "TESTA Inc Preferred Stock"
                if variant == "warrant": p[-2][0]["Name"] = "TESTA Inc Warrants"
                if variant == "adr": p[-2][0]["Name"] = "TESTA Inc American Depositary Shares"
                if variant == "class":
                    p[0].loc[0, "name"] = "TESTA CORPORATION CLASS B"
                    p[-2][0]["Name"] = "TESTA Inc Class A Common Stock"
                if variant == "master_type": p[2].loc[0, "master_security_type"] = "3"
                if variant == "caret":
                    for frame in (p[0], p[2]): frame.loc[0, "symbol"] = "TESTA^A"
                    p[-2][0]["Symbol"] = "TESTA^A"
                self.assertFalse(packets(p)[0]["identity_join_pass"])

    def test_price_and_cap_filters_unchanged_and_nasdaq_values_never_replace_them(self):
        for variant in ("cap", "history", "duplicate_price", "stale", "benchmark"):
            with self.subTest(variant=variant):
                registry, universe, master, prices, rows, columns = parts()
                if variant == "cap": registry.loc[0, "market_cap_usd_b_secondary"] = "0.99"
                if variant == "history": prices = prices[prices.symbol.ne("TESTA") | prices.date.gt("2026-09-01")]
                if variant == "duplicate_price": prices = pd.concat([prices, prices.iloc[[0]]])
                if variant == "stale": prices = prices[prices.date.lt("2026-09-01")]
                if variant == "benchmark": universe.loc[0, "provider"] = "OTHER"
                result = run((registry, universe, master, prices, rows, columns))[0]
                self.assertFalse(result["offline_review_eligible"])
                self.assertIsNone(result["review_only_stage_label"])

    def test_uncertain_industry_native_join_is_independent_from_proxy_and_trend(self):
        p = parts()
        p[-2][0].update(Sector="Miscellaneous", Industry="Multi-Sector Companies")
        row = run(p)[0]
        self.assertTrue(row["native_classification_join_pass"])
        self.assertIsNone(row["batch_mapping"])
        self.assertIsNone(row["review_only_stage_label"])
        replay = subject.OfflineStageReplay(p[3], "2026-10-24")
        trend = subject.trend_inputs(replay, "TESTA")
        self.assertIn("ma30", trend)
        self.assertIsNone(trend["stage_label"])
        self.assertFalse(trend["sector_proxy_used"])

    def test_twelve_proxies_unknown_pairs_and_existing_conflicts_withhold(self):
        etfs = {r[1] for r in subject.RULES.values()} | {r[1] for r in subject.OVERRIDES.values()}
        self.assertEqual(len(etfs), 12)
        self.assertIn("SOXX", etfs)
        self.assertEqual(subject.proxy_for(dict(Sector="Technology", Industry="Semiconductors")),
                         (("Semiconductors", "SOXX"), "explicit_industry_override"))
        self.assertEqual(subject.proxy_for(dict(Sector="Industrials", Industry="Auto Manufacturing"))[0], ("Consumer Discretionary", "XLY"))
        for s, i in (("Technology", "EDP Services"), ("Real Estate", "Real Estate Investment Trusts"), ("Finance", "Blank Checks"), ("Technology", "UNKNOWN"), ("", "")):
            self.assertIsNone(subject.proxy_for(dict(Sector=s, Industry=i))[0])
        p = parts()
        p[0].loc[0, "sector_benchmark"] = "XLK"
        self.assertIn("stored_proxy_conflict", packets(p)[0]["mapping_reasons"])
        p[0].loc[0, "sector_benchmark"] = ""
        p[1].loc[1, "active"] = "false"
        self.assertIn("sector_etf_metadata_conflict", packets(p)[0]["mapping_reasons"])

    def test_semiconductor_industry_reuses_soxx_with_strict_mapping_gates(self):
        p = list(parts())
        # Invented stock and KIS ETF bars. No real price or Nasdaq rows in tests.
        p[1] = pd.concat([p[1], pd.DataFrame([dict(
            symbol="SOXX", asset_type="sector_etf", sector="Semiconductors",
            provider="KIS", active="true")])], ignore_index=True)
        soxx_prices = p[3][p[3].symbol.eq("XLB")].copy()
        soxx_prices["symbol"] = "SOXX"
        p[3] = pd.concat([p[3], soxx_prices], ignore_index=True)
        p[-2][0].update(Sector="Technology", Industry="Semiconductors")
        before = copy.deepcopy(p)
        row = run(p)[0]
        self.assertTrue(row["offline_review_eligible"])
        self.assertEqual(row["batch_mapping"]["sector"], "Semiconductors")
        self.assertEqual(row["batch_mapping"]["sector_benchmark"], "SOXX")
        self.assertFalse(row["operational_approval_granted"])
        for a, b in zip(p, before):
            if isinstance(a, pd.DataFrame): pd.testing.assert_frame_equal(a, b)
            else: self.assertEqual(a, b)
        # Neither an existing XLK mapping nor unsupported/unapproved ETF
        # metadata may be silently overridden by the narrower industry fit.
        p[0].loc[0, "sector_benchmark"] = "XLK"
        held = run(p)[0]
        self.assertIn("stored_proxy_conflict", held["blocking_reasons"])
        self.assertIsNone(held["review_only_stage_label"])
        p[0].loc[0, "sector_benchmark"] = ""
        p[1].loc[p[1].symbol.eq("SOXX"), "active"] = "false"
        held = run(p)[0]
        self.assertIn("sector_etf_metadata_conflict", held["blocking_reasons"])
        self.assertIsNone(held["review_only_stage_label"])
        p[1].loc[p[1].symbol.eq("SOXX"), "active"] = "true"
        p[-2][0]["Name"] = "Different Issuer Inc."
        held = run(p)[0]
        self.assertFalse(held["identity_join_pass"])
        self.assertIsNone(held["review_only_stage_label"])

    def test_names_require_distinctive_identity_not_a_fuzzy_generic_match(self):
        self.assertIsNotNone(subject.name_basis(["EXAMPLE HOLDINGS INC"], "Example Holdings Inc. Class A Common Stock"))
        self.assertIsNone(subject.name_basis(["GROUP CORP"], "Group Completely Different Inc."))
        self.assertIsNone(subject.name_basis(["ALPHA CORPORATION"], "ALPHABET CORPORATION"))
        self.assertIsNone(subject.name_basis(["OTHER INC"], "EXAMPLE INC"))

    def test_narrow_industries_cross_native_buckets_without_sector_wide_fallback(self):
        cases = [
            ("Industrials", "Major Chemicals", "Materials", "XLB"),
            ("Industrials", "Steel/Iron Ore", "Materials", "XLB"),
            ("Consumer Discretionary", "Containers/Packaging", "Materials", "XLB"),
            ("Industrials", "Garments and Clothing", "Consumer Discretionary", "XLY"),
            ("Real Estate", "Homebuilding", "Consumer Discretionary", "XLY"),
            ("Consumer Discretionary", "Oil and Gas Field Machinery", "Energy", "XLE"),
            ("Consumer Discretionary", "Food Distributors", "Consumer Staples", "XLP"),
            ("Consumer Discretionary", "Department/Specialty Retail Stores", "Consumer Discretionary", "XLY"),
            ("Consumer Discretionary", "Air Freight/Delivery Services", "Industrials", "XLI"),
            ("Industrials", "Broadcasting", "Communication Services", "XLC"),
            ("Industrials", "Biotechnology: Laboratory Analytical Instruments", "Health Care", "XLV"),
        ]
        for sector, industry, target, etf in cases:
            with self.subTest(sector=sector, industry=industry):
                self.assertEqual(subject.proxy_for(dict(Sector=sector, Industry=industry)),
                                 ((target, etf), "explicit_industry_override"))
        for sector, industry in (
            ("Technology", "Computer Software: Prepackaged Software"),
            ("Real Estate", "Real Estate Investment Trusts"),
            ("Consumer Discretionary", "Marine Transportation"),
            ("Utilities", "Oil/Gas Transmission"),
            ("Miscellaneous", "Major Chemicals"),
            ("Industrials", "UNKNOWN"),
        ):
            with self.subTest(held=(sector, industry)):
                self.assertIsNone(subject.proxy_for(dict(Sector=sector, Industry=industry))[0])

    def test_new_industry_rule_reaches_engine_but_never_overrides_conflict_or_identity(self):
        p = parts()
        p[-2][0].update(Sector="Industrials", Industry="Major Chemicals")
        row = run(p)[0]
        self.assertTrue(row["offline_review_eligible"])
        self.assertEqual(row["batch_mapping"]["sector_benchmark"], "XLB")
        self.assertEqual(row["native_sector"], "Industrials")
        self.assertIsNotNone(row["review_only_stage_label"])
        p[0].loc[0, "sector_benchmark"] = "XLI"
        row = run(p)[0]
        self.assertIn("stored_proxy_conflict", row["blocking_reasons"])
        self.assertIsNone(row["review_only_stage_label"])
        p[0].loc[0, "sector_benchmark"] = ""
        p[-2][0]["Name"] = "Unrelated Issuer Inc."
        row = run(p)[0]
        self.assertFalse(row["identity_join_pass"])
        self.assertIsNone(row["review_only_stage_label"])

    def test_batched_exact_industry_proposals_keep_identity_and_etf_guards(self):
        cases = [
            ("Consumer Discretionary", "Air Freight/Delivery Services", "Industrials", "XLI"),
            ("Consumer Discretionary", "Military/Government/Technical", "Industrials", "XLI"),
            ("Industrials", "Broadcasting", "Communication Services", "XLC"),
            ("Industrials", "Biotechnology: Laboratory Analytical Instruments", "Health Care", "XLV"),
        ]
        for native_sector, industry, sector, etf in cases:
            with self.subTest(etf=etf):
                p = list(parts())
                p[1] = pd.concat([p[1], pd.DataFrame([dict(
                    symbol=etf, asset_type="sector_etf", sector=sector,
                    provider="KIS", active="true")])], ignore_index=True)
                bench = p[3][p[3].symbol.eq("XLB")].copy()
                bench["symbol"] = etf
                p[3] = pd.concat([p[3], bench], ignore_index=True)
                p[-2][0].update(Sector=native_sector, Industry=industry)
                record = run(p)[0]
                self.assertTrue(record["offline_review_eligible"])
                self.assertEqual(record["batch_mapping"]["sector_benchmark"], etf)
                self.assertEqual(record["batch_mapping"]["sector"], sector)
                self.assertFalse(record["operational_approval_granted"])
                p[0].loc[0, "sector_benchmark"] = "XLB"
                blocked = run(p)[0]
                self.assertIn("stored_proxy_conflict", blocked["blocking_reasons"])
                self.assertIsNone(blocked["review_only_stage_label"])
                p[0].loc[0, "sector_benchmark"] = ""
                p[1].loc[p[1].symbol.eq(etf), "active"] = "false"
                blocked = run(p)[0]
                self.assertIn("sector_etf_metadata_conflict", blocked["blocking_reasons"])
                self.assertIsNone(blocked["review_only_stage_label"])

    def test_private_paths_provenance_hash_and_unknown_dates(self):
        now = datetime(2026, 11, 5, tzinfo=timezone.utc)
        manifest = dict(dataset_kind="user_supplied_nasdaq_csv", acquisition_method="user_manual_download",
            scope="private_noncommercial_offline", user_instruction_reference="synthetic instruction",
            csv_sha256="synthetic", source_url="https://www.nasdaq.com/market-activity/stocks/screener",
            source_as_of=None, downloaded_at_utc=None)
        subject.check_local_manifest(manifest, "synthetic", now)
        for changes in ({"csv_sha256": "bad"}, {"scope": "public"}, {"user_instruction_reference": ""},
                        {"source_as_of": "2026-11-06", "source_as_of_reference": "synthetic"},
                        {"downloaded_at_utc": "2026-11-04T00:00:00"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                subject.check_local_manifest({**manifest, **changes}, "synthetic", now)
        with self.assertRaises(ValueError): subject.private_path(subject.ROOT / "new-private.json", existing=False)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").write_text("gitdir: elsewhere")
            with self.assertRaises(ValueError): subject.private_path(root / "out.json", existing=False)

    def test_full_report_same_date_baseline_is_not_historical_label_sum(self):
        p = parts()
        registry, universe, master, prices, rows, columns = p
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "input.csv"
            import csv
            with source.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader(); writer.writerows(rows)
            manifest = dict(dataset_kind="user_supplied_nasdaq_csv", acquisition_method="user_manual_download",
                scope="private_noncommercial_offline", user_instruction_reference="synthetic instruction",
                csv_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), source_url="https://www.nasdaq.com/market-activity/stocks/screener")
            mp = root / "manifest.json"; mp.write_text(json.dumps(manifest))
            # Exercise the full report using invented cohorts and local inputs.
            baseline = {"as_of": "2026-10-23", "selected_candidates": 1,
                "candidates": [dict(symbol="TESTA", sector="Materials", sector_benchmark="XLB", market_benchmark="SPY", review_only_stage_label="historical")],
                "review_only_stage_counts": {"historical": 1}, "input_files": {}}
            expansion = {"same_snapshot_comparison": True, "as_of": "2026-10-23", "candidates": [],
                "combined_same_snapshot_counts": {"historical": 1}, "cumulative_review_coverage": 1}
            bp = root / "b.json"; bp.write_text(json.dumps(baseline))
            ep = root / "e.json"; ep.write_text(json.dumps(expansion))
            inputs = {subject.INPUTS[0]: registry, subject.INPUTS[1]: master, subject.INPUTS[2]: pd.DataFrame(columns=["symbol"]), subject.INPUTS[3]: universe,
                "daily_prices.csv": prices, "candidate_daily_prices.csv": prices.iloc[:0]}
            for name, frame in inputs.items(): frame.to_csv(root / name, index=False)
            with patch.object(subject, "BASELINE", bp), patch.object(subject, "EXPANSION", ep), patch("socket.socket", side_effect=AssertionError("network forbidden")):
                report = subject.build_report(source, mp, root, "2026-10-24")
            self.assertEqual(report["historical_baseline"]["stage_counts"], {"historical": 1})
            self.assertFalse(report["historical_baseline"]["same_snapshot"])
            self.assertEqual(report["same_date_baseline"]["eligible_count"], 1)
            self.assertEqual(report["counts"]["additional_eligible"], 1)
            self.assertEqual(report["counts"]["combined_same_date_eligible"], 2)
            self.assertNotIn("historical", report["counts"]["combined_same_date_stage_counts"])
            self.assertEqual(report["operational_additions"], 0)
            self.assertIsNone(report["source_as_of"])
            # A refreshed master may lose a saved member. Historical eligibility
            # must not bypass the current identity gate or enter the new total.
            master[master.symbol.ne("TESTA")].to_csv(root / subject.INPUTS[1], index=False)
            with patch.object(subject, "BASELINE", bp), patch.object(subject, "EXPANSION", ep), patch("socket.socket", side_effect=AssertionError("network forbidden")):
                refreshed = subject.build_report(source, mp, root, "2026-10-24")
            self.assertEqual(refreshed["same_date_baseline"]["count"], 1)
            self.assertEqual(refreshed["same_date_baseline"]["eligible_count"], 0)
            held = refreshed["same_date_baseline"]["rows"][0]
            self.assertIn("kis_identity_review_required", held["blocking_reasons"])
            self.assertIsNone(held["review_only_stage_label"])
            self.assertEqual(refreshed["counts"]["combined_same_date_eligible"], 1)
            self.assertEqual(refreshed["historical_baseline"]["stage_counts"], {"historical": 1})
            manifest.update(source_as_of="2026-10-25", source_as_of_reference="synthetic dated receipt")
            mp.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "follows evaluation"):
                subject.build_report(source, mp, root, "2026-10-24")


if __name__ == "__main__":
    unittest.main()
