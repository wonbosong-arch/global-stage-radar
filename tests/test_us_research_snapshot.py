from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import pandas as pd

import us_research_dashboard
import us_research_snapshot as snapshot


class ResearchSnapshotTests(TestCase):
    def test_reuses_private_snapshot_and_refreshes_changed_inputs(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        data_dir = root / "data"
        data_dir.mkdir()
        for name in snapshot.INPUT_FILES:
            (data_dir / name).write_text("symbol,close\nAAA,1\n", encoding="utf-8")
        cache_file = root / "private" / "snapshot.zip"
        self.enterContext(patch.object(snapshot, "cache_path", return_value=cache_file))
        calls = []

        def build(registry, master, universe, prices, *args, **kwargs):
            calls.append(kwargs["raw"])
            report = pd.DataFrame({"symbol": ["AAA"], "research_eligible": [True]})
            return report, prices.assign(date=pd.Timestamp("2026-11-20"))

        mock_build = self.enterContext(patch.object(us_research_dashboard, "build_research", side_effect=build))

        def load(raw=b"approved", receipt=None, session="2026-11-20"):
            return snapshot.load_or_build(
                data_dir, snapshot.input_versions(data_dir), raw, receipt or {"version": 1},
                "2026-11-24", session, datetime(2026, 11, 24))

        original = load()
        for actual, expected in zip(load(), original):
            pd.testing.assert_frame_equal(actual, expected)
        self.assertEqual(calls, [b"approved"])

        load(raw=None)
        load()
        self.assertEqual(calls, [b"approved", None])

        for kwargs in ({"raw": b"updated"}, {"receipt": {"version": 2}}, {"session": "2026-11-23"}):
            load(**kwargs)
            load(**kwargs)
        self.assertEqual(calls, [b"approved", None, b"updated", b"approved", b"approved"])

        price_file = data_dir / "candidate_daily_prices.csv"
        price_file.write_text("symbol,close\nAAA,20\n", encoding="utf-8")
        self.assertEqual(load(session="2026-11-23")[1].close.tolist(), ["20"])
        cache_file.write_bytes(b"interrupted snapshot")
        self.assertEqual(load(session="2026-11-23")[1].close.tolist(), ["20"])
        self.assertEqual(len(calls), 7)

        def changed_during_build(*args, **kwargs):
            price_file.write_text("symbol,close\nAAA,300\n", encoding="utf-8")
            return original

        mock_build.side_effect = changed_during_build
        previous = cache_file.read_bytes()
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            load(session="2026-11-24")
        self.assertEqual(cache_file.read_bytes(), previous)
