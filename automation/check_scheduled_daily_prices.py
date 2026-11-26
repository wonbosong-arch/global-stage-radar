"""Skip a scheduled collection if its full snapshot is already saved."""
from datetime import datetime, timedelta, timezone
from hashlib import file_digest
import json
import os
from pathlib import Path
import sys


STATUS_PATH = Path("data/daily_prices_status.json")
CANDIDATE_STATUS_PATH = Path("data/candidate_daily_prices_status.json")
CANDIDATE_PRICES_PATH = Path("data/candidate_daily_prices.csv")


def parse_scheduled_slot(scheduled_at: str, minute: int) -> datetime:
    slot = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    if (
        slot.utcoffset() != timedelta(0)
        or slot.weekday() == 5
        or (slot.hour, slot.minute) != (22, minute)
        or slot > datetime.now(timezone.utc)
    ):
        raise ValueError(f"scheduled_at must be a past Sunday–Friday 22:{minute:02d} UTC slot")
    return slot.replace(second=0, microsecond=0)


def snapshot_covers_slot(scheduled_at: str, status_path: Path = STATUS_PATH) -> bool:
    if not scheduled_at:
        return False  # Pushes and ordinary manual dispatches still refresh prices.

    slot = parse_scheduled_slot(scheduled_at, 13)
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        updated = datetime.fromisoformat(status["updated_at_utc"])
        requested = status["requested_symbols"]
        return (
            updated >= slot - timedelta(minutes=30)
            and requested > 0
            and len(status["fresh_data_symbols"]) == requested
            and status["symbols_with_data"] == requested
            and status["errors"] == []
        )
    except (FileNotFoundError, ValueError, TypeError, KeyError):
        return False


def candidate_snapshot_covers_slot(
    slot: datetime,
    status_path: Path = CANDIDATE_STATUS_PATH,
    prices_path: Path = CANDIDATE_PRICES_PATH,
) -> bool:
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        saved_slot = parse_scheduled_slot(status["last_completed_scheduled_slot"], 35)
        if saved_slot < slot:
            return False
        with prices_path.open("rb") as prices:
            return file_digest(prices, "sha256").hexdigest() == status["snapshot_sha256"]
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def main() -> None:
    scheduled_at = os.environ.get("SCHEDULED_AT", "")
    if not scheduled_at:
        return

    if sys.argv[1:] == ["--candidate"]:
        slot = parse_scheduled_slot(scheduled_at, 35)
        skip = candidate_snapshot_covers_slot(slot)
        if not skip:
            with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
                output.write(f"scheduled_slot={slot.isoformat()}\n")
    else:
        skip = snapshot_covers_slot(scheduled_at)

    if skip:
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write("skip=true\n")
        message = "Skipped collection: a complete price snapshot already covers this slot."
        print(message)
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as summary:
            summary.write(f"{message}\n")


if __name__ == "__main__":
    main()
