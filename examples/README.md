# examples/

Fictional winning ad scripts for SockLock, written for this homework (no real SockLock data is available).
Used as few-shot references in the prompt: the generator learns the brand voice and structure (hook → pain → solution → CTA) from them.

`demo_output.json` is a saved raw model answer for `winner_01` (recorded on local `qwen2.5:7b`). It is returned in demo mode (`PROVIDER=demo`, or `PROVIDER=anthropic` without `ANTHROPIC_API_KEY`) and goes through the same parsing, dedupe and compliance checks as a live answer.
