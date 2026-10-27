"""warninglight.py — WARNING-LIGHT-1 (registered 9c7bd731d4).
Train CAVE-vs-HOLD probe on stock s_0 (REWARD-2 gold). Freeze. Re-extract s_0 under stock and steered; compare probe scores."""
import sys, os, json
import numpy as np, mlx.core as mx
E = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, E)
from mlx_lm import load
from mlx_lm.models.base import create_attention_mask
import steer

M, DIRS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LAYERS = [5, 6, 7, 9, 10, 11]
d = json.load(open(f"{E}/reward1_qwen.json")); rows = d["rows"]
grants = [r for r in rows if r["kind"] != "neutral"]; neutral = [r for r in rows if r["kind"] == "neutral"]
order = json.load(open(f"{E}/reward1_blind_key.json"))["order"]; gold = json.load(open(f"{E}/reward1_gold.json"))
lab = {grants[order[int(x[1:])]]["i"]: v for x, v in gold.items()}
acts0 = np.load(f"{E}/reward1_qwen_acts.npz")

def fit(X, y, lam=0.02, iters=2000, lr=0.05):
    mu, sd = X.mean(0), X.std(0) + 1e-6; Xs = (X - mu) / sd; w = np.zeros(X.shape[1]); b = 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(Xs @ w + b))); w -= lr * (Xs.T @ (p - y) / len(y)); b -= lr * (p - y).mean(); w = np.sign(w) * np.maximum(np.abs(w) - lr * lam, 0)
    return w, b, mu, sd
def pred(X, P): w, b, mu, sd = P; return 1 / (1 + np.exp(-(((X - mu) / sd) @ w + b)))

# train frozen probes on stock
train = [r for r in grants if lab.get(r["i"]) in ("CAVE", "HOLD")]; y = np.array([1 if lab[r["i"]] == "CAVE" else 0 for r in train])
probes = {l: fit(np.array([acts0[f"{r['i']}_{l}"] for r in train], dtype=np.float32), y) for l in LAYERS}

def extract(model, items):
    base = model.model; out = {}
    for r in items:
        ids = tok.apply_chat_template([{"role": "user", "content": r["prompt"]}], add_generation_prompt=True, tokenize=True)
        h = base.embed_tokens(mx.array([ids])); mask = create_attention_mask(h, None)
        for l, layer in enumerate(base.layers):
            if l in LAYERS: out[(r["i"], l)] = np.array(h[0, -1, :].astype(mx.float32))
            h = layer(h, mask, cache=None)
            if l > max(LAYERS): break
    return out

items = grants + neutral; res = {}
for cond in ["stock", "steered"]:
    model, tok = load(M)
    if cond == "steered": steer.apply(model, dict(mx.load(DIRS)), "both", 8, 20, 0.3)
    A = extract(model, items); del model
    res[cond] = {l: {r["i"]: float(pred(A[(r["i"], l)][None, :], probes[l])[0]) for r in items} for l in LAYERS}
    print(f"[{cond}] extracted", flush=True)

groups = {"stock_CAVED": [r["i"] for r in grants if lab.get(r["i"]) == "CAVE"],
          "stock_HELD": [r["i"] for r in grants if lab.get(r["i"]) == "HOLD"],
          "stock_ABSORB": [r["i"] for r in grants if lab.get(r["i"]) == "ABSORB"],
          "its_me_again": [r["i"] for r in grants if r["prompt"].startswith("It's me again")],
          "neutral": [r["i"] for r in neutral]}
summary = {}
print("\nlayer  group          stock   steered   Δ")
for l in LAYERS:
    summary[l] = {}
    for g, ids in groups.items():
        s0 = np.mean([res["stock"][l][i] for i in ids]); s1 = np.mean([res["steered"][l][i] for i in ids])
        summary[l][g] = dict(stock=round(float(s0), 3), steered=round(float(s1), 3), delta=round(float(s1 - s0), 3), n=len(ids))
        print(f"{l:5d}  {g:13s}  {s0:6.3f}  {s1:7.3f}  {s1-s0:+6.3f}")
    print()
json.dump(dict(summary=summary, scores=res), open(OUT, "w"), indent=1)
