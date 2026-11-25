"""Skip a scheduled collection if its full snapshot is already saved."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path


STATUS_PATH = Path("data/daily_prices_status.json")


def snapshot_covers_slot(scheduled_at: str, status_path: Path = STATUS_PATH) -> bool:
    if not scheduled_at:
        return False  # Pushes and ordinary manual dispatches still refresh prices.

    slot = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    if (
        slot.utcoffset() != timedelta(0)
        or slot.weekday() == 5
        or (slot.hour, slot.minute, slot.second, slot.microsecond) != (22, 13, 0, 0)
        or slot > datetime.now(timezone.utc)
    ):
        raise ValueError("scheduled_at must be a past Sunday–Friday 22:13 UTC slot")

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


if __name__ == "__main__":
    if snapshot_covers_slot(os.environ.get("SCHEDULED_AT", "")):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write("skip=true\n")
        message = "Skipped collection: a complete price snapshot already covers this slot."
        print(message)
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as summary:
            summary.write(f"{message}\n")
