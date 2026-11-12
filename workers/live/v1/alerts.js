// Alerts v2 (12 Nov 2026).
//  - Article alerts: a new article about a followed country / asset (watchlist stars). Unlimited; email (Free), push and/or email (Pro).
//  - Smart alerts: price move, market-moving only, sector news (country+price, release and combined come next). Free: 3 per 7 days
//    (enforced in Supabase), email only; Pro: unlimited, push and/or email per alert.
// Off unless ALERTS_ENABLED="true" and Supabase + Brevo settings exist. At most one email per member per run; never the same item twice.
import { sendPush } from './webpush.js';
import { alertEmail, sendEmail } from './brevo.js';
export const FREE_SMART = 3;
const SITE = 'https://investedia.com';
const norm = s => String(s || '').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '').replace(/^the /, '').trim();
const COUNTRY_ALIAS = { 'united states of america': 'united states', usa: 'united states', us: 'united states', uk: 'united kingdom', 'czech republic': 'czechia' };
const country = s => COUNTRY_ALIAS[norm(s)] || norm(s);
const sym = s => String(s || '').toUpperCase().replace(/-USD$/, '');
export function about(story) {
  const syms = new Set(), names = new Set();
  for (const i of story.impacts || []) { if (i.ticker) syms.add(sym(i.ticker)); if (i.name) names.add(norm(i.name)); }
  for (const e of story.entities || []) { if (e.ticker) syms.add(sym(e.ticker)); if (e.asset?.id) syms.add(sym(String(e.asset.id).split(':').pop())); if (e.name) names.add(norm(e.name)); }
  return { country: country(story.location?.country), syms, names };
}
// Followed items this article is about, minus muted ones. Keys: 'a:SYM' / 'c:Country'.
export function followHits(items, muted, story) {
  const a = about(story), m = new Set(muted || []), out = [];
  for (const x of items?.a || []) { const k = 'a:' + sym(x.s); if (!m.has(k) && ((x.s && a.syms.has(sym(x.s))) || (x.n && a.names.has(norm(x.n))))) out.push({ key: k, label: x.n || x.s }); }
  for (const x of items?.c || []) { const k = 'c:' + x.k; if (!m.has(k) && x.k && country(x.k) === a.country) out.push({ key: k, label: x.k }); }
  return out;
}
export const match = (items, story) => followHits(items, [], story)[0]?.label || null;  // kept for PR #69 tests
// Does a smart alert of an article type fire for this article? Returns the reason text or null.
export function smartArticleHit(alert, story, items) {
  const p = alert.params || {};
  if (alert.type === 'market_moving') {
    if (!story.market_moving) return null;
    if (p.scope === 'follows') { const h = followHits(items, [], story)[0]; return h ? 'Market-moving · ' + h.label : null; }
    return 'Market-moving';
  }
  if (alert.type === 'sector') {
    if (!p.category || norm(story.category) !== norm(p.category)) return null;
    if (p.market_moving_only && !story.market_moving) return null;
    return 'Sector · ' + p.category[0].toUpperCase() + p.category.slice(1);
  }
  return null;
}
// Price move from the Worker's price snapshot row [price, pct day, market time, fetched]. Returns {item, why, line} or null.
export function priceHit(alert, row) {
  const p = alert.params || {}; if (!row || !Number.isFinite(row[1]) || !(p.pct > 0)) return null;
  const d = row[1], dir = p.dir || 'either';
  if (!(dir === 'either' ? Math.abs(d) >= p.pct : dir === 'up' ? d >= p.pct : d <= -p.pct)) return null;
  const day = new Date(row[2] > 1e12 ? row[2] : (row[2] || 0) * 1000 || Date.now()).toISOString().slice(0, 10);
  return { item: sym(p.symbol) + ':' + day, why: `Price move · ${d > 0 ? '+' : ''}${d.toFixed(2)}% today`, title: `${p.name || p.symbol} ${d > 0 ? 'up' : 'down'} ${Math.abs(d).toFixed(1)}%`, line: `Your alert: moves ${dir === 'either' ? 'up or down' : dir} more than ${p.pct}% in a day.`, url: SITE + '/asset.html?s=' + encodeURIComponent(p.symbol) };
}
export function alertsReady(env) { return env.ALERTS_ENABLED === 'true' && !!(env.SUPABASE_URL && env.SUPABASE_SERVICE_KEY && env.BREVO_API_KEY && env.BREVO_SENDER_EMAIL); }
const pushReady = env => !!(env.VAPID_PUBLIC_KEY && env.VAPID_PRIVATE_KEY);
function sb(env, path, init = {}) {
  return fetch(env.SUPABASE_URL.replace(/\/$/, '') + '/rest/v1/' + path, { ...init, headers: { apikey: env.SUPABASE_SERVICE_KEY, ...(String(env.SUPABASE_SERVICE_KEY).startsWith('sb_') ? {} : { Authorization: 'Bearer ' + env.SUPABASE_SERVICE_KEY }), /* new sb_secret_ keys go in apikey only */ 'Content-Type': 'application/json', ...(init.headers || {}) } });
}
const get = (env, path) => sb(env, path).then(r => r.ok ? r.json() : []).catch(() => []);
const inList = ids => '(' + ids.map(x => '"' + String(x).replace(/["\\]/g, '') + '"').join(',') + ')';
// Plan deliveries (pure). members: [{user_id, email, muted, items, plan, push}], smart: active smart alerts, sent: Set of 'user|key|item|channel'.
export function plan(stories, members, smart, sent) {
  const out = new Map();  // user_id -> {member, email: [], push: []}
  const add = (m, ch, key, item, entry) => { if (sent.has([m.user_id, key, item, ch].join('|'))) return; const o = out.get(m.user_id) || { member: m, email: [], push: [] }; if (!o[ch].some(e => e.item === item && e.key === key)) o[ch].push({ key, item, ...entry }); out.set(m.user_id, o); };
  const fresh = [...stories].sort((x, y) => Date.parse(y.published_at) - Date.parse(x.published_at));
  for (const m of members) {
    for (const s of fresh) {
      const entry = { title: s.headline, line: s.summary || '', url: SITE + '/story.html?id=' + encodeURIComponent(s.id) };
      if (m.alerts_on !== false) { const h = followHits(m.items, m.muted, s)[0]; if (h) { if (m.plan === 'pro' && m.push) add(m, 'push', 'follow', s.id, { ...entry, why: 'You follow ' + h.label }); add(m, 'email', 'follow', s.id, { ...entry, why: 'You follow ' + h.label }); } }
      for (const a of smart.filter(x => x.user_id === m.user_id)) { const why = smartArticleHit(a, s, m.items); if (!why) continue; for (const ch of channelsFor(a, m)) add(m, ch, a.id, s.id, { ...entry, why }); }
    }
  }
  return [...out.values()];
}
export const channelsFor = (a, m) => m.plan === 'pro' ? (a.channels || ['email']).filter(c => c === 'email' || (c === 'push' && m.push)) : ['email'];
async function members(env, userIds) {
  const f = userIds ? '&user_id=in.' + inList(userIds) : '';
  const [contacts, watch, plans, subs] = await Promise.all([
    get(env, 'alert_contacts?select=user_id,email,alerts_on,muted,unsubscribe_token&unsubscribed_at=is.null' + f),
    get(env, 'watchlists?select=user_id,items' + f), get(env, 'member_plans?select=user_id,plan' + f),
    pushReady(env) ? get(env, 'push_subscriptions?select=user_id,endpoint,p256dh,auth' + f) : []]);
  const W = new Map(watch.map(w => [w.user_id, w.items])), P = new Map(plans.map(p => [p.user_id, p.plan]));
  return contacts.map(c => ({ ...c, items: W.get(c.user_id) || {}, plan: P.get(c.user_id) || 'free', push: subs.filter(s => s.user_id === c.user_id) }));
}
async function emailsToday(env, now) {
  const r = await sb(env, 'alert_sends?select=user_id&channel=eq.email&sent_at=gte.' + new Date(now).toISOString().slice(0, 10), { headers: { Prefer: 'count=exact', Range: '0-0' } }).catch(() => null);
  const n = r && Number((r.headers.get('content-range') || '').split('/')[1]); return Number.isFinite(n) ? n : 0;
}
async function deliver(env, groups, now) {
  const limit = Number(env.BREVO_DAILY_LIMIT || 280); let budget = limit - await emailsToday(env, now), emails = 0, pushes = 0, calls = 0; const rows = [];
  for (const g of groups) {
    if (calls > 40) break;  // Worker subrequest budget
    const m = g.member, unsub = `https://api.investedia.com/v1/alerts/unsubscribe?u=${encodeURIComponent(m.user_id)}&t=${encodeURIComponent(m.unsubscribe_token)}`;
    if (g.email.length && budget > 0) {
      const items = g.email.slice(0, 5); calls++;
      try { const st = await sendEmail(env, m.email, alertEmail(items, unsub), unsub); if (st >= 200 && st < 300) { emails++; budget--; for (const i of items) rows.push({ user_id: m.user_id, alert_key: i.key, item_id: i.item, channel: 'email' }); } } catch {}
    }
    for (const i of g.push.slice(0, 2)) for (const s of m.push.slice(0, 2)) { calls++;
      try { const st = await sendPush(s, { title: i.why, body: i.title, url: i.url, tag: 'inv-' + i.item }, env); if (st >= 200 && st < 300) { pushes++; rows.push({ user_id: m.user_id, alert_key: i.key, item_id: i.item, channel: 'push' }); } else if (st === 404 || st === 410) await sb(env, 'push_subscriptions?endpoint=eq.' + encodeURIComponent(s.endpoint), { method: 'DELETE' }); } catch {} }
  }
  const seen = new Set(), uniq = rows.filter(r => { const k = [r.user_id, r.alert_key, r.item_id, r.channel].join('|'); return !seen.has(k) && seen.add(k); });
  if (uniq.length) await sb(env, 'alert_sends', { method: 'POST', headers: { Prefer: 'resolution=ignore-duplicates' }, body: JSON.stringify(uniq) });
  return { emails, pushes, budget_left: budget };
}
// After each news ingest: article alerts + article-type smart alerts.
export async function runAlerts(env, stories, now = Date.now()) {
  if (!alertsReady(env) || !stories?.length) return { skipped: true };
  const recent = stories.filter(s => now - Date.parse(s.published_at) < 3 * 36e5); if (!recent.length) return { emails: 0 };
  const [ms, smart, sends] = await Promise.all([members(env), get(env, 'smart_alerts?select=id,user_id,type,params,channels&active=eq.true&type=in.(market_moving,sector)'),
    get(env, 'alert_sends?select=user_id,alert_key,item_id,channel&item_id=in.' + inList(recent.map(s => s.id)))]);
  const sent = new Set(sends.map(r => [r.user_id, r.alert_key, r.item_id, r.channel].join('|')));
  return deliver(env, plan(recent, ms, smart, sent), now);
}
// Every ~10 minutes from the price cron: price-move smart alerts against the Worker's own price snapshot.
export async function runPriceAlerts(env, px, now = Date.now()) {
  if (!alertsReady(env) || !px) return { skipped: true };
  const smart = await get(env, 'smart_alerts?select=id,user_id,type,params,channels&active=eq.true&type=eq.price'); if (!smart.length) return { emails: 0 };
  const hits = smart.map(a => ({ a, h: priceHit(a, px[sym(a.params?.symbol)] || px[a.params?.symbol]) })).filter(x => x.h); if (!hits.length) return { emails: 0 };
  const [ms, sends] = await Promise.all([members(env, [...new Set(hits.map(x => x.a.user_id))]), get(env, 'alert_sends?select=user_id,alert_key,item_id,channel&item_id=in.' + inList(hits.map(x => x.h.item)))]);
  const sent = new Set(sends.map(r => [r.user_id, r.alert_key, r.item_id, r.channel].join('|'))), groups = new Map();
  for (const { a, h } of hits) { const m = ms.find(x => x.user_id === a.user_id); if (!m) continue; const g = groups.get(m.user_id) || { member: m, email: [], push: [] };
    for (const ch of channelsFor(a, m)) if (!sent.has([m.user_id, a.id, h.item, ch].join('|'))) g[ch].push({ key: a.id, item: h.item, title: h.title, line: h.line, url: h.url, why: h.why }); groups.set(m.user_id, g); }
  return deliver(env, [...groups.values()], now);
}
export async function unsubscribe(url, env) {
  const u = url.searchParams.get('u'), t = url.searchParams.get('t');
  if (!/^[0-9a-f-]{36}$/i.test(u || '') || !/^[0-9a-f-]{36}$/i.test(t || '') || !env.SUPABASE_SERVICE_KEY) return { status: 400, html: page('This link is not valid.') };
  const r = await sb(env, `alert_contacts?user_id=eq.${u}&unsubscribe_token=eq.${t}`, { method: 'PATCH', headers: { Prefer: 'return=representation' }, body: JSON.stringify({ unsubscribed_at: new Date().toISOString() }) });
  const rows = r.ok ? await r.json() : []; return rows.length ? { status: 200, html: page('You will not get alert emails from Investedia any more. You can turn them back on in the bell menu on investedia.com.') } : { status: 404, html: page('This link has expired.') };
}
const page = msg => `<!doctype html><meta name="viewport" content="width=device-width"><title>Investedia alerts</title><body style="font-family:Inter,system-ui,sans-serif;background:#0a0a0b;color:#f4f4f5;display:grid;place-items:center;min-height:90vh;margin:0"><div style="max-width:420px;padding:24px;text-align:center"><h1 style="font-size:22px">Investedia</h1><p style="color:#a1a1aa;line-height:1.5">${msg}</p><a href="${SITE}" style="color:#ff7a1a">Back to investedia.com</a></div>`;

// Owner preview: send the three email layouts to one address. Protected by the ingest token (only GitHub Actions has it).
export async function sendPreview(req, env) {
  const auth = req.headers.get('Authorization') || '';
  if (!env.INGEST_TOKEN || auth !== 'Bearer ' + env.INGEST_TOKEN) return { status: 401, body: { error: 'unauthorized' } };
  if (!env.BREVO_API_KEY || !env.BREVO_SENDER_EMAIL) return { status: 503, body: { error: 'email not configured' } };
  let b = {}; try { b = await req.json(); } catch {}
  const to = String(b.to || '').trim(); if (!/^[^@\s]{1,64}@[^@\s]{1,190}\.[a-z]{2,}$/i.test(to)) return { status: 422, body: { error: 'bad address' } };
  const unsub = SITE + '/watchlist.html', U = SITE + '/news.html';
  const sets = [
    [{ why: 'You follow Brazil', title: 'Preview · Brazil central bank holds rates as inflation eases', line: 'This is a preview of a single article alert. Real alerts use real Investedia articles.', url: U }],
    [{ why: 'You follow Nvidia', title: 'Preview · Several alerts in one email', line: 'Up to five articles arrive together in one email per news update.', url: U },
     { why: 'Market-moving', title: 'Preview · A market-moving article', line: 'Smart alert: market-moving only.', url: U },
     { why: 'Sector · Commodities', title: 'Preview · A sector article', line: 'Smart alert: sector news.', url: U }],
    [{ why: 'Price move · -6.20% today', title: 'Preview · Nvidia down 6.2%', line: 'Your alert: moves up or down more than 5% in a day.', url: SITE + '/markets.html' }]];
  const out = []; for (const items of sets) out.push(await sendEmail(env, to, alertEmail(items, unsub), unsub));
  return { status: 200, body: { ok: out.every(s => s >= 200 && s < 300), statuses: out } };
}
