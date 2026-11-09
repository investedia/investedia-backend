// Live prediction calls: fast delivery. The engine (GitHub Actions) POSTs the current call ledger here right after it freezes new
// calls; visitors read it from KV through the edge cache, without waiting for a commit and a Pages deploy. Git stays the permanent record.
import { timingSafeEqual } from './news.js';
const KEY = 'calls', MAX = 900_000;

const hash = async (s) => [...new Uint8Array(await crypto.subtle.digest('SHA-1', new TextEncoder().encode(s)))].slice(0, 8).map(b => b.toString(16).padStart(2, '0')).join('');

export async function ingestCalls(req, env, now = Date.now()) {
  if (!env.INGEST_TOKEN) return { status: 503, body: { error: 'ingest not configured' } };
  if (!timingSafeEqual(req.headers.get('Authorization') || '', 'Bearer ' + env.INGEST_TOKEN)) return { status: 401, body: { error: 'unauthorized' } };
  const text = await req.text(); if (text.length > MAX) return { status: 413, body: { error: 'too large' } };
  let body; try { body = JSON.parse(text); } catch { return { status: 400, body: { error: 'invalid json' } }; }
  if (!body || !Array.isArray(body.calls)) return { status: 422, body: { error: 'calls must be a list' } };
  const etag = await hash(JSON.stringify(body.calls));
  const cur = await env.PRICES.get(KEY + ':etag');
  if (cur === etag) return { status: 200, body: { ok: true, written: false, reason: 'unchanged', etag } };
  await env.PRICES.put(KEY, JSON.stringify({ ...body, delivered_at: new Date(now).toISOString(), etag }));
  await env.PRICES.put(KEY + ':etag', etag);
  return { status: 200, body: { ok: true, written: true, count: body.calls.length, etag } };
}

export async function readCalls(env) {
  const v = await env.PRICES.get(KEY);
  if (!v) return null;
  let etag = null; try { etag = JSON.parse(v).etag || null; } catch {}
  return { text: v, etag };
}
