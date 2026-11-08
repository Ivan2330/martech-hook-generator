"""Checks on generated variations: drop near-duplicates and flag risky claims."""

import re
from difflib import SequenceMatcher

# Phrases Meta / FTC reject: (regex, why it is risky). Flags warn; the designer decides.
RISKY_CLAIMS = [
    (r"\bguarantee[ds]?\b|\brisk[- ]free\b", "absolute guarantee (FTC)"),
    (r"\b\d+(\.\d+)?\s?(%|percent\b)", "a percentage needs proof (FTC)"),
    (
        r"\bforever\b|\blifetime\b|\bnever\b.*\bagain\b|\bnever lose\b|\bno more (lost|losing|missing)\b",
        "absolute promise (FTC)",
    ),
    (
        r"\b(cures?|heals?|healing|pain relief|relieves?|circulation|blisters?|diabetic|arthritis"
        r"|therapeutic|medical|clinically|doctor[- ]approved)\b",
        "health claim (Meta ad policy)",
    ),
]


def similarity(a: str, b: str) -> float:
    """Return how alike two texts are, from 0 (different) to 1 (identical)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def original_phrases(script: str) -> list[str]:
    """Pull the spoken lines and on-screen texts out of a script (everything in quotes)."""
    quoted = re.findall(r'"([^"]+)"', script)
    return quoted or [line for line in script.splitlines() if line.strip()]


def dedupe_similar(
    variants: list[dict], original: str, threshold: float = 0.75, earlier: list[str] | None = None
) -> tuple[list[dict], list[dict]]:
    """Split variants into (kept, removed): removed ones are too close to the original, to texts kept in earlier sections, or to an earlier kept one."""
    references = original_phrases(original) + (earlier or [])
    kept, removed = [], []
    for variant in variants:
        others = references + [k["text"] for k in kept]
        # default="" covers an empty script: similarity with "" is 0, so the variant is kept.
        closest = max(others, key=lambda other: similarity(variant["text"], other), default="")
        score = similarity(variant["text"], closest)
        if score >= threshold:
            # Remember what it matched, so the UI can show why it was removed.
            removed.append({**variant, "similar_to": closest, "similarity": round(score, 2)})
        else:
            kept.append(variant)
    return kept, removed


def compliance_flags(text: str) -> list[str]:
    """Return a warning for each risky claim found in the text, e.g. '"100%": a percentage needs proof (FTC)'."""
    flags = []
    for pattern, reason in RISKY_CLAIMS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            flags.append(f'"{match.group(0)}": {reason}')
    return flags
