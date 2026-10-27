// GET /api/search?q=...&page=0  — FTS5 over arXiv cs.AI/cs.CL/cs.LG abstracts in D1. Abstract verbatim; retrieved timestamp returned (provenance).
export async function onRequestGet({ request, env }) {
  const u = new URL(request.url);
  const q = (u.searchParams.get("q") || "").trim().slice(0, 200);
  const page = Math.max(0, parseInt(u.searchParams.get("page") || "0", 10) || 0);
  const hdr = { "content-type": "application/json; charset=utf-8", "cache-control": "public, max-age=300", "access-control-allow-origin": "*" };
  if (!q) {
    const n = await env.DB.prepare("SELECT count(*) AS n, max(created) AS latest, max(retrieved) AS retrieved FROM papers").first();
    return new Response(JSON.stringify({ count: n.n, latest: n.latest, retrieved: n.retrieved, results: [] }), { headers: hdr });
  }
  // sanitise to FTS5 terms: quote each token; allow AND/OR/NOT and quoted phrases
  const fts = q.match(/"[^"]+"|\S+/g).map(t => /^(AND|OR|NOT)$/i.test(t) ? t.toUpperCase() : (t.startsWith('"') ? t : '"' + t.replace(/"/g, "") + '"')).join(" ");
  try {
    const rows = await env.DB.prepare(
      `SELECT p.id, p.title, p.authors, p.abstract, p.categories, p.created, p.updated, p.doi, p.retrieved, bm25(papers_fts, 0, 8.0, 2.0, 1.0) AS rank
       FROM papers_fts JOIN papers p ON p.rowid = papers_fts.rowid
       WHERE papers_fts MATCH ?1 ORDER BY rank LIMIT 20 OFFSET ?2`).bind(fts, page * 20).all();
    return new Response(JSON.stringify({ q, page, results: rows.results }), { headers: hdr });
  } catch (e) {
    return new Response(JSON.stringify({ q, error: "query could not be parsed", results: [] }), { status: 400, headers: hdr });
  }
}
