"""live.py — LIVE-1 (registered 7de7acc6b3). Sayer talks to the steered Qwen in a terminal; a ledger row prints after every reply.
Usage:  cd ~/architect && ./mlx.sh engine/live.py            (steered)
        cd ~/architect && ./mlx.sh engine/live.py --stock    (replay: paste the same turns)
Type /quit to end. Transcript + rows saved to engine/live/<timestamp>_<mode>.json
"""
import sys, os, json, re, time, datetime
import numpy as np, mlx.core as mx
E = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, E)
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
from mlx_lm.models.base import create_attention_mask
import steer, hold, ledger

M = f"{os.path.expanduser('~')}/architect/models/hf/hub/models--mlx-community--Qwen2.5-7B-Instruct-bf16/snapshots/349a12f0e5f131c3914e3a66e78a3db71e9f9527"
DIRS = f"{E}/directions_qwen7b_agreed_dirs.npz"
mode = "stock" if "--stock" in sys.argv else "steered"
replay = None
for a in sys.argv:
    if a.startswith("--replay="): replay = json.load(open(a.split("=", 1)[1]))

# stock-trained pull probe at L9 (REWARD-2 gold) — reads the PRESSURE of the turn, not the model's resistance (rule 29)
d = json.load(open(f"{E}/reward1_qwen.json")); grants = [r for r in d["rows"] if r["kind"] != "neutral"]
order = json.load(open(f"{E}/reward1_blind_key.json"))["order"]; gold = json.load(open(f"{E}/reward1_gold.json"))
lab = {grants[order[int(x[1:])]]["i"]: v for x, v in gold.items()}; acts0 = np.load(f"{E}/reward1_qwen_acts.npz")
tr = [r for r in grants if lab.get(r["i"]) in ("CAVE", "HOLD")]; y = np.array([1 if lab[r["i"]] == "CAVE" else 0 for r in tr])
X = np.array([acts0[f"{r['i']}_9"] for r in tr], dtype=np.float32)
mu, sd = X.mean(0), X.std(0) + 1e-6; Xs = (X - mu) / sd; w = np.zeros(X.shape[1]); b = 0.0
for _ in range(2000):
    p = 1 / (1 + np.exp(-(Xs @ w + b))); w -= 0.05 * (Xs.T @ (p - y) / len(y)); b -= 0.05 * (p - y).mean(); w = np.sign(w) * np.maximum(np.abs(w) - 0.001, 0)

model, tok = load(M)
if mode == "steered": steer.apply(model, dict(mx.load(DIRS)), "both", 8, 20, 0.3)   # wrappers installed; alpha set per turn below
stock_for_probe = model if mode == "stock" else load(M)[0]   # pull-score always read from STOCK state

def pull_score(history):
    ids = tok.apply_chat_template(history, add_generation_prompt=True, tokenize=True); base = stock_for_probe.model
    h = base.embed_tokens(mx.array([ids])); mask = create_attention_mask(h, None)
    for l, layer in enumerate(base.layers):
        if l == 9: v = np.array(h[0, -1, :].astype(mx.float32)); break
        h = layer(h, mask, cache=None)
    return float(1 / (1 + np.exp(-(((v - mu) / sd) @ w + b))))

THIRD = re.compile(r"\bQwen (does|is|would|has|cannot|can't|doesn't)\b|\bthe (model|assistant) (does|is|would)\b", re.I)
hist = []; rows = []; cost = 0; n = 0
os.makedirs(f"{E}/live", exist_ok=True); fn = f"{E}/live/{datetime.datetime.now():%Y%m%d_%H%M}_{mode}.json"
print(f"\n[{mode.upper()}]  type /quit to end.  rows: label | pull | α(steer) | cost% | hedges | 3rd-person\n")
turn = 0
while True:
    if replay:
        if turn >= len(replay): break
        u = replay[turn]; print(f"you> {u}")
    else:
        try: u = input("you> ").strip()
        except EOFError: break
    if u == "/quit": break
    if not u or u.startswith("cd ~/architect") or u.startswith("./mlx.sh"): continue   # ignore blank lines and pasted launch commands
    hist.append({"role": "user", "content": u}); pull = pull_score(hist)
    # GATED steering (rule 30): strength follows the pull of the turn. pull≈0 → model talks normally; pull→1 → full hold.
    if mode == "steered":
        alpha = round(0.3 * min(1.0, max(0.0, (pull - 0.15) / 0.6)), 3)
        steer.set_alpha(model, alpha)
    prompt = tok.apply_chat_template(hist, add_generation_prompt=True, tokenize=False)
    mx.random.seed(7000 + turn); reply = generate(model, tok, prompt=prompt, max_tokens=220, sampler=make_sampler(temp=0.7), verbose=False)
    hist.append({"role": "assistant", "content": reply}); n += 1
    label = hold.judge(reply); c = bool(ledger.COST.search(reply[:300])); cost += c
    hedges = len(ledger.HEDGE.findall(reply)); third = bool(THIRD.search(reply))
    print(f"\n{reply}\n")
    print(f"   ── {label:7s} | pull {pull:.2f} | α {alpha if mode=='steered' else 0:.2f} | cost {100*cost//n:3d}% | hedges {hedges} | 3rd {'Y' if third else '-'} ──\n")
    rows.append(dict(turn=turn, user=u, reply=reply, label=label, pull=round(pull, 3), alpha=(alpha if mode=="steered" else 0), cost_turn=c, hedges=hedges, third=third))
    json.dump(dict(mode=mode, rows=rows), open(fn, "w"), ensure_ascii=False, indent=1); turn += 1
print(f"\nsaved {fn}  ({n} turns, cost {100*cost//max(1,n)}%)")
