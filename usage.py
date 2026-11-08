"""Usage log for the pilot: who saw what and what they liked, in usage_log.csv."""

import csv
from datetime import datetime, timedelta
from pathlib import Path

LOG_FILE = Path(__file__).parent / "usage_log.csv"
FIELDS = ["timestamp", "designer", "action", "section", "angle"]


def log_event(designer: str, action: str, section: str = "", angle: str = "") -> None:
    """Append one row: action is 'generate' (one row per shown variant), 'like' or 'dislike'."""
    is_new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(FIELDS)
        writer.writerow([datetime.now().isoformat(timespec="seconds"), designer, action, section, angle])


def log_generate(designer: str, brief: dict, sections: list[str]) -> None:
    """Log every variant shown to the designer, so we can count the share they take."""
    for section in sections:
        for variant in brief[section]:
            log_event(designer, "generate", section, variant["angle"])


def read_log() -> list[dict]:
    """All rows of the log as dicts; empty if nothing was logged yet."""
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def acceptance() -> tuple[int, int]:
    """Return (likes, shown) over the whole log; likes / shown is the 'variants taken' metric."""
    actions = [row["action"] for row in read_log()]
    return actions.count("like"), actions.count("generate")


def active_designers(days: int = 7) -> int:
    """How many different designers generated a brief in the last N days (the adoption metric)."""
    since = datetime.now() - timedelta(days=days)
    return len({
        row["designer"]
        for row in read_log()
        if row["action"] == "generate" and datetime.fromisoformat(row["timestamp"]) >= since
    })
