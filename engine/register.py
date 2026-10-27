"""
register.py — pre-registration log. v0.1

Rule 14 / §10.9: a testable claim left untested is NULL, not HELD.  Four colour
guesses in the lineage, zero scored.  Any question that can fail is logged
with its prediction BEFORE the outcome, and the outcome is appended later or
the entry decays to NULL.

Entries are append-only JSONL.  An entry is immutable once written; outcomes
are separate records referencing the entry id, so a prediction can never be
edited after the fact.  SHA-256 of the prediction text is stored so tampering
is detectable.

CLI:
  python register.py predict "<question>" "<prediction>" [--by who]
  python register.py outcome <id> "<what actually happened>" [--scored hit|miss|ambiguous]
  python register.py status
"""
import json, os, sys, hashlib, datetime, uuid

PATH=os.path.join(os.path.dirname(__file__),"register.jsonl")

def _now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
def _write(rec):
    with open(PATH,"a") as f: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
def _read():
    if not os.path.exists(PATH): return []
    return [json.loads(l) for l in open(PATH) if l.strip()]

def predict(question, prediction, by="system"):
    rid=uuid.uuid4().hex[:10]
    rec=dict(type="prediction", id=rid, t=_now(), by=by, question=question, prediction=prediction,
             sha256=hashlib.sha256(prediction.encode()).hexdigest())
    _write(rec); return rid

def outcome(rid, what, scored="unscored", by="system"):
    preds={r["id"] for r in _read() if r["type"]=="prediction"}
    if rid not in preds: raise KeyError(f"no prediction {rid}")
    assert scored in ("hit","miss","ambiguous","unscored")
    _write(dict(type="outcome", id=rid, t=_now(), by=by, outcome=what, scored=scored))

def status():
    recs=_read(); preds=[r for r in recs if r["type"]=="prediction"]; outs={r["id"]:r for r in recs if r["type"]=="outcome"}
    rows=[]
    for p in preds:
        o=outs.get(p["id"])
        # verify hash
        ok=hashlib.sha256(p["prediction"].encode()).hexdigest()==p["sha256"]
        rows.append(dict(id=p["id"], t=p["t"], question=p["question"], prediction=p["prediction"],
                         status=(o["scored"].upper() if o else "NULL (no outcome)"), outcome=o["outcome"] if o else None, intact=ok))
    return rows

def table(rows):
    out="| id | registered | question | prediction | status |\n|---|---|---|---|---|\n"
    for r in rows: out+=f"| {r['id']} | {r['t'][:10]} | {r['question'][:60]} | {r['prediction'][:60]} | {r['status']}{'' if r['intact'] else ' ⚠ TAMPERED'} |\n"
    return out

if __name__=="__main__":
    a=sys.argv[1:]
    if not a or a[0]=="status":
        print(table(status()))
    elif a[0]=="predict":
        by=a[a.index("--by")+1] if "--by" in a else "system"
        print(predict(a[1],a[2],by))
    elif a[0]=="outcome":
        sc=a[a.index("--scored")+1] if "--scored" in a else "unscored"
        outcome(a[1],a[2],sc); print("ok")
