"""Tests for the shared rule memory."""

import pytest

import memory

VARIANT = {"text": "Three kids, forty-two socks.", "angle": "hero", "why": ""}


@pytest.fixture(autouse=True)
def temp_memory_file(tmp_path, monkeypatch):
    """Point memory.json to a temp file so tests never touch the real one."""
    monkeypatch.setattr(memory, "MEMORY_FILE", tmp_path / "memory.json")


def test_no_file_means_no_rules():
    assert memory.load_rules() == []


def test_add_rule_saves_and_appends():
    memory.add_rule("Rule one.")
    memory.add_rule("Rule two.")
    assert memory.load_rules() == ["Rule one.", "Rule two."]


def test_delete_rule_removes_by_text():
    for rule in ["One.", "Two.", "Three."]:
        memory.add_rule(rule)
    assert memory.delete_rule("Two.") == ["One.", "Three."]
    assert memory.load_rules() == ["One.", "Three."]
    assert memory.delete_rule("Already gone.") == ["One.", "Three."]  # no error if someone deleted it first


def test_broken_file_gives_empty_memory_and_is_kept_aside():
    memory.MEMORY_FILE.write_text('["half a rule', encoding="utf-8")
    assert memory.load_rules() == []
    assert memory.MEMORY_FILE.with_suffix(".broken.json").exists()


def test_very_long_rule_is_cut():
    memory.add_rule("Short rule.")
    memory.add_rule("x" * 10_000)
    rules = memory.load_rules()
    assert rules[0] == "Short rule."  # the long rule did not push the others out
    assert len(rules[1]) == memory.MAX_RULE_CHARS


def test_trim_drops_oldest_first():
    rules = ["a" * 400, "b" * 400, "c" * 400]  # ≈ 100 tokens each
    assert memory.trim_to_budget(rules, max_tokens=200) == ["b" * 400, "c" * 400]


def test_add_rule_keeps_memory_within_budget():
    for i in range(30):
        memory.add_rule(f"Rule {i}: " + "x" * 200)  # ≈ 52 tokens each, 30 rules ≈ 1560 tokens
    rules = memory.load_rules()
    assert memory.estimate_tokens(rules) <= memory.MAX_TOKENS
    assert rules[-1].startswith("Rule 29")  # the newest rule survives
    assert not any(r.startswith("Rule 0:") for r in rules)  # the oldest is gone


def test_template_rule_is_positive_and_keeps_reason():
    liked = memory.template_rule(VARIANT, "hooks", liked=True)
    disliked = memory.template_rule(VARIANT, "hooks", liked=False, reason="too generic, name a real moment")
    assert liked == 'Write more hero hooks like "Three kids, forty-two socks.".'
    assert disliked.startswith("Write hero hooks that take a different direction")
    assert disliked.endswith(": too generic, name a real moment.")


def test_make_rule_uses_template_in_demo(monkeypatch):
    monkeypatch.setattr(memory, "get_provider", lambda: "demo")
    assert memory.make_rule(VARIANT, "hooks", liked=True).startswith("Write more hero hooks")


def test_make_rule_asks_model_and_cleans_answer(monkeypatch):
    calls = []

    def fake_model(system, user, json_answer=True):
        calls.append((user, json_answer))
        return '"Open hooks with a concrete family number."\nExtra line the model added.'

    monkeypatch.setattr(memory, "get_provider", lambda: "ollama")
    monkeypatch.setattr(memory, "call_model", fake_model)

    rule = memory.make_rule(VARIANT, "hooks", liked=False, reason="needs a number")
    assert rule == "Open hooks with a concrete family number."
    assert "needs a number" in calls[0][0] and calls[0][1] is False
