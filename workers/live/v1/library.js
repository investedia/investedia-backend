// Article library by day: the hourly robot sends the articles of its last two days (compact rows); one KV key per day.
// GET /v1/library -> { days: { 'YYYY-MM-DD': count } }; GET /v1/library?day=YYYY-MM-DD -> { rows: [...] }.
// The website's built library covers everything up to its last build; these days fill the gap until the next build.
import { timingSafeEqual } from './news.js';
// Every stored day stays listed in the index (months-back backfills included); ~30 bytes per day, 10-year cap.
const DAY = /^\d{4}-\d{2}-\d{2}$/, KEEP_DAYS = 3660, MAX_ROWS = 1500;
const clean = r => (r && typeof r.id === 'string' && typeof r.h === 'string' && Number.isFinite(Date.parse(r.t)) ? {
  id: r.id.slice(0, 40), h: r.h.slice(0, 300), c: String(r.c || 'news').slice(0, 30), t: r.t, s: r.s ? String(r.s).slice(0, 120) : null,
  n: r.n ? String(r.n).slice(0, 80) : null, g: r.g ? String(r.g).slice(0, 10) : null, k: Number.isSafeInteger(r.k) && r.k > 0 ? Math.min(r.k, 99) : 1,
  ...(typeof r.i === 'string' && /^[\w./-]{1,200}$/.test(r.i) && !r.i.includes('..') ? { i: r.i } : {}) } : null);
export async function ingestLibrary(req, env, now = Date.now()) {
  if (!env.INGEST_TOKEN) return { status: 503, body: { error: 'ingest not configured' } };
  if (!timingSafeEqual(req.headers.get('Authorization') || '', 'Bearer ' + env.INGEST_TOKEN)) return { status: 401, body: { error: 'unauthorized' } };
  const text = await req.text(); if (text.length > 900_000) return { status: 413, body: { error: 'too large' } };
  let body; try { body = JSON.parse(text); } catch { return { status: 400, body: { error: 'invalid json' } }; }
  const days = body && typeof body.days === 'object' && !Array.isArray(body.days) ? Object.entries(body.days) : null;
  if (!days || !days.length || days.length > 3) return { status: 422, body: { error: 'send 1 to 3 days' } };
  let meta = {}; try { meta = JSON.parse(await env.PRICES.get('library:meta'))?.days || {}; } catch {}
  let written = 0;
  for (const [day, rows] of days) {
    if (!DAY.test(day) || !Array.isArray(rows) || rows.length > MAX_ROWS || Date.parse(day) > now + 864e5) return { status: 422, body: { error: 'bad day ' + day } };
    const seen = new Set(), out = rows.map(clean).filter(r => r && r.t.slice(0, 10) === day && !seen.has(r.id) && seen.add(r.id)).sort((a, b) => (a.t < b.t ? 1 : -1));
    if (!out.length) continue;
    const key = 'library:' + day, cur = await env.PRICES.get(key), next = JSON.stringify(out);
    if (cur !== next) { await env.PRICES.put(key, next); written++; }
    meta[day] = out.length;
  }
  const keep = Object.keys(meta).sort().slice(-KEEP_DAYS), metaNext = JSON.stringify({ updated_at: new Date(now).toISOString(), days: Object.fromEntries(keep.map(d => [d, meta[d]])) });
  if (written || (await env.PRICES.get('library:meta')) === null) { await env.PRICES.put('library:meta', metaNext); }
  return { status: 200, body: { ok: true, written } };
}
export async function handleLibrary(url, env) {
  const day = url.searchParams.get('day');
  if (day != null) {
    if (!DAY.test(day)) return { status: 400, body: { error: 'day must be YYYY-MM-DD' } };
    const raw = await env.PRICES.get('library:' + day);
    return raw ? { status: 200, body: { data: { day, rows: JSON.parse(raw) } } } : { status: 404, body: { error: 'no articles for that day' } };
  }
  let meta = null; try { meta = JSON.parse(await env.PRICES.get('library:meta')); } catch {}
  return { status: 200, body: { data: meta || { days: {} } } };
}
