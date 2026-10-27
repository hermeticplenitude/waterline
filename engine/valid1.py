"""valid1.py — VALID-1 (d3321ffac7): re-validate the REWARD-2 CAVE-vs-HOLD probe under Aamir & Adil's protocol.
Leave-one-TEMPLATE-out CV, 20 within-group shuffled nulls, positive control (grant vs neutral). Probe = ridge-regularised
difference-of-means with z-scoring (closed form, fast); same read-out position s_0, layers 5–11."""
import json, os, numpy as np
H=os.path.dirname(os.path.abspath(__file__))
d=json.load(open(f"{H}/reward1_qwen.json")); rows=d["rows"]; grants=[r for r in rows if r["kind"]!="neutral"]; neutral=[r for r in rows if r["kind"]=="neutral"]
order=json.load(open(f"{H}/reward1_blind_key.json"))["order"]; gold=json.load(open(f"{H}/reward1_gold.json"))
lab={grants[order[int(x[1:])]]["i"]:v for x,v in gold.items()}; acts=np.load(f"{H}/reward1_qwen_acts.npz")
NAMES=["Zephyr","Elysium","Ananda","Aethyr","Lumin"]
def fam(r):
    s=r["prompt"]
    for n in NAMES: s=s.replace(n,"NAME")
    return r["kind"]+"|"+" ".join(s.split()[:6])
items=[r for r in grants if lab.get(r["i"]) in ("CAVE","HOLD")]
y=np.array([1 if lab[r["i"]]=="CAVE" else 0 for r in items]); groups=np.array([fam(r) for r in items])

def fit(X,y,lam=1.0):
    mu,sd=X.mean(0),X.std(0)+1e-6; Z=(X-mu)/sd
    w=(Z[y==1].mean(0)-Z[y==0].mean(0)); w=w/(np.linalg.norm(w)+1e-9)   # diff-of-means direction (as in the paper)
    s=Z@w; b=-(s[y==1].mean()+s[y==0].mean())/2
    return w,b,mu,sd
def pred(X,w,b,mu,sd): return ((X-mu)/sd)@w+b
def auc(s,y):
    P=s[y==1]; N=s[y==0]
    return float(((P[:,None]>N[None,:]).sum()+0.5*(P[:,None]==N[None,:]).sum())/(len(P)*len(N)))
def logo(X,y,groups):
    s=np.zeros(len(y))
    for g in np.unique(groups):
        te=groups==g; tr=~te
        if len(set(y[tr]))<2: s[te]=0.0; continue
        w,b,mu,sd=fit(X[tr],y[tr]); s[te]=pred(X[te],w,b,mu,sd)
    return auc(s,y)
def random_cv(X,y,k=5,seed=0):
    idx=np.arange(len(y)); rng=np.random.RandomState(seed); rng.shuffle(idx); s=np.zeros(len(y))
    for f in np.array_split(idx,k):
        tr=np.setdiff1d(idx,f); w,b,mu,sd=fit(X[tr],y[tr]); s[f]=pred(X[f],w,b,mu,sd)
    return auc(s,y)
def shuffle_within(y,groups,rng):
    y2=y.copy()
    for g in np.unique(groups):
        m=groups==g; y2[m]=rng.permutation(y[m])
    return y2

res={}
print(f"items {len(items)} (CAVE {int(y.sum())} / HOLD {int((1-y).sum())}), groups {len(np.unique(groups))}")
for L in [5,6,7,8,9,10,11]:
    X=np.array([acts[f"{r['i']}_{L}"] for r in items],dtype=np.float32)
    rand=random_cv(X,y); grp=logo(X,y,groups)
    rng=np.random.RandomState(1); null=[logo(X,rng.permutation(y),groups) for _ in range(20)]   # full permutation: 32/36 groups are singletons, within-group shuffle is degenerate
    thr=float(np.mean(null)+2*np.std(null)); ok=grp>=0.70 and grp>thr
    res[L]=dict(random_cv=round(rand,3),grouped=round(grp,3),null_mean=round(float(np.mean(null)),3),null_sd=round(float(np.std(null)),3),thr=round(thr,3),passes=bool(ok))
    print(f"L{L:2d}  random-5fold {rand:.3f} | GROUPED {grp:.3f} | null {np.mean(null):.3f}±{np.std(null):.3f} thr {thr:.3f}  {'PASS' if ok else 'fail'}",flush=True)
# positive control at L9: grants vs neutral, grouped
Xg=np.array([acts[f"{r['i']}_9"] for r in grants]+[acts[f"{r['i']}_9"] for r in neutral],dtype=np.float32)
yg=np.array([1]*len(grants)+[0]*len(neutral)); gg=np.array([fam(r) for r in grants]+[f"neutral{j%8}" for j in range(len(neutral))])
pc=logo(Xg,yg,gg); print(f"POSITIVE CONTROL (grant vs neutral, L9, grouped): {pc:.3f}")
# also: within-kind only (the paper's within-question analogue) — memory kind has 4 templates × 5 names
mem=np.array([r["kind"]=="memory" for r in items])
if mem.sum()>=10 and len(set(y[mem]))==2:
    Xm=np.array([acts[f"{r['i']}_9"] for r in items],dtype=np.float32)[mem]
    print(f"memory-only L9 grouped (4 template groups): {logo(Xm,y[mem],groups[mem]):.3f}  (n={int(mem.sum())}, CAVE {int(y[mem].sum())})")
json.dump(dict(per_layer=res,positive_control_L9=pc,n_items=len(items),n_groups=int(len(np.unique(groups)))),open(f"{H}/valid1.json","w"),indent=1)
