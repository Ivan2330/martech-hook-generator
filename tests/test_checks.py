"""Tests for similarity dedupe and compliance flags."""

import pytest

from checks import compliance_flags, dedupe_similar, original_phrases, similarity

WINNER = '''HOOK (0–3s, on-screen: "Where do my socks GO?"):
"Okay, I'm convinced my washing machine is eating my socks."'''


def v(text: str) -> dict:
    """Make a variant dict with just the text we care about."""
    return {"text": text, "angle": "pain", "why": ""}


def test_similarity_bounds():
    assert similarity("Same text", "same TEXT") == 1.0
    assert similarity("My dryer has a sock habit", "POV: laundry day") < 0.5


def test_original_phrases_takes_quoted_lines():
    assert original_phrases(WINNER) == [
        "Where do my socks GO?",
        "Okay, I'm convinced my washing machine is eating my socks.",
    ]


def test_original_phrases_falls_back_to_lines_without_quotes():
    assert original_phrases("Line one\n\nLine two") == ["Line one", "Line two"]


def test_removes_variant_too_close_to_original():
    kept, removed = dedupe_similar(
        [v("I'm convinced my washing machine is eating all my socks."), v("Grandma solved the sock problem.")],
        WINNER,
    )
    assert [k["text"] for k in kept] == ["Grandma solved the sock problem."]
    assert len(removed) == 1
    assert removed[0]["similar_to"] == "Okay, I'm convinced my washing machine is eating my socks."
    assert 0.75 <= removed[0]["similarity"] <= 1


def test_removes_later_variant_too_close_to_earlier_one():
    kept, removed = dedupe_similar(
        [v("My kids lose a sock every single day."), v("My kids lose a sock every single day!"), v("POV: 7am drawer hunt")],
        WINNER,
    )
    assert [k["text"] for k in kept] == ["My kids lose a sock every single day.", "POV: 7am drawer hunt"]
    assert [r["text"] for r in removed] == ["My kids lose a sock every single day!"]


def test_removes_variant_repeating_an_earlier_section():
    kept, removed = dedupe_similar(
        [v("I'm a mom of three."), v("Laundry day, again.")], WINNER, earlier=["I'm a mom of three!"]
    )
    assert [k["text"] for k in kept] == ["Laundry day, again."]
    assert removed[0]["similar_to"] == "I'm a mom of three!"


def test_keeps_everything_when_all_different():
    variants = [v("My dryer has a sock habit."), v("Three kids, forty-two socks."), v("Nurse life: no time to sort.")]
    kept, removed = dedupe_similar(variants, WINNER)
    assert kept == variants and removed == []


def test_empty_original_keeps_variants():
    kept, removed = dedupe_similar([v("Grandma solved the sock problem.")], "")
    assert len(kept) == 1 and removed == []


def test_flags_risky_claims():
    assert compliance_flags("Never lose a sock again, guaranteed!") == [
        '"guaranteed": absolute guarantee (FTC)',
        '"Never lose a sock again": absolute promise (FTC)',
    ]
    assert compliance_flags("100% of pairs stay together") == ['"100%": a percentage needs proof (FTC)']
    assert compliance_flags("100 percent matched") == ['"100 percent": a percentage needs proof (FTC)']
    assert compliance_flags("Magnets that improve circulation") == ['"circulation": health claim (Meta ad policy)']
    assert compliance_flags("Together forever") == ['"forever": absolute promise (FTC)']


@pytest.mark.parametrize(
    "text", ["Never lose a sock.", "No more lost socks, ever.", "Socks that last a lifetime"]
)
def test_flags_absolute_promises_without_again(text):
    assert [f.split(": ")[1] for f in compliance_flags(text)] == ["absolute promise (FTC)"]


@pytest.mark.parametrize("text", ["Together forever", "FOREVER paired.", "Forever-matched socks"])
def test_flags_forever_in_any_case(text):
    flags = compliance_flags(text)
    assert len(flags) == 1 and "absolute promise (FTC)" in flags[0]


def test_honest_copy_has_no_flags():
    assert compliance_flags("The pair stays together in the wash. My drawer finally makes sense.") == []
    assert compliance_flags("The pain of laundry day is real") == []  # 'pain' alone is not a health claim
