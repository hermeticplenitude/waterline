CREATE TABLE IF NOT EXISTS papers(id TEXT PRIMARY KEY, title TEXT, authors TEXT, abstract TEXT, categories TEXT, created TEXT, updated TEXT, doi TEXT, retrieved TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(id UNINDEXED, title, authors, abstract, content='papers', content_rowid='rowid');
CREATE TRIGGER IF NOT EXISTS p_ai AFTER INSERT ON papers BEGIN INSERT INTO papers_fts(rowid,id,title,authors,abstract) VALUES (new.rowid,new.id,new.title,new.authors,new.abstract); END;
CREATE INDEX IF NOT EXISTS p_created ON papers(created);