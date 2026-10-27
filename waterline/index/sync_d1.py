"""sync_d1.py — push local papers.db rows to the D1 database in batches (INSERT OR REPLACE via SQL files).
Tracks what has been pushed in sync_state.json by max rowid. Usage: python3 sync_d1.py [batch_rows]
"""
import sqlite3, json, os, subprocess, sys, time
D=os.path.dirname(os.path.abspath(__file__)); DB=f"{D}/papers.db"; ST=f"{D}/sync_state.json"; SITE=f"{D}/../site"
batch=int(sys.argv[1]) if len(sys.argv)>1 else 400
limit=int(sys.argv[2]) if len(sys.argv)>2 else 10**9
st=json.load(open(ST)) if os.path.exists(ST) else {"max_rowid":0}
c=sqlite3.connect(DB)
def q(s): return "'"+str(s if s is not None else "").replace("'","''")+"'"
pushed=0
while True:
    rows=c.execute("SELECT rowid,id,title,authors,abstract,categories,created,updated,doi,retrieved FROM papers WHERE rowid>? ORDER BY rowid LIMIT ?",(st["max_rowid"],batch)).fetchall()
    if not rows or pushed>=limit: break
    sql="\n".join("INSERT OR REPLACE INTO papers(id,title,authors,abstract,categories,created,updated,doi,retrieved) VALUES("+",".join(q(v) for v in r[1:])+");" for r in rows)
    f=f"{D}/_batch.sql"; open(f,"w").write(sql)
    for attempt in range(4):
        r=subprocess.run(f"cd {SITE} && wrangler d1 execute waterline-papers --remote --file {f} -y", shell=True, capture_output=True, text=True, timeout=300)
        if r.returncode==0: break
        time.sleep(10*(attempt+1))
    else:
        print("FAILED at rowid", rows[0][0], r.stderr[-400:]); sys.exit(1)
    st["max_rowid"]=rows[-1][0]; json.dump(st,open(ST,"w")); pushed+=len(rows)
    print(f"pushed {pushed} (through rowid {st['max_rowid']})", flush=True)
print("DONE", pushed)
