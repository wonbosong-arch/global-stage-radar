from datetime import datetime

import pandas as pd
import pytest

import us_research_dashboard
import us_research_snapshot as snapshot


def test_reuses_private_snapshot_and_refreshes_changed_inputs(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in snapshot.INPUT_FILES:
        (data_dir / name).write_text("symbol,close\nAAA,1\n", encoding="utf-8")
    cache_file = tmp_path / "private" / "snapshot.zip"
    monkeypatch.setattr(snapshot, "cache_path", lambda _: cache_file)
    calls = []

    def build(registry, master, universe, prices, *args, **kwargs):
        calls.append(kwargs["raw"])
        report = pd.DataFrame({"symbol": ["AAA"], "research_eligible": [True]})
        return report, prices.assign(date=pd.Timestamp("2026-11-20"))

    monkeypatch.setattr(us_research_dashboard, "build_research", build)

    def load(raw=b"approved", receipt=None, session="2026-11-20"):
        return snapshot.load_or_build(
            data_dir, snapshot.input_versions(data_dir), raw, receipt or {"version": 1},
            "2026-11-24", session, datetime(2026, 11, 24))

    original = load()
    for actual, expected in zip(load(), original):
        pd.testing.assert_frame_equal(actual, expected)
    assert calls == [b"approved"]

    load(raw=None)
    load()
    assert calls == [b"approved", None]

    for kwargs in ({"raw": b"updated"}, {"receipt": {"version": 2}}, {"session": "2026-11-23"}):
        load(**kwargs)
        load(**kwargs)
    assert calls == [b"approved", None, b"updated", b"approved", b"approved"]

    price_file = data_dir / "candidate_daily_prices.csv"
    price_file.write_text("symbol,close\nAAA,20\n", encoding="utf-8")
    assert load(session="2026-11-23")[1].close.tolist() == ["20"]
    cache_file.write_bytes(b"interrupted snapshot")
    assert load(session="2026-11-23")[1].close.tolist() == ["20"]
    assert len(calls) == 7

    def changed_during_build(*args, **kwargs):
        price_file.write_text("symbol,close\nAAA,300\n", encoding="utf-8")
        return original

    monkeypatch.setattr(us_research_dashboard, "build_research", changed_during_build)
    previous = cache_file.read_bytes()
    with pytest.raises(ValueError, match="inputs changed"):
        load(session="2026-11-24")
    assert cache_file.read_bytes() == previous
