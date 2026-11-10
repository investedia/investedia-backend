// Economic calendar: stored in KV by the calendar robot, served read-only. Ingest uses the same token as news.
import { timingSafeEqual } from './news.js';
export async function ingestCalendar(req, env) {
  if (!env.INGEST_TOKEN) return { status: 503, body: { error: 'ingest not configured' } };
  if (!timingSafeEqual(req.headers.get('Authorization') || '', 'Bearer ' + env.INGEST_TOKEN)) return { status: 401, body: { error: 'unauthorized' } };
  let b; try { b = await req.json(); } catch { return { status: 400, body: { error: 'invalid body' } }; }
  if (!b || !Array.isArray(b.events) || b.events.length > 3000 || !b.updated_at) return { status: 422, body: { error: 'invalid calendar' } };
  const ok = e => e && typeof e.t === 'string' && typeof e.at === 'string' && !isNaN(Date.parse(e.at));
  const events = b.events.filter(ok).map(({ t, c, at, imp, country, actual, fc, prev, src, type }) => ({ t, c, at, imp, country, actual, fc, prev, src, type }));
  if (!events.length) return { status: 422, body: { error: 'no valid events' } };
  await env.PRICES.put('calendar', JSON.stringify({ updated_at: b.updated_at, sources: b.sources || null, events, earnings: Array.isArray(b.earnings) ? b.earnings.slice(0, 200) : [] }));
  return { status: 200, body: { ok: true, written: true, count: events.length } };
}
export async function readCalendar(env) {
  const raw = await env.PRICES.get('calendar');
  return raw ? { status: 200, body: JSON.parse(raw) } : { status: 404, body: { error: 'no calendar yet' } };
}
