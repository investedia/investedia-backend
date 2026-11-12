// Push alerts: after each news ingest, members who follow a country or asset named in a new article get one push.
// Free: 3 alerts per ISO week (reset Monday 00:00 UTC). Off unless ALERTS_ENABLED="true" and the Supabase + VAPID settings exist.
import { sendPush } from './webpush.js';
export const FREE_PER_WEEK = 3;
export function isoWeek(t) { const d = new Date(t); d.setUTCHours(0, 0, 0, 0); d.setUTCDate(d.getUTCDate() + 3 - ((d.getUTCDay() + 6) % 7));
  const w1 = new Date(Date.UTC(d.getUTCFullYear(), 0, 4)); return d.getUTCFullYear() + '-W' + String(1 + Math.round(((d - w1) / 864e5 - 3 + ((w1.getUTCDay() + 6) % 7)) / 7)).padStart(2, '0'); }
const norm = s => String(s || '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/^the /, '').trim();
const COUNTRY_ALIAS = { 'united states of america': 'united states', usa: 'united states', us: 'united states', uk: 'united kingdom', 'czech republic': 'czechia' };
const country = s => COUNTRY_ALIAS[norm(s)] || norm(s);
const sym = s => String(s || '').toUpperCase().replace(/-USD$/, '');
// What an article is about: its country, and the symbols / names of the assets it names.
export function about(story) {
  const syms = new Set(), names = new Set();
  for (const i of story.impacts || []) { if (i.ticker) syms.add(sym(i.ticker)); if (i.name) names.add(norm(i.name)); }
  for (const e of story.entities || []) { if (e.ticker) syms.add(sym(e.ticker)); if (e.asset?.id) syms.add(sym(String(e.asset.id).split(':').pop())); if (e.name) names.add(norm(e.name)); }
  return { country: country(story.location?.country), syms, names };
}
// The first followed item this article matches (country or asset), or null.
export function match(items, story) {
  const a = about(story);
  for (const x of items?.a || []) if ((x.s && a.syms.has(sym(x.s))) || (x.n && a.names.has(norm(x.n)))) return x.n || x.s;
  for (const x of items?.c || []) if (x.k && country(x.k) === a.country) return x.k;
  return null;
}
function sb(env, path, init = {}) {
  return fetch(env.SUPABASE_URL.replace(/\/$/, '') + '/rest/v1/' + path, { ...init, headers: { apikey: env.SUPABASE_SERVICE_KEY, Authorization: 'Bearer ' + env.SUPABASE_SERVICE_KEY, 'Content-Type': 'application/json', ...(init.headers || {}) } });
}
export function alertsReady(env) { return env.ALERTS_ENABLED === 'true' && env.SUPABASE_URL && env.SUPABASE_SERVICE_KEY && env.VAPID_PUBLIC_KEY && env.VAPID_PRIVATE_KEY; }
// Plan who gets what (pure, testable): newest articles first; at most one alert per member per run; weekly cap; never the same article twice.
export function plan(stories, watch, logs, now) {
  const week = isoWeek(now), byUser = new Map(logs.filter(l => l.week === week).map(l => [l.user_id, l])), out = [];
  const fresh = [...stories].sort((x, y) => Date.parse(y.published_at) - Date.parse(x.published_at));
  for (const w of watch) {
    const log = byUser.get(w.user_id) || { sent: 0, article_ids: [] };
    if (log.sent >= FREE_PER_WEEK) continue;
    for (const s of fresh) { if ((log.article_ids || []).includes(s.id)) continue; const why = match(w.items, s); if (why) { out.push({ user_id: w.user_id, story: s, why, week, sent: log.sent + 1, ids: [...(log.article_ids || []).slice(-49), s.id] }); break; } }
  }
  return out;
}
export async function runAlerts(env, stories, now = Date.now()) {
  if (!alertsReady(env) || !stories?.length) return { skipped: true };
  const recent = stories.filter(s => now - Date.parse(s.published_at) < 3 * 36e5);  // only news from the last 3 hours is "instant"
  if (!recent.length) return { sent: 0 };
  const [watch, subs, logs] = await Promise.all([
    sb(env, 'watchlists?select=user_id,items').then(r => r.ok ? r.json() : []),
    sb(env, 'push_subscriptions?select=user_id,endpoint,p256dh,auth').then(r => r.ok ? r.json() : []),
    sb(env, 'alert_log?select=user_id,week,sent,article_ids&week=eq.' + isoWeek(now)).then(r => r.ok ? r.json() : [])]);
  const withPush = new Set(subs.map(s => s.user_id)), todo = plan(recent, watch.filter(w => withPush.has(w.user_id)), logs, now);
  let sent = 0, gone = 0;
  for (const t of todo.slice(0, 40)) {  // stays well inside the Worker's 50 subrequests per run
    const left = FREE_PER_WEEK - t.sent;
    const payload = { title: t.why + ' · Investedia', body: t.story.headline, url: '/story.html?id=' + encodeURIComponent(t.story.id), tag: 'inv-' + t.story.id, left };
    let ok = false;
    for (const s of subs.filter(x => x.user_id === t.user_id).slice(0, 3)) {
      try { const st = await sendPush(s, payload, env); if (st >= 200 && st < 300) ok = true; else if (st === 404 || st === 410) { gone++; await sb(env, 'push_subscriptions?endpoint=eq.' + encodeURIComponent(s.endpoint), { method: 'DELETE' }); } } catch {}
    }
    if (ok) { sent++; await sb(env, 'alert_log', { method: 'POST', headers: { Prefer: 'resolution=merge-duplicates' }, body: JSON.stringify({ user_id: t.user_id, week: t.week, sent: t.sent, article_ids: t.ids, updated_at: new Date(now).toISOString() }) }); }
  }
  return { sent, gone, planned: todo.length };
}
