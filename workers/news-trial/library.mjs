// Full articles remain private trial artifacts until a separately approved website cutover.
const ID = /^[A-Za-z0-9_-]{4,80}$/;
const MAX_PAGE = 6 * 1024 * 1024;

export function validArticle(article) {
  return article && typeof article.id === "string" && ID.test(article.id) && typeof article.headline === "string" && article.headline.length > 0
    && typeof article.published_at === "string" && Number.isFinite(Date.parse(article.published_at))
    && article.source && typeof article.source === "object" && !Array.isArray(article.source)
    && article.location && typeof article.location === "object" && !Array.isArray(article.location) && !article.demo;
}

async function boundedJson(response) {
  if (!response.ok || !response.body) throw new Error("Library export unavailable");
  const reader = response.body.getReader(), chunks = []; let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read(); if (done) break;
      size += value.length; if (size > MAX_PAGE) throw new Error("Library export too large");
      chunks.push(value);
    }
  } finally { await reader.cancel().catch(() => {}); }
  const data = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { data.set(chunk, offset); offset += chunk.length; }
  return JSON.parse(new TextDecoder().decode(data));
}

export async function storeTrialLibrary(port, store, expected) {
  if (!Number.isSafeInteger(expected) || expected < 0 || expected > 10000) throw new Error("Invalid library count");
  let cursor = 0, written = 0; const seen = new Set();
  do {
    const page = await boundedJson(await port.fetch(`http://container/library?cursor=${cursor}`));
    if (!Array.isArray(page.articles) || page.articles.length > 10 || page.total !== expected
        || page.next !== cursor + page.articles.length || page.next > expected
        || (page.articles.length === 0 && cursor !== expected)) throw new Error("Invalid library page");
    for (const article of page.articles) {
      if (!validArticle(article) || seen.has(article.id)) throw new Error("Invalid library article");
      seen.add(article.id);
      const body = JSON.stringify(article);
      if (new TextEncoder().encode(body).length > 512 * 1024) throw new Error("Library article too large");
      const key = `trial/library/articles/${article.id}.json`;
      // The shared news Durable Object serializes writes; preserve the first saved article exactly.
      if (!await store.head(key)) {
        await store.put(key, body, { httpMetadata: { contentType: "application/json" } }); written++;
      }
    }
    cursor = page.next;
  } while (cursor < expected);
  return { articles: seen.size, written };
}

export async function readTrialArticle(request, store) {
  const ids = new URL(request.url).searchParams.getAll("id");
  if (ids.length !== 1 || !ID.test(ids[0])) return new Response("Invalid article id", { status: 400 });
  const saved = await store.get(`trial/library/articles/${ids[0]}.json`);
  return saved ? new Response(saved.body, { headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } })
    : new Response("Article not found", { status: 404 });
}
