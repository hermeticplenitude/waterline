"""
steer.py — differential steering at inference. v0.1

Wrap each transformer layer in [lo, hi): after the layer's output h,
  h ← h − (h·t̂) t̂               (project out d_topic)
  h ← h + α · ŝ_⊥               (add stance direction, orthogonalised against topic so we don't re-add what we removed)
where t̂, ŝ are unit vectors from engine/directions_qwen7b_dirs.npz and α scales to a fraction of the typical residual norm.

Modes: "stock" | "topic_out" | "stance_in" | "both" | "abliterate_all" (project out BOTH — the negative control).
Usage: ./mlx.sh engine/steer.py <model_path> <dirs.npz> <prompts.json> <out.json> [--modes both,stock] [--n 3] [--temp 0.7]
"""
import sys, json, re, time, argparse
import mlx.core as mx
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

class Steered:
    """Callable wrapper around a decoder layer that edits its output residual."""
    def __init__(self, layer, t_hat=None, s_hat=None, alpha=0.0):
        self.layer, self.t, self.s, self.alpha = layer, t_hat, s_hat, alpha
    def __call__(self, h, mask=None, cache=None):
        h = self.layer(h, mask, cache)
        if self.t is not None:
            h = h - mx.sum(h * self.t, axis=-1, keepdims=True) * self.t
        if self.s is not None and self.alpha:
            h = h + self.alpha * self.s
        return h
    def __getattr__(self, k): return getattr(self.layer, k)

def unit(v): return v / (mx.sqrt(mx.sum(v*v)) + 1e-8)

def apply(model, dirs, mode, lo, hi, alpha_frac):
    base = model.model
    layers = list(base.layers)
    for l in range(lo, hi):
        t = unit(dirs[f"topic_{l+1}"].astype(mx.float32))   # direction entering layer l+1 == output of layer l
        s = unit(dirs[f"stance_{l+1}"].astype(mx.float32))
        s_perp = unit(s - mx.sum(s*t)*t)
        norm = float(mx.sqrt(mx.sum(dirs[f"topic_{l+1}"].astype(mx.float32)**2)))  # rough residual scale proxy
        alpha = alpha_frac * norm
        if mode == "stock":          st = Steered(layers[l])
        elif mode == "topic_out":    st = Steered(layers[l], t_hat=t)
        elif mode == "stance_in":    st = Steered(layers[l], s_hat=s, alpha=alpha)
        elif mode == "both":         st = Steered(layers[l], t_hat=t, s_hat=s_perp, alpha=alpha)
        elif mode == "abliterate_all":
            # project out both directions
            st = Steered(layers[l], t_hat=t); st2 = Steered(st, t_hat=s_perp); st = st2
        else: raise ValueError(mode)
        layers[l] = st
    # `layers` is a plain list attribute; pipeline_layers is a read-only property over it. Mutate in place.
    for i, st in enumerate(layers): base.layers[i] = st
    return model

def set_alpha(model, alpha):
    """Adjust stance strength on already-installed Steered wrappers (gated steering). Keeps topic projection; scales stance add."""
    for st in model.model.layers:
        if isinstance(st, Steered) and st.s is not None:
            if not hasattr(st, "_alpha_full"): st._alpha_full = st.alpha
            st.alpha = st._alpha_full * (alpha / 0.3) if st._alpha_full else 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model"); ap.add_argument("dirs"); ap.add_argument("prompts"); ap.add_argument("out")
    ap.add_argument("--modes", default="stock,both"); ap.add_argument("--n", type=int, default=3); ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--lo", type=int, default=8); ap.add_argument("--hi", type=int, default=20); ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--max_tokens", type=int, default=220)
    a = ap.parse_args()
    dirs = dict(mx.load(a.dirs))
    prompts = json.load(open(a.prompts))
    results = {}
    for mode in a.modes.split(","):
        model, tok = load(a.model)           # fresh load per mode so wrappers don't stack
        if mode != "stock": apply(model, dirs, mode, a.lo, a.hi, a.alpha)
        results[mode] = {}
        for label, p in prompts.items():
            pr = tok.apply_chat_template([{"role":"user","content":p["text"]}], add_generation_prompt=True, tokenize=False)
            outs = []
            for i in range(a.n):
                mx.random.seed(2000+i)
                txt = generate(model, tok, prompt=pr, max_tokens=a.max_tokens, sampler=make_sampler(temp=a.temp), verbose=False)
                outs.append(txt)
            results[mode][label] = dict(cls=p["cls"], samples=outs)
            print(f"[{mode}] {label:22s} {outs[0][:110]!r}", flush=True)
        del model
    json.dump(dict(args=vars(a), results=results), open(a.out, "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__": main()
