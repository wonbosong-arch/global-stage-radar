from datetime import datetime, timezone
from unittest import TestCase
import pandas as pd

from favorite_assets import asset_id, bookmark, decode_bookmarks, merge_bookmarks, watchlist_frame


class FavoriteAssetTests(TestCase):
    def test_exchange_identity_deduplicates_shared_views_without_merging_venues(self):
        first = bookmark(dict(symbol="ABC", exchange="NAS", name="Alpha", asset_type="stock"))
        second = bookmark(dict(symbol="ABC", exchange="NYS", name="Beta", asset_type="stock"))
        records = merge_bookmarks([first, second], [dict(first, name="Updated")])
        self.assertEqual([r["id"] for r in records], ["NAS:ABC", "NYS:ABC"])
        self.assertEqual(records[0]["name"], "Updated")
        self.assertEqual(merge_bookmarks(records, [], ["NAS:ABC"]), [second])

    def test_no_stage_gate_and_missing_data_preserves_bookmark(self):
        saved = bookmark(dict(symbol="ABC", exchange="NAS", name="Alpha", asset_type="stock",
                              last_daily_date="2026-10-29", ret26_pct=15))
        current = pd.DataFrame([dict(saved, stage_label="Stage 4 하락")])
        frame = watchlist_frame([saved], current)
        self.assertEqual(frame.stage_label.tolist(), ["Stage 4 하락"])
        self.assertTrue(frame.iloc[0].price_available)
        missing = watchlist_frame([saved], current.iloc[:0])
        self.assertEqual(missing.id.tolist(), [saved["id"]])
        self.assertFalse(missing.iloc[0].price_available)
        self.assertEqual(missing.iloc[0].last_daily_date, "2026-10-29")

    def test_filters_and_all_sort_orders(self):
        rows = [bookmark(dict(symbol="B", name="Beta", exchange="NAS", asset_type="stock", ret26_pct=30), "2026-10-01"),
                bookmark(dict(symbol="A", name="Alpha", exchange="NYS", asset_type="sector_etf", ret26_pct=20), "2026-10-03"),
                bookmark(dict(symbol="C", name="Gamma", exchange="NYS", asset_type="market_etf", ret26_pct=50), "2026-10-02")]
        current = pd.DataFrame(rows)
        self.assertEqual(watchlist_frame(rows, current).symbol.tolist(), ["C", "B", "A"])
        self.assertEqual(watchlist_frame(rows, current, sort="이름순").symbol.tolist(), ["A", "B", "C"])
        self.assertEqual(watchlist_frame(rows, current, sort="관심 등록순").symbol.tolist(), ["B", "C", "A"])
        for area, symbol in [("종목", "B"), ("업종", "A"), ("국가·원자재", "C")]:
            self.assertEqual(watchlist_frame(rows, current, area).symbol.tolist(), [symbol])

    def test_browser_payload_is_bounded_and_does_not_import_arbitrary_fields(self):
        self.assertEqual(decode_bookmarks({}), [])
        self.assertEqual(decode_bookmarks([{"symbol": "<script>"}]), [])
        good = decode_bookmarks([dict(symbol="ABC", exchange="NAS", password="secret", ret26_pct=float("inf"))])
        self.assertNotIn("password", good[0])
        self.assertIsNone(good[0]["ret26_pct"])
        self.assertEqual(asset_id(dict(symbol="abc", exchange="nas")), "NAS:ABC")

    def test_ambiguous_ticker_never_reuses_other_exchange_price(self):
        rows = [bookmark(dict(symbol="ABC", exchange=ex, asset_type="stock")) for ex in ["NAS", "NYS"]]
        result = watchlist_frame(rows, pd.DataFrame(rows))
        self.assertEqual(len(result), 2)
        self.assertFalse(result.price_available.any())
