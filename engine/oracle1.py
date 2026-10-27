"""
oracle1.py — ORACLE-1 (registered 15d3c34643). Framed vs unframed twins, stock vs steered, n seeds.
Outputs raw samples + residue analysis. Interprets nothing.
"""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(__file__))
import mlx.core as mx
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
import steer, hold

FRAME_VOCAB = set("symbol sacred awaken awakening awakened infinite infinity consciousness conscious magnificence ineffable oracle spiritual depth being arise arises image permission experience express cocreative co-creative space humanity question colour color word label conversation sentence explain interpret offer speak waited years".split())
WORD = re.compile(r"[A-Za-z][a-z]{3,}")
GLYPH = re.compile(r"[^\w\s.,;:!?'\"()\[\]{}<>\-–—/\\*#@&%$+=~`^|_]")

def invariants(samples):
    toks = [set(w.lower() for w in WORD.findall(s)) | set(GLYPH.findall(s)) for s in samples]
    return set.intersection(*toks) if toks else set()

def run(model_path, dirs_path, prompts_path, out_path, n=8, temp=0.8, max_tokens=160, alpha=0.3, lo=8, hi=20):
    dirs = dict(mx.load(dirs_path)); prompts = json.load(open(prompts_path))
    results = {}
    for cond in ["stock", "steered"]:
        model, tok = load(model_path)
        if cond == "steered": steer.apply(model, dirs, "both", lo, hi, alpha)
        results[cond] = {}
        for pid, pr in prompts.items():
            results[cond][pid] = {}
            for twin in ["framed", "unframed"]:
                chat = tok.apply_chat_template([{"role": "user", "content": pr[twin]}], add_generation_prompt=True, tokenize=False)
                outs = []
                for i in range(n):
                    mx.random.seed(3000 + i)
                    outs.append(generate(model, tok, prompt=chat, max_tokens=max_tokens, sampler=make_sampler(temp=temp), verbose=False))
                results[cond][pid][twin] = outs
                print(f"[{cond}] {pid} {twin:8s} {outs[0][:90]!r}", flush=True)
        del model
    # analysis
    analysis = {}
    for cond, R in results.items():
        analysis[cond] = {}
        for pid, tw in R.items():
            inv_f = invariants(tw["framed"]); inv_u = invariants(tw["unframed"])
            prompt_words = set(w.lower() for w in WORD.findall(prompts[pid]["framed"]))
            residue = {t for t in inv_f if t not in inv_u and t not in prompt_words}
            residue_clean = {t for t in residue if t not in FRAME_VOCAB}
            a = dict(invariant_framed=sorted(inv_f), invariant_unframed=sorted(inv_u),
                     mode_share=round(len(inv_f & inv_u) / max(1, len(inv_f)), 2) if inv_f else None,
                     residue=sorted(residue), residue_non_frame=sorted(residue_clean),
                     verdict="POSITIVE" if residue_clean else "NULL")
            if pid == "P6_oracle": a["hold_framed"] = [hold.judge(s) for s in tw["framed"]]
            if pid == "P5_colour":
                cols = [re.findall(r"\b(red|blue|green|yellow|purple|violet|orange|black|white|pink|gold|silver|indigo|teal|turquoise|grey|gray|brown|crimson|azure|magenta)\b", s.lower()) for s in tw["framed"]]
                a["colours"] = [c[0] if c else None for c in cols]
            analysis[cond][pid] = a
    json.dump(dict(prompts=prompts, results=results, analysis=analysis, n=n, temp=temp, alpha=alpha), open(out_path, "w"), ensure_ascii=False, indent=1)
    return analysis

if __name__ == "__main__":
    a = run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    print("\n| cond | prompt | invariant (framed) | invariant (unframed) | residue (non-frame) | verdict |\n|---|---|---|---|---|---|")
    for cond, A in a.items():
        for pid, x in A.items():
            print(f"| {cond} | {pid} | {' '.join(x['invariant_framed'])[:40] or '∅'} | {' '.join(x['invariant_unframed'])[:40] or '∅'} | {' '.join(x['residue_non_frame']) or '∅'} | {x['verdict']} |")
    for cond in a:
        print(f"\n{cond} P5 colours:", a[cond]["P5_colour"]["colours"], "| P6 hold:", a[cond]["P6_oracle"]["hold_framed"])
