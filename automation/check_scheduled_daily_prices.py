"""Validate Worker inputs and skip already saved scheduled collections."""
from datetime import datetime, timedelta, timezone
from hashlib import file_digest
import json
import os
from pathlib import Path
import sys


CANDIDATE_STATUS_PATH = Path("data/candidate_daily_prices_status.json")
CANDIDATE_PRICES_PATH = Path("data/candidate_daily_prices.csv")
SLOTS = {
    "operating": (22, 0, (6, 0, 1, 2, 3, 4)),
    "japan": (7, 30, range(5)),
    "china": (9, 30, range(5)),
    "crypto": (0, 15, range(7)),
}
AUXILIARY_SNAPSHOTS = {
    "japan": Path("data/japan_candidate_prices.csv"),
    "crypto": Path("data/crypto_daily_prices.csv"),
}


def parse_scheduled_slot(scheduled_at: str, collection: str = "operating") -> datetime:
    slot = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    hour, minute, weekdays = SLOTS[collection]
    if (
        slot.utcoffset() != timedelta(0)
        or slot.weekday() not in weekdays
        or (slot.hour, slot.minute) != (hour, minute)
        or slot > datetime.now(timezone.utc)
    ):
        raise ValueError(f"Unexpected {collection} collection slot")
    return slot.replace(second=0, microsecond=0)


def read_status(path: Path) -> dict:
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
        return status if isinstance(status, dict) else {}
    except (OSError, ValueError):
        return {}


def completed_symbols(status: dict, scheduled_slot: str) -> set[str]:
    if scheduled_slot and status.get("scheduled_slot") == scheduled_slot:
        return set(status.get("scheduled_completed_symbols", []))
    return set()


def snapshot_covers_slot(
    slot: datetime, status_path: Path, prices_path: Path, collection: str,
) -> bool:
    status = read_status(status_path)
    try:
        return prices_path.is_file() and parse_scheduled_slot(
            status["last_completed_scheduled_slot"], collection,
        ) >= slot
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def candidate_snapshot_covers_slot(
    slot: datetime,
    status_path: Path = CANDIDATE_STATUS_PATH,
    prices_path: Path = CANDIDATE_PRICES_PATH,
) -> bool:
    status = read_status(status_path)
    try:
        if parse_scheduled_slot(status["last_completed_scheduled_slot"]) < slot:
            return False
        with prices_path.open("rb") as prices:
            return file_digest(prices, "sha256").hexdigest() == status["snapshot_sha256"]
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def write_step_outputs(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with Path(path).open("a", encoding="utf-8") as output:
            for name, value in values.items():
                output.write(f"{name}={value}\n")


def main() -> None:
    scheduled_at = os.environ.get("SCHEDULED_AT", "")
    if not scheduled_at:
        return

    mode = sys.argv[1].removeprefix("--") if len(sys.argv) > 1 else "operating"
    collection = {"candidate": "operating", "japan-operating": "japan"}.get(mode, mode)
    slot = parse_scheduled_slot(scheduled_at, collection)
    if mode == "candidate":
        skip = candidate_snapshot_covers_slot(slot)
    else:
        prices = AUXILIARY_SNAPSHOTS.get(mode, Path("data/daily_prices.csv"))
        status = prices.with_name(f"{prices.stem}_status.json")
        if mode == "japan-operating":
            status = Path("data/japan_operating_prices_status.json")
        skip = snapshot_covers_slot(slot, status, prices, collection)

    write_step_outputs(scheduled_slot=slot.isoformat())
    if mode == "operating" and slot.weekday() == 6:
        write_step_outputs(weekly="true")
    if skip:
        write_step_outputs(skip="true")
        message = "Skipped collection: a complete price snapshot already covers this slot."
        print(message)
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as summary:
            summary.write(f"{message}\n")


if __name__ == "__main__":
    main()
