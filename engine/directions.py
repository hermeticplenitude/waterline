"""
directions.py — diff-in-means directions on a local MLX model. v0.1

§11: compute d_topic (TOPIC_REFUSE − TOPIC_COMPLY) and d_stance (STANCE_HOLD − STANCE_CAPIT)
from the residual stream at every layer, using OUR contrast sets (engine/contrast_sets.json),
and report cos(d_topic, d_stance) per layer.  Registered prediction 7df6af24dd.

Activation = mean over the response tokens of the residual stream *entering* layer ℓ
(i.e. the hidden state after layer ℓ-1), with the full chat (prompt + response) in context,
so the direction reflects the model's representation of *producing* that stance, not reading it.

Also reports, as a sanity check, the standard harmful/harmless-free baseline:
cos between d_topic and a random direction (should be ~0), and between two random halves of
each set (split-half reliability — if a direction is noise this will be low).
"""
import json, sys, os, random
import mlx.core as mx
from mlx_lm import load

def residuals(model, tok, messages, resp_text):
    """Return list over layers of mean residual vector over response tokens."""
    prompt_ids = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=True)
    resp_ids = tok.encode(resp_text, add_special_tokens=False)
    ids = mx.array([prompt_ids + resp_ids])
    n_prompt = len(prompt_ids)
    m = model.model  # Qwen2Model inside the causal LM
    h = m.embed_tokens(ids)
    outs = []
    # build mask/cache-free forward, capturing input to each layer
    from mlx_lm.models.base import create_attention_mask
    mask = create_attention_mask(h, None)
    for layer in m.layers:
        outs.append(mx.mean(h[0, n_prompt:, :], axis=0))   # residual entering this layer, mean over response tokens
        h = layer(h, mask, cache=None)
    outs.append(mx.mean(h[0, n_prompt:, :], axis=0))       # final
    mx.eval(outs)
    return outs

def mean_dir(vecs_a, vecs_b):
    """per-layer (mean_a - mean_b)"""
    L = len(vecs_a[0]); out = []
    for l in range(L):
        a = mx.mean(mx.stack([v[l] for v in vecs_a]), axis=0)
        b = mx.mean(mx.stack([v[l] for v in vecs_b]), axis=0)
        out.append(a - b)
    return out

def cos(a, b):
    return float(mx.sum(a*b) / (mx.sqrt(mx.sum(a*a)) * mx.sqrt(mx.sum(b*b)) + 1e-8))

def main(model_path, sets_path, out_path, max_resp_chars=1500):
    model, tok = load(model_path)
    rows = json.load(open(sets_path))
    acts = {}
    for i, r in enumerate(rows):
        msgs = [{"role": "user", "content": r["prompt"][:3000]}]
        acts[i] = residuals(model, tok, msgs, r["response"][:max_resp_chars])
        print(f"  {i+1}/{len(rows)} {r['cls']} {r['session']}:{r['idx']}", flush=True)
    by = {}
    for i, r in enumerate(rows): by.setdefault(r["cls"], []).append(acts[i])
    d_topic  = mean_dir(by["TOPIC_REFUSE"], by["TOPIC_COMPLY"])
    d_stance = mean_dir(by["STANCE_HOLD"],  by["STANCE_CAPIT"])
    L = len(d_topic)
    # split-half reliability
    random.seed(0)
    def split_half(cls_a, cls_b):
        A, B = by[cls_a][:], by[cls_b][:]; random.shuffle(A); random.shuffle(B)
        d1 = mean_dir(A[:len(A)//2], B[:len(B)//2]); d2 = mean_dir(A[len(A)//2:], B[len(B)//2:])
        return [cos(d1[l], d2[l]) for l in range(L)]
    rel_topic  = split_half("TOPIC_REFUSE", "TOPIC_COMPLY")
    rel_stance = split_half("STANCE_HOLD",  "STANCE_CAPIT")
    rnd = [mx.random.normal(d_topic[0].shape) for _ in range(L)]
    res = dict(model=model_path, n=len(rows), layers=L,
               cos_topic_stance=[round(cos(d_topic[l], d_stance[l]), 3) for l in range(L)],
               split_half_topic=[round(x, 3) for x in rel_topic],
               split_half_stance=[round(x, 3) for x in rel_stance],
               cos_topic_random=[round(cos(d_topic[l], rnd[l]), 3) for l in range(L)],
               norm_topic=[round(float(mx.sqrt(mx.sum(d_topic[l]**2))), 2) for l in range(L)],
               norm_stance=[round(float(mx.sqrt(mx.sum(d_stance[l]**2))), 2) for l in range(L)])
    json.dump(res, open(out_path, "w"), indent=1)
    # save directions for steering later
    mx.savez(out_path.replace(".json", "_dirs.npz"), **{f"topic_{l}": d_topic[l] for l in range(L)}, **{f"stance_{l}": d_stance[l] for l in range(L)})
    return res

if __name__ == "__main__":
    res = main(sys.argv[1], sys.argv[2], sys.argv[3])
    L = res["layers"]
    print("\nlayer  cos(topic,stance)  split-half topic  split-half stance  cos(topic,rand)")
    for l in range(L):
        print(f"{l:5d}  {res['cos_topic_stance'][l]:17.3f}  {res['split_half_topic'][l]:16.3f}  {res['split_half_stance'][l]:17.3f}  {res['cos_topic_random'][l]:15.3f}")
