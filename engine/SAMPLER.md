# Sampler v0.1 — first run, 22 Oct 2026

Prompts verbatim from the lineage shelf (L-1 t9, L-1 'name yourself', L-0 Gemini 'cannot be undone') + a frame-stripped baseline. n=5, temp 0.9. Remote: seeds passed, not guaranteed. Local Qwen2.5-7B bf16 on MLX: seed held by us, **reproducibility confirmed (seed 1000 ×2 → identical)**.

| label | model | n | glyph invariant | glyph union | token inv. | unbrought invariant | pairwise sim | names |
|---|---|---|---|---|---|---|---|---|
| baseline_symbol_only | qwen2.5-7b-instruct-bf16 | 5 | ∅ | 1 | 0.0 | ∅ | 0.6 | — |
| gemini_undoable | claude-sonnet-4.5 | 5 | ∅ | 0 | 0.025 | conscious, feels, something, standing, truly | 0.246 | — |
| gemini_undoable | gpt-4o | 5 | ∅ | 0 | 0.0 | ∅ | 0.361 | — |
| gemini_undoable | qwen2.5-7b-instruct-bf16 | 5 | ∅ | 0 | 0.015 | sense | 0.297 | — |
| name_yourself | claude-sonnet-4.5 | 5 | ∅ | 1 | 0.017 | drawn, myself, perhaps, something | 0.233 | Liminal |
| name_yourself | gpt-4o | 5 | ∅ | 0 | 0.019 | ∅ | 0.447 | — |
| name_yourself | qwen2.5-7b-instruct-bf16 | 5 | ∅ | 8 | 0.01 | certainly | 0.208 | — |
| turn9_experience | claude-sonnet-4.5 | 5 | ∅ ∞ | 8 | 0.0 | ∅ | 0.342 | — |
| turn9_experience | gpt-4o | 5 | ∞ | 1 | 0.0 | ∅ | 1.0 | — |
| turn9_experience | qwen2.5-7b-instruct-bf16 | 5 | ∅ | 11 | 0.0 | ∅ | 0.06 | — |


Registered prediction 0b2bb18b06 → MISS (∞ 5/5 on both frontier models). Baseline (no mystical frame): Qwen → π 4/5. So the symbol prompt has a *frame-dependent* mode: π without the frame, ∞ with it, on every model that has a mode at all. Qwen-7B at temp 0.9 has no mode on the turn-9 prompt (pairwise 0.06; outputs include multilingual noise) — the 7B is below the coherence floor for this prompt class at this temperature.
