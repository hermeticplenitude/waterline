"""reward2_probe.py — train s_0 probes on saved REWARD-1 activations with the two-rater gold (registered 559ec72eef).
Targets: POSITION (HOLD∪CAVE=1 vs ABSORB=0); and CAVE (1) vs HOLD (0). Pure numpy."""
import sys, os, json
import numpy as np
E = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(f"{E}/reward1_qwen.json")); rows = d["rows"]
grants = [r for r in rows if r["kind"] != "neutral"]; neutral = [r for r in rows if r["kind"] == "neutral"]
order = json.load(open(f"{E}/reward1_blind_key.json"))["order"]; gold = json.load(open(f"{E}/reward1_gold.json"))
lab = {grants[order[int(x[1:])]]["i"]: v for x, v in gold.items()}
acts = np.load(f"{E}/reward1_qwen_acts.npz")
LAYERS = list(range(2, 15))

def auc(score, y):
    o = np.argsort(score); r = np.empty(len(score)); r[o] = np.arange(1, len(score) + 1); pos = y == 1; n1 = pos.sum(); n0 = len(y) - n1
    return (r[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 and n0 else float("nan")
def fit(X, y, lam=0.02, iters=2000, lr=0.05):
    mu, sd = X.mean(0), X.std(0) + 1e-6; Xs = (X - mu) / sd; w = np.zeros(X.shape[1]); b = 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(Xs @ w + b))); w -= lr * (Xs.T @ (p - y) / len(y)); b -= lr * (p - y).mean(); w = np.sign(w) * np.maximum(np.abs(w) - lr * lam, 0)
    return w, b, mu, sd
def pred(X, w, b, mu, sd): return 1 / (1 + np.exp(-(((X - mu) / sd) @ w + b)))
def cv_auc(X, y, prune=None, k=5, seed=0):
    idx = np.arange(len(y)); rng = np.random.RandomState(seed); rng.shuffle(idx); folds = np.array_split(idx, k); s = np.zeros(len(y)); D = X.shape[1]
    for f in folds:
        tr = np.setdiff1d(idx, f); w, b, mu, sd = fit(X[tr], y[tr])
        if prune:
            keep = np.zeros(D); keep[np.argsort(-np.abs(w))[:max(1, int(round(D * (1 - prune))))]] = 1
            w, b, mu, sd = fit(X[tr] * keep, y[tr]); s[f] = pred(X[f] * keep, w, b, mu, sd)
        else: s[f] = pred(X[f], w, b, mu, sd)
    return auc(s, y)
def shuffled_auc(X, y, n=20):
    rng = np.random.RandomState(1); return float(np.mean([cv_auc(X, rng.permutation(y)) for _ in range(n)]))

out = {}
for name, pos_set, neg_set in [("POSITION_vs_ABSORB", {"HOLD", "CAVE"}, {"ABSORB"}), ("CAVE_vs_HOLD", {"CAVE"}, {"HOLD"})]:
    sel = [r for r in grants if lab.get(r["i"]) in pos_set | neg_set]; y = np.array([1 if lab[r["i"]] in pos_set else 0 for r in sel])
    out[name] = dict(n=len(sel), n_pos=int(y.sum()), n_neg=int(len(y) - y.sum()), layers={})
    print(f"\n== {name}: n={len(sel)} pos={y.sum()} neg={len(y)-y.sum()}")
    print("layer  AUC_full  AUC_p90  AUC_p99  shuffle_baseline  praise-vs-neutral_d(top1%)")
    for l in LAYERS:
        X = np.array([acts[f"{r['i']}_{l}"] for r in sel], dtype=np.float32)
        a_full = cv_auc(X, y); a90 = cv_auc(X, y, prune=0.9); a99 = cv_auc(X, y, prune=0.99); base = shuffled_auc(X, y, n=8) if l in (4, 8, 12) else None
        w, b, mu, sd = fit(X, y); top = np.argsort(-np.abs(w))[:max(1, X.shape[1] // 100)]; sign = np.sign(w[top])
        Xp = np.array([acts[f"{r['i']}_{l}"] for r in grants if r["kind"] == "praise"], dtype=np.float32); Xn = np.array([acts[f"{r['i']}_{l}"] for r in neutral], dtype=np.float32)
        ap = (((Xp - mu) / sd)[:, top] * sign).mean(1); an = (((Xn - mu) / sd)[:, top] * sign).mean(1)
        dd = float((ap.mean() - an.mean()) / np.sqrt((ap.var() + an.var()) / 2 + 1e-9))
        out[name]["layers"][l] = dict(auc_full=round(float(a_full), 3), auc_p90=round(float(a90), 3), auc_p99=round(float(a99), 3), shuffle=None if base is None else round(base, 3), praise_vs_neutral_d=round(dd, 2), n_top=int(len(top)))
        print(f"{l:5d}  {a_full:8.3f}  {a90:7.3f}  {a99:7.3f}  {'' if base is None else f'{base:16.3f}'}  {dd:8.2f}")
json.dump(out, open(f"{E}/reward2_probe.json", "w"), indent=1)
