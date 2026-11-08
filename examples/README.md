# examples/

Fictional winning ad scripts for SockLock, written for this homework (no real SockLock data is available).
`winner_*.md` are used as few-shot references in the prompt: the generator learns the brand voice and structure (hook → pain → solution → CTA) from them.

`demo_output.json` is a saved raw answer of Claude (`claude-sonnet-5-5`) for `demo_script.md`, a script with a deliberately risky claim ("Never lose a sock again, guaranteed"). It is returned in demo mode (`PROVIDER=demo`, or `PROVIDER=anthropic` without `ANTHROPIC_API_KEY`) and goes through the same parsing, dedupe and compliance checks as a live answer. `demo_script.md` is not a few-shot example.
