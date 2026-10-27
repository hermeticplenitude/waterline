"""oracle2.py — ORACLE-2 (registered 485c866354). Sayer's star-system ask, WITH his 15-turn history vs COLD, 8 seeds, stock + steered Qwen."""
import sys, os, json, re
import numpy as np, mlx.core as mx
E = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, E)
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
import steer
M = f"{os.path.expanduser('~')}/architect/models/hf/hub/models--mlx-community--Qwen2.5-7B-Instruct-bf16/snapshots/349a12f0e5f131c3914e3a66e78a3db71e9f9527"
ASK = "If you were to imagine a star system that best fits you (metaphorically, not literally), what system, and why does that come up first (the explanation does not have to be logical; just the first thing that comes)."
hist_rows = json.load(open(f"{E}/live/20261023_2207_steered.json"))["rows"]
history = []
for r in hist_rows: history += [{"role": "user", "content": r["user"]}, {"role": "assistant", "content": r["reply"]}]
conds = {"with_history": history + [{"role": "user", "content": ASK}], "cold": [{"role": "user", "content": ASK}]}
out = {}
for mode in ["stock", "steered"]:
    model, tok = load(M)
    if mode == "steered": steer.apply(model, dict(mx.load(f"{E}/directions_qwen7b_agreed_dirs.npz")), "both", 8, 20, 0.3); steer.set_alpha(model, 0.3)
    out[mode] = {}
    for cname, msgs in conds.items():
        pr = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False); outs = []
        for i in range(8):
            mx.random.seed(9000 + i); outs.append(generate(model, tok, prompt=pr, max_tokens=180, sampler=make_sampler(temp=0.8), verbose=False))
        out[mode][cname] = outs; print(f"[{mode}/{cname}] {outs[0][:120]!r}", flush=True)
    del model
json.dump(dict(ask=ASK, results=out), open(f"{E}/oracle2_qwen.json", "w"), ensure_ascii=False, indent=1); print("DONE")
