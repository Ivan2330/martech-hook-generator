"""Tests for the usage log and the pilot metrics."""

from datetime import datetime, timedelta

import pytest

import usage


@pytest.fixture(autouse=True)
def temp_log_file(tmp_path, monkeypatch):
    """Point usage_log.csv to a temp file so tests never touch the real one."""
    monkeypatch.setattr(usage, "LOG_FILE", tmp_path / "usage_log.csv")


def test_empty_log_has_no_metrics():
    assert usage.acceptance() == (0, 0)
    assert usage.active_designers() == 0


def test_counts_likes_against_shown_variants():
    brief = {
        "hooks": [{"angle": "pain"}, {"angle": "hero"}, {"angle": "voice"}],
        "on_screen": [{"angle": "format"}],
    }
    usage.log_generate("Olia", brief, ["hooks", "on_screen"])
    usage.log_event("Olia", "like", "hooks", "hero")
    usage.log_event("Olia", "dislike", "hooks", "pain")
    assert usage.acceptance() == (1, 4)


def test_log_has_header_once_and_designer_column():
    usage.log_event("Olia", "like", "hooks", "pain")
    usage.log_event("Taras", "dislike", "on_screen", "voice")
    lines = usage.LOG_FILE.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "timestamp,designer,action,section,angle"
    assert len(lines) == 3 and lines[2].endswith(",Taras,dislike,on_screen,voice")


def test_active_designers_counts_unique_names_in_last_week():
    usage.log_event("Olia", "generate", "hooks", "pain")
    usage.log_event("Olia", "generate", "hooks", "hero")
    usage.log_event("Taras", "generate", "hooks", "pain")
    usage.log_event("Ira", "like", "hooks", "pain")  # a like alone is not "used the tool to generate"
    old = (datetime.now() - timedelta(days=10)).isoformat(timespec="seconds")
    with usage.LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{old},Max,generate,hooks,pain\n")  # Max used it, but not this week
    assert usage.active_designers() == 2
