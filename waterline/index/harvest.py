"""harvest.py — arXiv OAI-PMH backfill + incremental into local SQLite (papers.db).
Keeps only papers with a category in cs.AI / cs.CL / cs.LG. Abstract verbatim; retrieved timestamp recorded (provenance).
Usage: python3 harvest.py backfill            # full cs set, resumable (state in harvest_state.json)
       python3 harvest.py since 2026-10-20     # incremental
"""
import sys, os, json, time, sqlite3, re, urllib.request, urllib.error, xml.etree.ElementTree as ET, datetime
D=os.path.dirname(os.path.abspath(__file__)); DB=f"{D}/papers.db"; STATE=f"{D}/harvest_state.json"
KEEP={"cs.AI","cs.CL","cs.LG"}
UA={"User-Agent":"waterline.institute/0.1 (research index; mailto:contact@waterline.institute)"}
NS={"o":"http://www.openarchives.org/OAI/2.0/","a":"http://arxiv.org/OAI/arXiv/"}

def db():
    c=sqlite3.connect(DB); c.executescript("""
    CREATE TABLE IF NOT EXISTS papers(id TEXT PRIMARY KEY, title TEXT, authors TEXT, abstract TEXT, categories TEXT, created TEXT, updated TEXT, doi TEXT, retrieved TEXT);
    CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(id UNINDEXED, title, authors, abstract, content='papers', content_rowid='rowid');
    CREATE TRIGGER IF NOT EXISTS p_ai AFTER INSERT ON papers BEGIN INSERT INTO papers_fts(rowid,id,title,authors,abstract) VALUES (new.rowid,new.id,new.title,new.authors,new.abstract); END;
    CREATE TRIGGER IF NOT EXISTS p_ad AFTER DELETE ON papers BEGIN INSERT INTO papers_fts(papers_fts,rowid,id,title,authors,abstract) VALUES('delete',old.rowid,old.id,old.title,old.authors,old.abstract); END;
    CREATE TRIGGER IF NOT EXISTS p_au AFTER UPDATE ON papers BEGIN INSERT INTO papers_fts(papers_fts,rowid,id,title,authors,abstract) VALUES('delete',old.rowid,old.id,old.title,old.authors,old.abstract); INSERT INTO papers_fts(rowid,id,title,authors,abstract) VALUES (new.rowid,new.id,new.title,new.authors,new.abstract); END;
    """); return c

def fetch(url, tries=6):
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=120) as r: return r.read().decode("utf-8","replace")
        except urllib.error.HTTPError as e:
            if e.code==503: wait=int(e.headers.get("Retry-After","10")); time.sleep(min(wait,60)); continue
            if e.code==429: time.sleep(30); continue
            raise
        except Exception: time.sleep(5*(t+1))
    raise RuntimeError("fetch failed "+url)

def parse(xml):
    root=ET.fromstring(xml); out=[]
    for rec in root.iter(f"{{{NS['o']}}}record"):
        m=rec.find("o:metadata/a:arXiv",NS)
        if m is None: continue
        cats=(m.findtext("a:categories",default="",namespaces=NS)).split()
        if not KEEP.intersection(cats): continue
        auth="; ".join(" ".join(filter(None,[a.findtext("a:forenames",default="",namespaces=NS),a.findtext("a:keyname",default="",namespaces=NS)])).strip() for a in m.findall("a:authors/a:author",NS))
        out.append((m.findtext("a:id",namespaces=NS), re.sub(r"\s+"," ",m.findtext("a:title",default="",namespaces=NS)).strip(), auth,
                    re.sub(r"\s+"," ",m.findtext("a:abstract",default="",namespaces=NS)).strip(), " ".join(cats),
                    m.findtext("a:created",default="",namespaces=NS), m.findtext("a:updated",default="",namespaces=NS), m.findtext("a:doi",default="",namespaces=NS),
                    datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")))
    tok=root.find(".//o:resumptionToken",NS)
    return out, (tok.text.strip() if tok is not None and tok.text else None), (tok.get("completeListSize") if tok is not None else None)

def run(base_params, label):
    c=db(); st=json.load(open(STATE)) if os.path.exists(STATE) else {}
    tok=st.get(label,{}).get("token"); n=st.get(label,{}).get("n",0); pages=0
    while True:
        url="https://oaipmh.arxiv.org/oai?verb=ListRecords&"+(f"resumptionToken={tok}" if tok else f"metadataPrefix=arXiv&{base_params}")
        rows,tok,size=parse(fetch(url))
        c.executemany("INSERT INTO papers VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,authors=excluded.authors,abstract=excluded.abstract,categories=excluded.categories,updated=excluded.updated,doi=excluded.doi,retrieved=excluded.retrieved",rows); c.commit()
        n+=len(rows); pages+=1
        st[label]={"token":tok,"n":n,"size":size,"at":datetime.datetime.utcnow().isoformat()}; json.dump(st,open(STATE,"w"))
        total=c.execute("SELECT count(*) FROM papers").fetchone()[0]
        print(f"[{label}] page {pages} +{len(rows)} kept (cursor {tok.split('|')[-1] if tok and '|' in tok else '-'}/{size})  db={total}", flush=True)
        if not tok: break
        time.sleep(3)
    print("DONE", label, n)

if __name__=="__main__":
    if sys.argv[1]=="backfill": run("set=cs","backfill")
    elif sys.argv[1]=="since": run(f"set=cs&from={sys.argv[2]}",f"since_{sys.argv[2]}")
