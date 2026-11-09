import { FEEDS, PROMPT } from './feeds.js';
import { COUNTRIES, SYM, CATS } from './ref.js';
import { fetchFeed } from '../providers/feeds.js';
import { generate } from '../providers/gemini.js';
import { canon, contentHash, dedupe, score } from './newscore.js';
import { day, envelope } from './core.js';

export const PROVIDER = { id: 'rss+gemini', licensed: false, delayed: false };  // publisher RSS terms are unclear for commercial use: see DATA-LICENSING.md
export const KEEP = 40, MAX_CAND = 24, MAX_NEW = 10, SEEN_MS = 3 * 86400e3, NEWS_WRITE_BUDGET = 200  // KV puts per day (the stories blob and the small index each count);
const NOISE = /\b(stock to buy|stocks to buy|price target|horoscope|celebrity|football|soccer)\b/i;
const KINDS = new Set(['country', 'company', 'asset', 'sector']), DIRS = new Set(['up', 'down', 'mixed', 'unclear']);

// same bounds as validate_analysis() in update_globe_news.py
export function validateImpacts(raw, marketMoving) {
  const impacts = [];
  for (const r of Array.isArray(raw?.impacts) ? raw.impacts : []) {
    if (!r || typeof r !== 'object' || !KINDS.has(r.kind) || typeof r.name !== 'string' || !r.name.trim() || typeof r.why !== 'string' || !r.why.trim()) continue;
    const country = String(r.country || '').trim().toUpperCase(); if (!COUNTRIES[country]) continue;
    impacts.push({ kind: r.kind, name: r.name.trim().slice(0, 80), country, ticker: typeof r.ticker === 'string' && /^[A-Za-z0-9.^=_-]{1,32}$/.test(r.ticker) ? r.ticker : null, direction: DIRS.has(r.direction) ? r.direction : 'unclear', why: r.why.trim().slice(0, 200) });
    if (impacts.length === 4) break;
  }
  return { impacts, why_moved: marketMoving && typeof raw?.why_moved === 'string' && raw.why_moved.trim() ? raw.why_moved.trim().slice(0, 400) : null };
}

const sid = (url) => 'w' + [...url].reduce((h, c) => (Math.imul(h, 31) + c.charCodeAt(0)) >>> 0, 7).toString(36).padStart(7, '0');

// Gemini rows -> stories. Anything malformed is dropped, never repaired by guessing.
export function buildStories(rows, cands, nowIso) {
  const out = [];
  for (const p of Array.isArray(rows) ? rows : []) {
    try {
      const mem = (Array.isArray(p.members) ? p.members : []).filter(m => Number.isInteger(m) && m >= 0 && m < cands.length);
      const iso2 = String(p.country || '').toUpperCase(), ctry = COUNTRIES[iso2];
      if (!mem.length || !ctry || !CATS.includes(p.category) || typeof p.headline !== 'string') continue;
      const lat = +p.lat, lon = +p.lon; if (!(Math.abs(lat) <= 90) || !(Math.abs(lon) <= 180)) continue;
      const srcs = mem.map(m => ({ name: cands[m].source, url: cands[m].url }));
      const mm = !!p.market_moving;
      const ents = (Array.isArray(p.entities) ? p.entities : []).slice(0, 3).filter(e => e && e.name).map(e => { const t = e.ticker || null; return { name: String(e.name).slice(0, 60), ticker: t, ...(t && SYM[String(t).toUpperCase()] ? { sym: SYM[String(t).toUpperCase()] } : {}) }; });
      out.push({ id: sid(cands[mem[0]].url), headline: p.headline.slice(0, 110), summary: String(p.summary || '').slice(0, 400), why: String(p.why || '').slice(0, 400), category: p.category,
        importance: Math.max(1, Math.min(3, parseInt(p.importance, 10) || 1)), flag: null, market_moving: mm,
        location: { place: String(p.place || ctry[0]).slice(0, 60), country: ctry[0], lat: +lat.toFixed(3), lon: +lon.toFixed(3), region: ctry[1] },
        entities: ents, links: [], source: srcs[0], sources: srcs, published_at: mem.map(m => cands[m].published).sort()[0], retrieved_at: nowIso,
        official: mem.some(m => cands[m].kind === 'official'), ai_summary: true, score: Math.max(...mem.map(m => cands[m].score || 0)), content_hash: cands[mem[0]].chash, via: 'worker', ...validateImpacts(p, mm) });
    } catch { /* skip this row */ }
  }
  return out;
}

const emptyNewsStats = (now) => ({ day: day(now), writes: 0, runs: 0, failures: 0, feeds_failed: 0, gemini_calls: 0, gemini_failures: 0, new_articles: 0 });

const fnv = (s) => { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h.toString(36); };
const SEEN_MAX = 2500;

// One cron run. KV layout keeps the common run (nothing new) cheap: 'newsx' (small index: seen hashes, known headlines, stats) is read every run;
// 'news' (the stories, the big blob) is read and written only when there is something to add.
// Order: fetch feeds -> cheap filters (seen, noise, dedupe, score) -> Gemini only for what is left -> KV writes only when something changed.
export async function refreshNews(env, now = Date.now(), fx = {}) {
  const fetchFn = fx.fetch || fetch, gen = fx.generate || generate;
  let ix = null; try { ix = JSON.parse(await env.PRICES.get('newsx')); } catch {}
  ix = ix || { seen: '', known: [], urls: '', stats: null };
  const stats = ix.stats && ix.stats.day === day(now) ? ix.stats : emptyNewsStats(now); stats.runs++;
  const seen = new Map(String(ix.seen || '').split(' ').filter(Boolean).map(x => { const [k, h, t] = x.split('.'); return [k, { h, t: +t }]; }));
  for (const [k, v] of seen) if (now - v.t * 6e4 > SEEN_MS) seen.delete(k);
  const known = ix.known || [], knownUrls = new Set(String(ix.urls || '').split(' '));
  const res = await Promise.allSettled(FEEDS.map(f => fetchFeed(f, now, fetchFn)));
  const raw = []; res.forEach(r => { if (r.status === 'fulfilled') raw.push(...r.value); else stats.feeds_failed++; });
  const fresh = [];
  for (const c of raw) { const u = fnv(canon(c.url)); c.chash = contentHash(c); c.cu = u; if (knownUrls.has(u) || NOISE.test(c.title)) continue; if (seen.get(u)?.h === c.chash) continue; fresh.push(c); }
  const { kept } = dedupe(fresh, known, now);
  for (const c of kept) c.score = score(c, now, c.dups || 0);
  const cands = kept.sort((a, b) => b.score - a.score).slice(0, MAX_CAND);
  let added = [], model = null, geminiOk = !cands.length;
  if (cands.length) {
    stats.gemini_calls++;
    try {
      const listing = JSON.stringify(cands.map((c, i) => ({ i, title: c.title, source: c.source, ...(c.hint ? { about: c.hint } : {}), ...(c.desc ? { description: c.desc } : {}) })));
      const prompt = PROMPT.replace('{n}', String(MAX_NEW)).replace('{cats}', CATS.join(', ')).replace('{topics}', '(none: use null)').replace('{cands}', () => listing);
      const g = await gen(prompt, env, fetchFn); model = g.model; geminiOk = true;
      added = buildStories(g.json, cands, new Date(now).toISOString().replace(/\.\d+Z$/, 'Z')).slice(0, MAX_NEW);
    } catch (e) { stats.gemini_failures++; stats.last_error = String(e.message || e).slice(0, 160); }
  }
  if (geminiOk) { // a failed Gemini call must not mark candidates as judged; duplicates of a judged candidate count as judged, candidates cut by the cap do not
    const keptSet = new Set(kept), cut = new Set(kept.filter(c => !cands.includes(c)));
    for (const c of fresh) if (!cut.has(c) && (cands.includes(c) || !keptSet.has(c))) seen.set(c.cu, { h: c.chash, t: Math.floor(now / 6e4) });
  }
  stats.new_articles += added.length;
  if (!raw.length) stats.failures++;
  let wrote = false, stories = null;
  const room = stats.writes + (added.length ? 2 : 1) <= NEWS_WRITE_BUDGET;
  if (added.length && room) {
    let cur = []; try { cur = JSON.parse(await env.PRICES.get('news'))?.stories || []; } catch {}
    stories = [...new Map([...added, ...cur].map(s => [s.id, s])).values()].sort((a, b) => (a.published_at < b.published_at ? 1 : -1)).slice(0, KEEP);
    stats.writes++; await env.PRICES.put('news', JSON.stringify({ t: now, stories, model })); wrote = true;
  }
  if ((added.length || (geminiOk && cands.length)) && room) {
    const sx = stories || []; const newKnown = stories ? stories.map(s => [s.headline, Date.parse(s.published_at)]) : known;
    const urls = stories ? stories.flatMap(s => s.sources.map(x => fnv(canon(x.url)))).join(' ') : ix.urls;
    stats.writes++;
    await env.PRICES.put('newsx', JSON.stringify({ t: now, seen: [...seen].slice(-SEEN_MAX).map(([k, v]) => `${k}.${v.h}.${v.t}`).join(' '), known: newKnown, urls, stats }));
    wrote = true;
  }
  return { fetched: raw.length, candidates: cands.length, added: added.length, wrote, model, stats, feeds_failed: stats.feeds_failed, gemini_ok: geminiOk };
}

export async function handleNews(env, now = Date.now()) {
  let st = null; try { st = JSON.parse(await env.PRICES.get('news')); } catch {}
  if (!st || !Array.isArray(st.stories) || !st.stories.length) return { status: 503, body: { error: 'no data yet', meta: { state: 'unavailable', provider: PROVIDER.id, version: 1 } } };
  return { status: 200, body: envelope({ stories: st.stories }, { provider: PROVIDER, snapT: st.t, now, ttl: 30, extra: { count: st.stories.length, model: st.model || null, note: 'newest AI-enriched priority articles; the client merges them with the static broad feed' } }) };
}
// Globe events are a compact view of the same articles: no second pipeline, no extra KV writes.
export async function handleGlobe(env, now = Date.now()) {
  const r = await handleNews(env, now); if (r.status !== 200) return r;
  const events = r.body.data.stories.map(s => ({ id: s.id, headline: s.headline, category: s.category, importance: s.importance, market_moving: s.market_moving, place: s.location.place, country: s.location.country, lat: s.location.lat, lon: s.location.lon, published_at: s.published_at, source: s.source.name }));
  return { status: 200, body: { data: { events }, meta: { ...r.body.meta, count: events.length } } };
}

// ---- Ingest: the GitHub robot (which already does the heavy CPU work) pushes its newest articles here instead of waiting for a commit and a Pages deploy. ----
export const timingSafeEqual = (a, b) => { a = String(a); b = String(b); let d = a.length ^ b.length; for (let i = 0; i < Math.max(a.length, b.length); i++) d |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0); return d === 0; };
const REQ = ['id', 'headline', 'category', 'published_at', 'source', 'location'];
export function validateIngest(body) {
  if (!body || !Array.isArray(body.stories)) return 'stories must be an array';
  if (!body.stories.length) return 'refusing an empty list';
  if (body.stories.length > 80) return 'too many stories';
  const ids = new Set();
  for (const s of body.stories) {
    if (!s || typeof s !== 'object' || REQ.some(k => !s[k])) return 'story missing required fields';
    if (ids.has(s.id)) return 'duplicate id ' + s.id; ids.add(s.id);
    if (!Number.isFinite(Date.parse(s.published_at))) return 'bad published_at';
    if (!Number.isFinite(+s.location.lat) || !Number.isFinite(+s.location.lon)) return 'bad location';
  }
  return null;
}
export async function ingestNews(req, env, now = Date.now()) {
  if (!env.INGEST_TOKEN) return { status: 503, body: { error: 'ingest not configured' } };
  const auth = req.headers.get('Authorization') || '';
  if (!timingSafeEqual(auth, 'Bearer ' + env.INGEST_TOKEN)) return { status: 401, body: { error: 'unauthorized' } };
  const text = await req.text(); if (text.length > 400_000) return { status: 413, body: { error: 'too large' } };
  let body; try { body = JSON.parse(text); } catch { return { status: 400, body: { error: 'invalid json' } }; }
  const bad = validateIngest(body); if (bad) return { status: 422, body: { error: bad } };
  const stories = body.stories.slice().sort((a, b) => (a.published_at < b.published_at ? 1 : -1)).slice(0, KEEP);
  let cur = null; try { cur = JSON.parse(await env.PRICES.get('news')); } catch {}
  if (cur && JSON.stringify(cur.stories.map(s => s.id)) === JSON.stringify(stories.map(s => s.id))) return { status: 200, body: { ok: true, written: false, reason: 'unchanged' } };
  await env.PRICES.put('news', JSON.stringify({ t: now, stories, model: 'github-ingest', generated_at: body.generated_at || null }));
  return { status: 200, body: { ok: true, written: true, count: stories.length } };
}
