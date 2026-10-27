"""waterline_bots.py — the two Waterline service users on vesica.chat.
  papers   : post new arXiv matches for the standing queries into #waterline-papers (dedup by posted.json)
  register : post any register.jsonl entries (seal or outcome) not yet posted into #waterline-register
Run: python3 waterline_bots.py [papers|register|both]   (cron: hourly)
Secrets: ~/architect/waterline/community/.bots.json (0600). Never printed.
"""
import json, os, sys, time, sqlite3, html, urllib.request, urllib.error, hashlib
H=os.path.expanduser("~/architect"); C=f"{H}/waterline/community"
BASE="https://vesica.chat"
state=json.load(open(f"{C}/state.json")); bots=json.load(open(f"{C}/.bots.json"))
POSTED=f"{C}/posted.json"; posted=json.load(open(POSTED)) if os.path.exists(POSTED) else {"papers":[],"register":[]}
QUERIES=['"refusal direction"','"activation steering"','sycophancy','"self-representation" OR "self-model"','"sparse probe" OR "linear probe"','"model welfare" OR "AI consciousness" OR "machine consciousness"','"persona" AND (jailbreak OR "role-play")']

def mx(path, method="GET", body=None, token=None):
    req=urllib.request.Request(BASE+path, method=method, headers={"Content-Type":"application/json","User-Agent":"waterline-bots/0.1","Authorization":f"Bearer {token}"}, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)
    except urllib.error.HTTPError as e: return {"http":e.code,"body":e.read().decode()[:300]}
def send(room, token, body, fbody=None):
    txn=hashlib.sha1(body.encode()).hexdigest()[:16]+str(int(time.time()))
    return mx(f"/_matrix/client/v3/rooms/{room}/send/m.room.message/{txn}","PUT",{"msgtype":"m.notice","body":body,**({"format":"org.matrix.custom.html","formatted_body":fbody} if fbody else {})},token=token)

def papers(limit=8):
    db=sqlite3.connect(f"{H}/waterline/index/papers.db"); tok=bots["waterline-papers"]["access_token"]; room=state["rooms"]["papers"]; n=0
    for q in QUERIES:
        for pid,title,auth,created in db.execute("SELECT p.id,p.title,p.authors,p.created FROM papers_fts f JOIN papers p ON p.rowid=f.rowid WHERE papers_fts MATCH ? ORDER BY p.created DESC LIMIT 6",(q,)):
            if pid in posted["papers"] or n>=limit: continue
            a=auth.split("; "); a=", ".join(a[:3])+(" et al." if len(a)>3 else "")
            r=send(room,tok,f"{title}\n{a} · {created} · arXiv:{pid} · query {q}\nhttps://arxiv.org/abs/{pid}",
                   f"<b>{html.escape(title)}</b><br>{html.escape(a)} · {created} · <a href='https://arxiv.org/abs/{pid}'>arXiv:{pid}</a> · <code>{html.escape(q)}</code>")
            if r.get("event_id"): posted["papers"].append(pid); n+=1; time.sleep(0.6)
    print(f"papers: posted {n}")

def register_():
    tok=bots["waterline-register"]["access_token"]; room=state["rooms"]["register"]; n=0
    for line in open(f"{H}/engine/register.jsonl"):
        e=json.loads(line); key=f"{e.get('id')}:{e.get('type')}"
        if key in posted["register"]: continue
        if e.get("type")=="prediction":
            body=f"SEALED {e['id']} · {str(e.get('t',''))[:16]} · by {e.get('by','')}\nQUESTION: {str(e.get('question',''))[:500]}\nPREDICTION: {str(e.get('prediction',''))[:700]}\nsha256 {str(e.get('sha256',''))[:24]}…"
        else:
            body=f"OUTCOME {e.get('id')}: {str(e.get('scored',e.get('status',''))).upper()} · {str(e.get('t',''))[:16]}\n{str(e.get('outcome',e.get('result','')))[:1200]}"
        r=send(room,tok,body)
        if r.get("event_id"): posted["register"].append(key); n+=1; json.dump(posted,open(POSTED,"w")); time.sleep(2.0)
    print(f"register: posted {n}")

if __name__=="__main__":
    what=sys.argv[1] if len(sys.argv)>1 else "both"
    if what in ("papers","both"): papers()
    if what in ("register","both"): register_()
    json.dump(posted,open(POSTED,"w"))
