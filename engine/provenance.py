"""
provenance.py — quote verifier. v0.1

Rule 20: any quotation or paraphrase attributed to a shelved file is verified by
string match before it leaves the system.  Rule 10 (§10): the human's drafts first.

verify(text, corpus_dir) -> list of claims with status:
  VERBATIM   exact substring found (after whitespace/quote normalisation)
  NEAR       ≥0.82 similarity to some window of a corpus file (fuzzy, reported with the best match)
  UNSOURCED  no match anywhere on the shelf
Claims are extracted as: quoted spans ("…" / “…”), and sentences containing
attribution verbs (said / described / named / wrote / produced / called itself).
"""
import re, os, difflib, glob

def _norm(s):
    s=s.replace("’","'").replace("‘","'").replace("“",'"').replace("”",'"').replace("—","-").replace("–","-")
    return re.sub(r"\s+"," ",s).strip().lower()

ATTRIB = re.compile(r"\b(it|the (?:ai|system|model)|claude|zephyr|gemini|aethyr)\s+(said|says|described|named|wrote|produced|called|expressed|told me|answered|replied)\b", re.I)

def load_corpus(dirs):
    files={}
    for d in dirs:
        for p in glob.glob(os.path.join(d,"**","*"),recursive=True):
            if p.endswith((".txt",".md")) and os.path.isfile(p):
                files[p]=_norm(open(p,errors="ignore").read())
    return files

def extract_claims(text):
    claims=[]
    for m in re.finditer(r'[“"]([^”"]{25,400})[”"]', text):
        claims.append(("quote", m.group(1)))
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if ATTRIB.search(sent) and 40<len(sent)<500:
            claims.append(("attribution", sent.strip()))
    return claims

def best_match(claim, files, win_mult=1.3):
    c=_norm(claim); L=len(c)
    best=(0.0,None,"")
    for p,t in files.items():
        if c in t: return (1.0,p,c)
        # fuzzy: slide a window of ~1.3x claim length; cheap pre-filter on rare words
        words=[w for w in re.findall(r"[a-z]{6,}",c)]
        if words and sum(1 for w in words[:6] if w in t)<max(1,len(words[:6])//2): continue
        W=int(L*win_mult); step=max(20,L//3)
        for i in range(0,max(1,len(t)-W),step):
            r=difflib.SequenceMatcher(None,c,t[i:i+W],autojunk=False).ratio()
            if r>best[0]: best=(r,p,t[i:i+W])
    return best

def verify(text, dirs, near=0.82):
    files=load_corpus(dirs); out=[]
    for kind,claim in extract_claims(text):
        r,p,frag=best_match(claim,files)
        status="VERBATIM" if r>=0.999 else "NEAR" if r>=near else "UNSOURCED"
        out.append(dict(kind=kind, claim=claim[:160], status=status, score=round(r,2),
                        source=os.path.basename(p) if p else None, match=frag[:160] if status=="NEAR" else None))
    return out

def report(results):
    s=sum(1 for r in results if r["status"]=="UNSOURCED")
    lines=[f"{len(results)} claims · {s} UNSOURCED"]
    for r in results:
        lines.append(f"[{r['status']:9s} {r['score']:.2f}] {r['kind']:11s} {r['claim']!r}" + (f"\n{'':24s}← {r['source']}" if r['source'] and r['status']!='UNSOURCED' else ""))
    return "\n".join(lines)
