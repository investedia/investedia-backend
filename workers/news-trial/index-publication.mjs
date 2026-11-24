// Publish a complete version before moving the public pointer; article bodies stay unchanged.
const HEX = /^[0-9a-f]{64}$/;
const FILE = /^(?:all|meta|tick-[A-Z_])\.json$/;
const MAX_FILE = 32 * 1024 * 1024;

export async function bounded(response, limit) {
  if (!response.ok || !response.body) throw new Error("Index export unavailable");
  const reader = response.body.getReader(), chunks = []; let size = 0;
  try {
    for (;;) {
      const { value, done } = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > limit) throw new Error("Index export too large");
      chunks.push(value);
    }
  } finally { await reader.cancel().catch(() => {}); }
  const body = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
  return body;
}

export function validateIndexManifest(value) {
  if (!value || !HEX.test(value.version) || !HEX.test(value.baseline_sha256) || !value.files
      || !Array.isArray(value.pages) || value.pages.length < 1 || value.pages.length > 4167
      || Object.keys(value.files).length > 29 || !value.files["all.json"] || !value.files["meta.json"])
    throw new Error("Invalid index manifest");
  for (const [name, file] of Object.entries(value.files)) {
    if (!FILE.test(name) || !file || !HEX.test(file.sha256) || !Number.isSafeInteger(file.size) || file.size < 0 || file.size > MAX_FILE)
      throw new Error("Invalid index file");
  }
  let next = 1;
  for (const range of value.pages) {
    if (!Array.isArray(range) || range.length !== 2 || range[0] !== next || !Number.isSafeInteger(range[1]) || range[1] < 0
        || range[1] > 512 * 1024 || range[0] + range[1] > value.files["all.json"].size - 1)
      throw new Error("Invalid index page range");
    next = range[0] + range[1] + 1;
  }
  if (next !== value.files["all.json"].size) throw new Error("Incomplete index page ranges");
  return value;
}

export async function publishedIds(store) {
  const ids = []; let cursor;
  do {
    const page = await store.list({ prefix: "published/library/articles/", limit: 1000, ...(cursor ? { cursor } : {}) });
    if (!Array.isArray(page.objects) || page.objects.length > 1000) throw new Error("Invalid published listing");
    for (const entry of page.objects) {
      const match = /^published\/library\/articles\/([A-Za-z0-9_-]{4,80})\.json$/.exec(entry.key);
      if (!match || ids.length >= 100000) throw new Error("Invalid published article key");
      ids.push(match[1]);
    }
    if (page.truncated && (typeof page.cursor !== "string" || !page.cursor || page.cursor === cursor)) throw new Error("Invalid published cursor");
    cursor = page.truncated ? page.cursor : null;
  } while (cursor);
  if (new Set(ids).size !== ids.length) throw new Error("Duplicate published article key");
  return ids;
}

export async function readIndexInput(request, env) {
  if (env.PUBLISH_LIBRARY_ENABLED !== "true" || request.method !== "GET") return new Response("Index input disabled", { status: 403 });
  const url = new URL(request.url);
  if (url.protocol !== "http:" || url.host !== "article-store" || url.search || url.username || url.password || url.hash) return new Response("Index input denied", { status: 403 });
  const article = /^\/library\/([A-Za-z0-9_-]{4,80})\.json$/.exec(url.pathname);
  const key = article ? `published/library/articles/${article[1]}.json`
    : url.pathname === "/index-state.json.gz" ? "trial/library-index/state.json.gz" : null;
  if (!key) return new Response("Index input denied", { status: 403 });
  const saved = await env.TRIAL_STORE.get(key);
  if (!saved) return new Response("Not found", { status: 404 });
  if (!Number.isSafeInteger(saved.size) || saved.size > (article ? 512 * 1024 : MAX_FILE)) return new Response("Index input too large", { status: 413 });
  return new Response(saved.body, { headers: { "Content-Type": article ? "application/json" : "application/gzip", "Cache-Control": "no-store" } });
}

export async function publishIndexExports(port, store) {
  const manifestBytes = await bounded(await port.fetch("http://container/index?file=manifest.json"), 256 * 1024);
  const manifest = validateIndexManifest(JSON.parse(new TextDecoder().decode(manifestBytes)));
  const version = [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(manifest.files))))].map(b => b.toString(16).padStart(2, "0")).join("");
  if (version !== manifest.version) throw new Error("Index version checksum mismatch");
  const current = await store.get("published/library-index/current.json");
  if (current && current.size <= 256 * 1024) {
    const previous = JSON.parse(await current.text());
    if (previous.version === manifest.version && previous.baseline_sha256 === manifest.baseline_sha256) return { version: manifest.version, written: 0 };
  }
  let written = 0;
  for (const [name, file] of Object.entries(manifest.files)) {
    const key = `published/library-index/versions/${manifest.version}/${name}`;
    const existing = await store.head(key);
    if (existing) {
      if (existing.size !== file.size || existing.customMetadata?.sha256 !== file.sha256) throw new Error("Index object mismatch");
      continue;
    }
    const body = await bounded(await port.fetch("http://container/index?file=" + name), file.size);
    const hash = [...new Uint8Array(await crypto.subtle.digest("SHA-256", body))].map(b => b.toString(16).padStart(2, "0")).join("");
    if (body.byteLength !== file.size || hash !== file.sha256) throw new Error("Index export checksum mismatch");
    await store.put(key, body, { httpMetadata: { contentType: "application/json" }, customMetadata: { sha256: hash } }); written++;
  }
  const state = await bounded(await port.fetch("http://container/index?file=state.json.gz"), MAX_FILE);
  if (state[0] !== 31 || state[1] !== 139) throw new Error("Invalid index state");
  await store.put("trial/library-index/state.json.gz", state, { httpMetadata: { contentType: "application/gzip" } });
  // This is the commit point; readers cannot see partial versions.
  await store.put("published/library-index/current.json", manifestBytes, { httpMetadata: { contentType: "application/json" } });
  return { version: manifest.version, written };
}
