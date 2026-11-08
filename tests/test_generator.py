"""Tests for parsing the model's answer, the pipeline and the prompt."""

import json

import pytest

import generator
from generator import ANGLES, build_prompt, build_schema, parse_response


def grouped(texts_by_angle: dict) -> dict:
    """Build one section in the model's format: {angle: [{text, why}]} for all five angles."""
    return {angle: [{"text": t, "why": "w"} for t in texts_by_angle.get(angle, [])] for angle in ANGLES}


ANSWER = {
    "hooks": grouped({"pain": ["My dryer has a sock habit."], "hero": ["Mom of three here."]}),
    "first_lines": grouped({"pain": ["Every Sunday, a pile of singles."]}),
    "on_screen": grouped({"format": ["POV: laundry day"]}),
}


def test_flattens_groups_into_list_with_angle():
    brief = parse_response(json.dumps(ANSWER))
    assert brief["hooks"] == [
        {"text": "My dryer has a sock habit.", "angle": "pain", "why": "w"},
        {"text": "Mom of three here.", "angle": "hero", "why": "w"},
    ]
    assert brief["on_screen"] == [{"text": "POV: laundry day", "angle": "format", "why": "w"}]


def test_flatten_takes_angles_in_turn():
    answer = dict(ANSWER, hooks=grouped({"pain": ["p1", "p2"], "hero": ["h1", "h2"], "voice": ["v1"]}))
    texts = [v["text"] for v in parse_response(json.dumps(answer))["hooks"]]
    assert texts == ["p1", "h1", "v1", "p2", "h2"]  # a cut to N keeps the angle mix


def test_parses_json_inside_markdown_fence():
    text = "Here you go:\n```json\n" + json.dumps(ANSWER) + "\n```"
    assert parse_response(text) == parse_response(json.dumps(ANSWER))


def test_drops_items_without_text_and_tolerates_missing_angle():
    hooks = {"pain": [{"text": "  Keep me  "}, {"why": "no text"}, "not a dict"]}  # other angles missing
    brief = parse_response(json.dumps(dict(ANSWER, hooks=hooks)))
    assert brief["hooks"] == [{"text": "Keep me", "angle": "pain", "why": ""}]


def test_missing_section_raises():
    answer = {"hooks": ANSWER["hooks"], "first_lines": ANSWER["first_lines"]}
    with pytest.raises(ValueError, match="on_screen"):
        parse_response(json.dumps(answer))


def test_not_json_raises():
    with pytest.raises(ValueError):
        parse_response("Sorry, I can't help with that.")


def test_schema_counts_only_when_asked():
    with_counts = build_schema(with_counts=True)["properties"]["hooks"]["properties"]["pain"]
    without = build_schema(with_counts=False)["properties"]["hooks"]["properties"]["pain"]
    assert (with_counts["minItems"], with_counts["maxItems"]) == (2, 3)
    assert "minItems" not in without


def test_generate_dedupes_cuts_and_flags(monkeypatch):
    hooks = grouped({
        "pain": ["My dryer has a sock habit.", "My dryer has a sock habit!", "Sunday sorting, cancelled."],
        "hero": ["Three kids, forty-two socks.", "Nurse life: zero time to sort.", "Grandma fixed laundry day."],
        "format": ["POV: 7am drawer hunt", "Confession: I buy new socks monthly.", "Is it just my house?"],
        "emotion": ["College dorm laundry is chaos.", "Dads, this one's for you."],
        "voice": ["Where do they even go?", "The quiz took thirty seconds."],
    })
    on_screen = grouped({"voice": ["Guaranteed: together forever"]})
    answer = dict(ANSWER, hooks=hooks, on_screen=on_screen)
    monkeypatch.setattr(generator, "call_model", lambda system, user: json.dumps(answer))

    brief = generator.generate('HOOK: "Where do my socks GO?"')

    assert len(brief["hooks"]) == 10  # 13 written, 1 near-duplicate removed → 12, cut to 10
    assert [r["text"] for r in brief["removed"]["hooks"]] == ["My dryer has a sock habit!"]
    assert {v["angle"] for v in brief["hooks"]} == set(ANGLES)
    assert brief["first_lines"][0]["flags"] == []
    assert len(brief["on_screen"][0]["flags"]) == 2  # "Guaranteed" + "forever"


def test_generate_drops_first_line_that_repeats_a_hook(monkeypatch):
    answer = dict(
        ANSWER,
        hooks=grouped({"hero": ["I'm a mom of three."]}),
        first_lines=grouped({"hero": ["I'm a mom of three!"], "pain": ["Sunday sorting takes forty minutes."]}),
    )
    monkeypatch.setattr(generator, "call_model", lambda system, user: json.dumps(answer))
    brief = generator.generate("HOOK: socks")
    assert [v["text"] for v in brief["first_lines"]] == ["Sunday sorting takes forty minutes."]
    assert brief["removed"]["first_lines"][0]["similar_to"] == "I'm a mom of three."


def test_generate_keeps_script_in_brief(monkeypatch):
    monkeypatch.setattr(generator, "call_model", lambda system, user: json.dumps(ANSWER))
    assert generator.generate("HOOK: socks")["script"] == "HOOK: socks"


def test_empty_script_raises():
    with pytest.raises(ValueError, match="empty"):
        generator.generate("   ")


def test_demo_file_parses():
    brief = parse_response(generator.DEMO_FILE.read_text(encoding="utf-8"))
    assert all(brief[section] for section in generator.SECTIONS)


def test_anthropic_without_key_falls_back_to_demo(monkeypatch):
    monkeypatch.setenv("PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert generator.get_provider() == "demo"


def test_prompt_contains_examples_rules_and_script():
    system, user = build_prompt("HOOK: socks vanish", ["Use a mom's voice in hooks."])
    assert "washing machine" in system  # a few-shot example from examples/
    assert "- Use a mom's voice in hooks." in system
    assert "{examples}" not in system and "{rules}" not in system
    assert "HOOK: socks vanish" in user
