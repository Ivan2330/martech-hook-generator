"""Shared team memory: designer 👍/👎 become short rules that go into every next prompt."""

import json
from pathlib import Path

from generator import call_model, get_provider

MEMORY_FILE = Path(__file__).parent / "memory.json"
MAX_TOKENS = 1000  # the whole rule list stays this small, so it never crowds out the prompt
MAX_RULE_CHARS = 300  # one long rule (e.g. a pasted paragraph as "why") must not push out all the others

RULE_PROMPT = """A motion designer rated one variation of a SockLock ad line (magnetic socks, US video ads on Meta).
Turn this feedback into ONE rule for writing future variations, at most 25 words.
Phrase it as what to do, for example "Open hooks with a concrete number from family life." Positive instructions are easier to follow than bans.
Generalize from this one line to a pattern, so the rule helps on other scripts too.
Reply with the rule only."""


def load_rules() -> list[str]:
    """Read the rule list from memory.json, oldest first; empty if the file is missing or broken."""
    if not MEMORY_FILE.exists():
        return []
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Keep the broken file for a human to look at, and start a clean memory instead of crashing the app.
        MEMORY_FILE.replace(MEMORY_FILE.with_suffix(".broken.json"))
        return []


def save_rules(rules: list[str]) -> None:
    """Write the rule list to memory.json."""
    MEMORY_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


def estimate_tokens(rules: list[str]) -> int:
    """Rough token count: about 4 characters per token in English."""
    return sum(len(rule) for rule in rules) // 4


def trim_to_budget(rules: list[str], max_tokens: int = MAX_TOKENS) -> list[str]:
    """Drop the oldest rules until the list fits the token budget."""
    while rules and estimate_tokens(rules) > max_tokens:
        rules = rules[1:]
    return rules


def template_rule(variant: dict, section: str, liked: bool, reason: str = "") -> str:
    """Make a rule without a model (demo mode): a plain 'do this' sentence built from the variant."""
    angle, text = variant["angle"], variant["text"]
    if liked:
        rule = f'Write more {angle} {section} like "{text}"'
    else:
        rule = f'Write {angle} {section} that take a different direction from "{text}"'
    return f"{rule}: {reason}." if reason else f"{rule}."


def make_rule(variant: dict, section: str, liked: bool, reason: str = "") -> str:
    """Turn one 👍/👎 (+ optional reason) into one short positive rule, using the model when there is one."""
    if get_provider() == "demo":
        return template_rule(variant, section, liked, reason)
    feedback = (
        f"Section: {section}\nAngle: {variant['angle']}\nVariation: {variant['text']}\n"
        f"Rating: {'liked' if liked else 'disliked'}\nDesigner's reason: {reason or 'not given'}"
    )
    answer = call_model(RULE_PROMPT, feedback, json_answer=False)
    return answer.strip().splitlines()[0].strip(' "')


def delete_rule(rule: str) -> list[str]:
    """Remove this rule (a designer disagrees with it) and return the updated list."""
    rules = load_rules()
    if rule in rules:  # by text, not position: another designer may have changed the list meanwhile
        rules.remove(rule)
        save_rules(rules)
    return rules


def add_rule(rule: str) -> list[str]:
    """Append a rule to memory.json, trim to the budget, and return the updated list."""
    rules = trim_to_budget(load_rules() + [rule[:MAX_RULE_CHARS]])
    save_rules(rules)
    return rules
