"""Turns a winning ad script into a brief of hook / first line / on-screen variations."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from checks import compliance_flags, dedupe_similar

load_dotenv()

ROOT = Path(__file__).parent
EXAMPLES_DIR = ROOT / "examples"
SYSTEM_PROMPT_FILE = ROOT / "prompts" / "system.md"
DEMO_FILE = EXAMPLES_DIR / "demo_output.json"

SECTIONS = ["hooks", "first_lines", "on_screen"]
ANGLES = ["pain", "hero", "format", "emotion", "voice"]
# How many variations per angle the model must write: (min, max). 5 angles × 2–3 hooks = 10–15 hooks.
PER_ANGLE = {"hooks": (2, 3), "first_lines": (1, 2), "on_screen": (1, 2)}
# How many we show after dropping near-duplicates.
LIMITS = {"hooks": 10, "first_lines": 5, "on_screen": 5}


def build_schema(with_counts: bool) -> dict:
    """JSON schema of the answer: each section is grouped by the five angles, each angle is a list of {text, why}."""
    variant = {
        "type": "object",
        "properties": {"text": {"type": "string"}, "why": {"type": "string"}},
        "required": ["text", "why"],
        "additionalProperties": False,
    }

    def angle_list(section: str) -> dict:
        """List of variations for one angle, with min/max counts when the provider supports them."""
        schema = {"type": "array", "items": variant}
        if with_counts:  # Ollama enforces counts; Claude's structured output does not support them
            schema["minItems"], schema["maxItems"] = PER_ANGLE[section]
        return schema

    def section_schema(section: str) -> dict:
        """One section (e.g. hooks) as an object with all five angles required."""
        return {
            "type": "object",
            "properties": {angle: angle_list(section) for angle in ANGLES},
            "required": ANGLES,
            "additionalProperties": False,
        }

    return {
        "type": "object",
        "properties": {section: section_schema(section) for section in SECTIONS},
        "required": SECTIONS,
        "additionalProperties": False,
    }


def load_examples() -> str:
    """Join all winning scripts from examples/ into one text block for the prompt."""
    files = sorted(EXAMPLES_DIR.glob("winner_*.md"))
    return "\n\n---\n\n".join(f.read_text(encoding="utf-8").strip() for f in files)


def build_prompt(script: str, rules: list[str]) -> tuple[str, str]:
    """Return (system, user) messages: instructions + examples + team rules, then the script."""
    rules_text = "\n".join(f"- {rule}" for rule in rules) or "No rules yet."
    system = (
        SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        .replace("{examples}", load_examples())
        .replace("{rules}", rules_text)
    )
    user = f"Here is the winning script to modify:\n\n<script>\n{script.strip()}\n</script>"
    return system, user


def get_provider() -> str:
    """Pick the model provider from env; without an Anthropic key the 'anthropic' choice falls back to demo."""
    provider = os.getenv("PROVIDER", "demo").lower()
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        return "demo"
    return provider


def call_model(system: str, user: str, json_answer: bool = True) -> str:
    """Send the prompt to the chosen provider and return the raw text of the answer (a brief in JSON, or free text)."""
    provider = get_provider()

    if provider == "demo":
        if not json_answer:
            raise ValueError("Demo mode has no model to write free text.")
        # Saved real answer, so anyone can run the app without a key or a local model.
        return DEMO_FILE.read_text(encoding="utf-8")

    if provider == "ollama":
        import ollama

        response = ollama.chat(
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            # Ollama constrains the output to this JSON schema
            format=build_schema(with_counts=True) if json_answer else None,
            options={"temperature": 0.9},  # more variety between variations
        )
        return response.message.content

    if provider == "anthropic":
        import anthropic

        schema = {"type": "json_schema", "schema": build_schema(with_counts=False)}
        extra = {"output_config": {"format": schema}} if json_answer else {}
        response = anthropic.Anthropic().messages.create(
            model=os.getenv("MODEL", "claude-sonnet-5-5"),
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user}],
            **extra,
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("The model declined this script. Try rephrasing it.")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("The answer was cut off (too long). Try again or shorten the script.")
        # No text block → "" → parse_response explains "did not return JSON".
        return next((block.text for block in response.content if block.type == "text"), "")

    raise ValueError(f"Unknown PROVIDER '{provider}'. Use demo, ollama or anthropic.")


def is_valid(variant: object) -> bool:
    """A usable variation is a dict with non-empty text."""
    return isinstance(variant, dict) and bool(str(variant.get("text", "")).strip())


def flatten_by_angle(groups: dict) -> list[dict]:
    """Turn {angle: [variants]} into one flat list, taking angles in turn (pain 1, hero 1, ..., pain 2, ...) so a cut keeps the mix."""
    clean = {angle: [v for v in groups.get(angle) or [] if is_valid(v)] for angle in ANGLES}
    flat = []
    for i in range(max(len(variants) for variants in clean.values())):
        for angle in ANGLES:
            if i < len(clean[angle]):
                variant = clean[angle][i]
                flat.append({"text": variant["text"].strip(), "angle": angle, "why": variant.get("why", "")})
    return flat


def parse_response(text: str) -> dict:
    """Parse the model's JSON answer into three flat lists of {text, angle, why}."""
    start, end = text.find("{"), text.rfind("}")  # skips ```json fences or chatter around the JSON
    if start == -1 or end == -1:
        raise ValueError("The model did not return JSON.")
    data = json.loads(text[start : end + 1])

    result = {}
    for name in SECTIONS:
        groups = data.get(name)
        if not isinstance(groups, dict):
            raise ValueError(f"The answer has no '{name}' section.")
        result[name] = flatten_by_angle(groups)
    return result


def generate(script: str, rules: list[str] | None = None) -> dict:
    """Full pipeline: prompt → model → parse → drop near-duplicates → cut to 10/5/5 → flag risky claims."""
    if not script.strip():
        raise ValueError("The script is empty.")
    system, user = build_prompt(script, rules or [])
    parsed = parse_response(call_model(system, user))

    brief = {"script": script, "removed": {}}  # keep the script, so the downloaded brief matches its variations
    shown = []  # texts already shown in earlier sections: a first line must not repeat a hook
    for name in SECTIONS:
        kept, removed = dedupe_similar(parsed[name], original=script, earlier=shown)
        brief[name] = kept[: LIMITS[name]]
        shown += [variant["text"] for variant in brief[name]]
        brief["removed"][name] = removed
        for variant in brief[name]:
            variant["flags"] = compliance_flags(variant["text"])
    return brief


if __name__ == "__main__":
    # Usage: python generator.py examples/winner_01_washing_machine.md
    sys.stdout.reconfigure(encoding="utf-8")
    brief = generate(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(f"provider: {get_provider()}")
    for name in SECTIONS:
        print(f"\n== {name}: {len(brief[name])} shown, {len(brief['removed'][name])} removed as too similar")
        for v in brief[name]:
            flags = f"\n    ⚠ {'; '.join(v['flags'])}" if v["flags"] else ""
            print(f"[{v['angle']}] {v['text']}\n    why: {v['why']}{flags}")
        for v in brief["removed"][name]:
            print(f"  (removed, {v['similarity']:.2f} similar to \"{v['similar_to']}\") {v['text']}")
