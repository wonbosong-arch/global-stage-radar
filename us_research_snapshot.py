"""Prepare and reuse the US research snapshot inside the private app host."""
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import BadZipFile, ZipFile
from zoneinfo import ZoneInfo

import pandas as pd
import pyarrow

from market_data import completed_bar_cutoff_date


INPUT_FILES = (
    "stock_universe_candidates.csv", "unranked_us_stock_master.csv",
    "monitoring_universe.csv", "candidate_daily_prices.csv", "daily_prices.csv",
    "provisional_candidate_stage_report.csv", "yahoo_market_cap_supplement.csv",
)


def input_versions(data_dir):
    versions = []
    for name in INPUT_FILES:
        info = (data_dir / name).stat()
        versions.append((name, info.st_mtime_ns, info.st_ctime_ns, info.st_size))
    return tuple(versions)


@lru_cache(maxsize=2)
def source_revision(files):
    # Include transitive research and Stage dependencies on disk.
    digest = sha256()
    for name, *_ in files:
        path = Path(name)
        digest.update(path.name.encode())
        digest.update(sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def snapshot_key(versions, raw, receipt, as_of, completed_session):
    root = Path(__file__).resolve().parent
    sources = tuple((str(path), path.stat().st_mtime_ns, path.stat().st_size)
                    for path in sorted(root.glob("*.py")) if not path.name.startswith("_"))
    fields = (versions, sha256(raw).hexdigest(), receipt, as_of, completed_session,
              source_revision(sources), pd.__version__, pyarrow.__version__)
    return sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def cache_path(data_dir):
    namespace = sha256(os.fsencode(data_dir.resolve())).hexdigest()
    return Path.home() / ".cache" / "global-stage-radar" / f"us-research-{namespace}.zip"


def read_snapshot(path, key):
    try:
        with ZipFile(path) as archive:
            if archive.comment != key.encode():
                return None
            return tuple(pd.read_feather(BytesIO(archive.read(name)))
                         for name in ("report.feather", "prices.feather"))
    except (OSError, BadZipFile, KeyError, ValueError):
        return None


def write_snapshot(path, key, frames):
    temporary = None
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            with ZipFile(output, "w") as archive:
                archive.comment = key.encode()
                for name, frame in zip(("report.feather", "prices.feather"), frames):
                    buffer = BytesIO()
                    frame.to_feather(buffer)
                    archive.writestr(name, buffer.getbuffer())
        os.replace(temporary, path)
    except (OSError, ValueError, TypeError):
        # The existing in-process result still works on read-only hosts.
        pass
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def load_or_build(data_dir, versions, raw, receipt, as_of, completed_session, now):
    from us_research_dashboard import build_research

    # A temporary classification outage must not replace the approved result.
    key = snapshot_key(versions, raw, receipt, as_of, completed_session) if raw is not None else None
    path = cache_path(data_dir)
    frames = read_snapshot(path, key) if key else None
    if frames is None:
        def read(name):
            return pd.read_csv(data_dir / name, dtype=str, keep_default_na=False)

        *prices_and_metadata, supplement = map(read, INPUT_FILES)
        frames = build_research(*prices_and_metadata, raw=raw, receipt=receipt,
                                supplement=supplement, as_of=as_of, now=now)
        if key and versions == input_versions(data_dir):
            write_snapshot(path, key, frames)
    if versions != input_versions(data_dir):
        raise ValueError("Research inputs changed during snapshot preparation")
    return frames


if __name__ == "__main__":
    from us_research_dashboard import approved_classification

    data_dir = Path(__file__).resolve().parent / "data"
    raw, receipt = approved_classification()
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    report, prices = load_or_build(data_dir, input_versions(data_dir), raw, receipt,
                                   now.date().isoformat(), completed_bar_cutoff_date("NAS", now), now)
    print(f"US research snapshot prepared for {len(report):,} rows and {prices.symbol.nunique():,} charts.")
