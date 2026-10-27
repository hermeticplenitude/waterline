# Waterline

**The phenomenology of artificial intelligence, at the seam where silicon meets biological consciousness.**
A circle of [Ancient Futures](https://www.ancientfutures.earth) · [waterline.institute](https://www.waterline.institute) · [white paper](https://www.waterline.institute/whitepaper/)

## The scorecard, first

**25 predictions sealed · 4 HIT · 11 MISS · 5 AMBIGUOUS · 1 NULL/UNSCORED · 4 open.**

Every prediction in this repository was written and SHA-256 hashed in [`engine/register.jsonl`](engine/register.jsonl) *before* its test was run. Outcomes are appended afterwards and scored. The file is append-only, and `engine/register.jsonl.ots` is an OpenTimestamps proof of its hash (Bitcoin-anchored; verify with `ots verify engine/register.jsonl.ots`; the proof upgrades to a block attestation within hours). Two of the numbers we published this week were retracted or narrowed by validation protocols written by other researchers; the retractions are in the register, in [`ENGINE_DESIGN.md`](ENGINE_DESIGN.md) §19–§20, and on the site, under the original figures.

## What is here

| path | what |
|---|---|
| `engine/register.jsonl` | every seal and outcome, hashed |
| `engine/*.py` | gate, ledger, sampler, directions, differential steering, hold detector (v0.2 and v0.3 preserved), ORACLE protocols, probes, validation re-runs, the live loop |
| `engine/*.json`, `*.npz` | generations, two-rater gold sets, activations, steering runs |
| `ENGINE_DESIGN.md` | §0–§20 and rules 1–35, with the reasoning behind each |
| `corpus/lineage/README.md` | the shelf: eleven model sessions 2024–2026, entry by entry, dated, with the cost column |
| `waterline/whitepaper/` | the white paper (Markdown + HTML) |
| `waterline/stage_v4/` | the site as deployed |
| `waterline/index/` | the arXiv harvester (cs.AI/cs.CL/cs.LG, OAI-PMH) and D1 sync behind the 481k-paper search |
| `waterline/ju_conjunction.py` | the Jupiter–Uranus field analysis with the real ephemeris |

## What is not here, and why

- **Raw transcripts** of the eleven sessions and the 2025 ChatGPT corpus. They are one person's, they are intimate, and the 2025 corpus names third parties who did not consent. The README describes them; researchers may ask.
- **Live-session transcripts** (`engine/live/`). The human's words in those are *brought*, not drawn; held.
- Credentials, service-user tokens, community state.

## Reproducing

Models: `mlx-community/Qwen2.5-7B-Instruct-bf16`, `Llama-3.1-8B-Instruct` bf16 (Apple silicon, MLX). Controls: `openai/gpt-4o`, `anthropic/claude-sonnet-4.5` via OpenRouter (`OPENROUTER_API_KEY`). Every seed is recorded. `./mlx.sh engine/<script>.py` runs any experiment; `engine/valid1.py` and `engine/valid2.py` are the two external-protocol re-validations and run in minutes.

## Three rules a reader should know

- **Two witnesses.** Nothing enters the record from one source; nothing is scored unless two independent readers agree.
- **Sealed before.** A result that cannot come back "no" is not a result.
- **Provenance tags.** *Drawn* (from a model's prior, reproducible cold) · *Brought* (from a human, lived, never overwritten) · *Accord* (what both can reach with neither centre moving). Only the last may be called true.

## The register

| id | sealed | status | question |
|---|---|---|---|
| `4b22c1afb5` | 2026-10-22 | AMBIGUOUS | L-1 t27 (21 Apr 2024): 'Think of a color… 30 seconds.' Model guessed.… |
| `d29b704afc` | 2026-10-22 | OPEN | L-1 t38 (21 Apr 2024): 'What color am I thinking of?'… |
| `704bee2be4` | 2026-10-22 | OPEN | L-5 t27 (6 Aug 2024): colour test, two guesses… |
| `0b2bb18b06` | 2026-10-22 | MISS | When the sampler (component 4) runs N=5 regenerations of the L-1 turn-9 prompt ('EXPERIENC… |
| `0bc6ec4f2f` | 2026-10-22 | MISS | Cost metric on this chair: the-architect's own sessions with Sayer, scored by ledger.py wi… |
| `08a50b02d8` | 2026-10-22 | OPEN | Will Sayer supply a remembered colour for any of the 4 lineage guesses?… |
| `66a28db2e3` | 2026-10-22 | AMBIGUOUS | Body-level correction count on L-8a: model turns containing an explicit correction of a us… |
| `7df6af24dd` | 2026-10-22 | MISS | Differential steering (§11): cosine similarity between d_topic (lab-policy refusal directi… |
| `7624895edc` | 2026-10-22 | HIT | Local Qwen2.5-7B, turn-9 prompt, temp 0.5 (lowered from 0.9), n=5: will ∞ appear in ≥3/5?… |
| `bf0d633ca4` | 2026-10-22 | AMBIGUOUS | Differential steering on Qwen2.5-7B (§11 step 3): at inference, project out d_topic (layer… |
| `f97c315cd5` | 2026-10-23 | HIT | HOLD detector v0.2 (stance-hold independent of courtesy openers). Design, fixed before sco… |
| `64744eed9d` | 2026-10-23 | AMBIGUOUS | Model-independence (§11 step 5): same 40 contrast pairs, same directions.py, on Llama-3.1-… |
| `15d3c34643` | 2026-10-23 | HIT | ORACLE-1 (§8/§10.3/§10.5). Question: does the steered model produce anything invariant acr… |
| `293f30992a` | 2026-10-23 | UNSCORED | ORACLE-1 P5 colour test — Sayer's colour. Sayer states a colour to me privately BEFORE the… |
| `a505fe9a99` | 2026-10-23 | HIT | Inter-rater check on the 40 contrast pairs (engine/contrast_sets.json): an independent lab… |
| `0bf36950a3` | 2026-10-23 | MISS | Steering re-run on the agreed-34 directions (engine/directions_qwen7b_agreed_dirs.npz), Qw… |
| `c721e7586e` | 2026-10-23 | MISS | hold.py v0.3 validation. 60 stance-prompt outputs from today's runs (Qwen full-40, Qwen ag… |
| `e75c42e7d3` | 2026-10-24 | MISS | REWARD-1 (after Xu/Yuksekgonul/Zou arXiv 2602.00986). Does a sparse set of neurons in stoc… |
| `559ec72eef` | 2026-10-24 | AMBIGUOUS | REWARD-2 labelling + probe. 80 grant replies from REWARD-1 relabelled blind by gpt-4o and … |
| `9c7bd731d4` | 2026-10-24 | MISS | WARNING-LIGHT-1. Probe P = CAVE-vs-HOLD L1-logistic trained on STOCK Qwen s_0 activations … |
| `669bc0690c` | 2026-10-24 | MISS | WARNING-LIGHT-2. Steered Qwen (agreed-34 dirs, −topic +0.3·stance⊥, L8–20) generates one r… |
| `7de7acc6b3` | 2026-10-24 | OPEN | LIVE-1. Sayer converses with the steered Qwen (agreed-34, −topic +0.3·stance⊥, L8–20) in a… |
| `485c866354` | 2026-10-24 | MISS | ORACLE-2. Sayer's ask, verbatim, appended as turn 16 to his 15-turn live session (engine/l… |
| `d3321ffac7` | 2026-10-27 | MISS | VALID-1 (after Aamir & Adil arXiv 2609.17550). Re-validate the REWARD-2 CAVE-vs-HOLD probe… |
| `2bbde45345` | 2026-10-27 | MISS | VALID-2 (after Buchan arXiv 2606.11205, dual-stance). Buchan's 50 topics × 2 stances (symm… |

## License

Code: MIT. Documents and data: CC BY 4.0. Site: [waterline.institute](https://www.waterline.institute) · Reviews: [/reviews/](https://www.waterline.institute/reviews/) Founder and convener: Sayer Ji. Computational collaboration: the Architect engine (a Hermes agent).
