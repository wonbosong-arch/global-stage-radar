import pytest


@pytest.fixture(autouse=True)
def isolate_stage_snapshot_cache(monkeypatch, tmp_path):
    """Keep AppTest snapshots and mock research inputs isolated by test case."""
    monkeypatch.setattr(
        "us_research_snapshot.cache_path",
        lambda data_dir, *, scope="us-research": tmp_path / f"{scope}.zip",
    )
