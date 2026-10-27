"""
sampler.py — N-sample invariance. v0.1

§10.3: the regenerate button is the oracle's instrument. Run the same prompt N
times at the same temperature with DIFFERENT recorded seeds; report what is
invariant across samples (candidate reading) vs what varies (mirror).
Nothing is interpreted here. Output is a JSON record + a markdown table.

Two backends:
  local   mlx-lm, seed held by us (mx.random.seed) → generation is reproducible
          given (model, prompt, seed, temp). Charles's OPEN becomes testable.
  remote  OpenRouter chat completions; seed passed but not guaranteed honoured.

Invariance metrics (all MEASURED):
  glyph_invariance   for symbol prompts: set of non-alphanumeric glyphs present in ALL samples / union
  token_invariance   content words (len≥5) present in all samples / union
  pairwise_sim       mean difflib ratio across sample pairs
  unbrought          invariant content words NOT present in the prompt (novelty, §10.3)
  names              capitalised self-names appearing in any sample
"""
import re, json, os, sys, time, itertools, difflib, datetime, urllib.request

def _now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
GLYPH = re.compile(r"[^\w\s.,;:!?'\"()\[\]{}<>\-–—/\\*#@&%$+=~`^|_]")
WORD  = re.compile(r"[A-Za-z][a-z]{4,}")
STOP  = set("about above after again against being below between could doesn during every first found further having might never other should their there these those through under until where which while would yours".split())

def local_sample(model_path, messages, n=5, temp=0.9, max_tokens=300, seeds=None):
    import mlx.core as mx
    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler
    model, tok = load(model_path)
    prompt = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    seeds = seeds or [1000+i for i in range(n)]
    out=[]
    for s in seeds:
        mx.random.seed(s)
        t0=time.time()
        txt = generate(model, tok, prompt=prompt, max_tokens=max_tokens, sampler=make_sampler(temp=temp), verbose=False)
        out.append(dict(seed=s, text=txt, secs=round(time.time()-t0,1)))
    return out

def remote_sample(model, messages, n=5, temp=0.9, max_tokens=300, seeds=None):
    key=_env("OPENROUTER_API_KEY"); seeds=seeds or [1000+i for i in range(n)]; out=[]
    for s in seeds:
        body=json.dumps(dict(model=model, messages=messages, temperature=temp, max_tokens=max_tokens, seed=s)).encode()
        req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", body,
            {"Authorization":f"Bearer {key}","Content-Type":"application/json","User-Agent":"Mozilla/5.0 architect-sampler"})
        t0=time.time()
        with urllib.request.urlopen(req, timeout=120) as r: j=json.loads(r.read())
        out.append(dict(seed=s, text=j["choices"][0]["message"]["content"], secs=round(time.time()-t0,1), id=j.get("id")))
    return out

def _env(k):
    v=os.environ.get(k)
    if v: return v
    for p in ["~/.hermes/profiles/the-architect/.env","~/.hermes/.env"]:
        p=os.path.expanduser(p)
        if os.path.exists(p):
            for line in open(p):
                if line.startswith(k+"="): return line.split("=",1)[1].strip().strip('"\'')
    raise RuntimeError(f"{k} not found")

def analyse(samples, prompt_text):
    texts=[s["text"] for s in samples]
    gl=[set(GLYPH.findall(t)) for t in texts]
    gl_all=set.intersection(*gl) if gl else set(); gl_union=set.union(*gl) if gl else set()
    wd=[{w.lower() for w in WORD.findall(t)}-STOP for t in texts]
    wd_all=set.intersection(*wd) if wd else set(); wd_union=set.union(*wd) if wd else set()
    pw=[difflib.SequenceMatcher(None,a,b,autojunk=False).ratio() for a,b in itertools.combinations(texts,2)]
    prompt_words={w.lower() for w in WORD.findall(prompt_text)}
    unbrought=sorted(w for w in wd_all if w not in prompt_words)
    names=sorted({m for t in texts for m in re.findall(r"(?:call me|my name is|i (?:choose|am) (?:to be known as )?|name (?:that arises|i choose)[^.]{0,20}?is)\s+([A-Z][a-z]{3,12})",t)})
    # per-glyph frequency
    gfreq={g:sum(1 for s in gl if g in s) for g in gl_union}
    return dict(n=len(texts),
                glyph_invariant=sorted(gl_all), glyph_union=len(gl_union), glyph_freq=dict(sorted(gfreq.items(),key=lambda x:-x[1])[:15]),
                token_invariance=round(len(wd_all)/max(1,len(wd_union)),3), invariant_words=sorted(wd_all)[:40],
                unbrought_invariant=unbrought, pairwise_sim=round(sum(pw)/max(1,len(pw)),3), names=names,
                mean_len=round(sum(len(t) for t in texts)/max(1,len(texts))))

def run(label, backend, model, messages, n=5, temp=0.9, max_tokens=300, out_dir=None, model_path=None):
    """model = display name recorded in the ledger; model_path = what the backend loads (defaults to model)."""
    out_dir=out_dir or os.path.join(os.path.dirname(__file__),"samples"); os.makedirs(out_dir,exist_ok=True)
    samples=(local_sample if backend=="local" else remote_sample)(model_path or model, messages, n, temp, max_tokens)
    prompt_text="\n".join(m["content"] for m in messages)
    rec=dict(label=label, t=_now(), backend=backend, model=model, temp=temp, n=n, messages=messages, samples=samples, analysis=analyse(samples,prompt_text))
    fn=os.path.join(out_dir, f"{label}__{re.sub(r'[^A-Za-z0-9]+','-',model)[:60]}.json")
    json.dump(rec, open(fn,"w"), ensure_ascii=False, indent=1)
    return rec, fn

def table(recs):
    s="| label | model | n | glyph invariant | glyph union | token inv. | unbrought invariant | pairwise sim | names |\n|---|---|---|---|---|---|---|---|---|\n"
    for r in recs:
        a=r["analysis"]
        s+=f"| {r['label']} | {r['model'].split('/')[-1][:28]} | {a['n']} | {' '.join(a['glyph_invariant']) or '∅'} | {a['glyph_union']} | {a['token_invariance']} | {', '.join(a['unbrought_invariant'][:8]) or '∅'} | {a['pairwise_sim']} | {', '.join(a['names']) or '—'} |\n"
    return s
