// JavaScript mirror of news_core.py (canonical URL, title similarity, scoring). Kept in step by test/newscore.test.mjs, which checks both
// languages against the same golden vectors (tests/fixtures/news-core-vectors.json, written by tools/gen-news-vectors.py).
const TRACKING = /^(utm_|fbclid|gclid|ref$|ref_|cmp|ito$|at_|ocid|taid|mc_|igshid|source$|guccounter)/i;
const STOP = new Set(['the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was', 'has', 'have', 'its', 'new', 'says', 'said', 'after', 'over', 'into', 'will', 'amid']);

export function canon(u) {
  try {
    const p = new URL(u.trim());
    const q = [...p.searchParams].filter(([k]) => !TRACKING.test(k)).sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
    const path = p.pathname.replace(/\/+$/, '').replace(/\/amp$/i, '');
    return (p.host.toLowerCase().replace(/^www\./, '') + path + (q.length ? '?' + q.map(([k, v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v)).join('&') : '')).toLowerCase();
  } catch { return u; }
}
const NC = new Map(), EC = new Map();  // per-title caches: dedupe compares every title with many others, and re-tokenising was most of the CPU
export const norm = (t) => { t = String(t || ''); let v = NC.get(t); if (!v) { v = normRaw(t); if (NC.size > 2000) NC.clear(); NC.set(t, v); } return v; };
const normRaw = (t) => new Set((String(t || '').toLowerCase().replace(/[^a-z0-9 ]/g, ' ').split(' ')).filter(w => w.length > 2 && !STOP.has(w)));
const inter = (a, b) => { let n = 0; for (const x of a) if (b.has(x)) n++; return n; };
export const jaccard = (a, b) => { const i = inter(a, b); return i / Math.max(1, a.size + b.size - i); };
export function entities(t) { t = String(t || ''); let v = EC.get(t); if (!v) { v = entitiesRaw(t); if (EC.size > 2000) EC.clear(); EC.set(t, v); } return v; }
function entitiesRaw(t) {
  const s = new Set(); for (const m of String(t || '').matchAll(/\b(?:[A-Z][A-Za-z]{2,}|\d[\d.,]*%?)\b/g)) { const w = m[0].toLowerCase(); if (!STOP.has(w)) s.add(w); } return s;
}
export function sameEvent(a, b, hoursApart) {
  const wa = norm(a), wb = norm(b);
  if (wa.size < 3 || wb.size < 3) return false;
  const j = jaccard(wa, wb);
  if (j > .55) return true;
  if (hoursApart <= 12) {
    const ea = entities(a), eb = entities(b), shared = inter(ea, eb);
    const num = [...ea].some(w => eb.has(w) && /^\d/.test(w));
    if ((shared >= 3 && jaccard(ea, eb) >= .5 && j > .3) || (shared >= 2 && num && j > .3)) return true;
    if (j > .4 && inter(wa, wb) / Math.max(1, Math.min(wa.size, wb.size)) >= .8) return true;
  }
  return false;
}
export const contentHash = (c) => { // small FNV-1a hash (Workers have no sync sha1); only used to detect changed text
  const s = `${c.title || ''}|${(c.desc || '').slice(0, 400)}`; let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h.toString(36);
};

const MACRO = /\b(rate (?:decision|cut|hike)|interest rates?|inflation|cpi|ppi|gdp|payrolls?|unemployment|fomc|ecb|central bank|monetary policy|tariffs?|trade (?:deal|war)|opec|sanctions?|recession|treasury|yields?|stimulus|debt ceiling)\b/i;
const SEVERE = /\b(crash|plunge[sd]?|surge[sd]?|soar[sd]?|tumble[sd]?|collapse[sd]?|default|bankrupt\w*|emergency|halt(?:ed|s)?|downgrade[sd]?|record (?:high|low)|shock|crisis|bank run|outage|attack|invasion|ceasefire)\b/i;
const EXPOSURE = /\b(oil|brent|crude|gas|gold|copper|bitcoin|ether(?:eum)?|nasdaq|s&p|dow|dollar|euro|yen|yuan|sterling|nvidia|apple|microsoft|tesla|amazon|alphabet|meta|tsmc|asml|earnings|ipo|merger|acquisition|guidance)\b/i;
const RELEVANT = /\b(market|markets|stocks?|shares|bonds?|currency|commodit\w+|earnings|economy|economic|bank|fund|invest\w*|trade|price[sd]?|profit|revenue|oil|bitcoin|crypto)\b/gi;
const GEO = /\b(u\.?s\.?|united states|china|europe|eurozone|japan|britain|uk|germany|india)\b/i;
export const authority = (c) => c.kind === 'official' ? 1 : .7;
export function score(c, nowMs, dups = 0) {
  const t = `${c.title || ''} ${(c.desc || '').slice(0, 200)}`;
  const mins = c.published ? Math.max(0, (nowMs - Date.parse(c.published)) / 60000) : 1440;
  const recency = Math.pow(Math.max(0, 1 - mins / 720), 1.5);
  const rel = Math.min(1, .35 + .2 * new Set((t.match(RELEVANT) || []).map(x => x.toLowerCase())).size);
  const raw = .26 * authority(c) + .16 * rel + .20 * recency + .10 * (EXPOSURE.test(t) ? 1 : 0) + .14 * (MACRO.test(t) ? 1 : 0) + .08 * (SEVERE.test(t) ? 1 : 0) + .06 * (GEO.test(t) ? 1 : .4);
  return Math.round(Math.max(0, 100 * raw - 6 * Math.min(dups, 4)) * 10) / 10;
}

// Keeps one article per event, most authoritative first, then earliest. known: [[title, publishedMs]]
export function dedupe(items, known, nowMs) {
  const order = [...items].sort((a, b) => authority(b) - authority(a) || (a.published < b.published ? -1 : 1));
  const kept = [], urls = new Set(); let dropped = 0;
  for (const c of order) {
    const cu = canon(c.url); if (urls.has(cu)) { dropped++; continue; }
    const pub = c.published ? Date.parse(c.published) : nowMs;
    const hit = kept.find(k => sameEvent(c.title, k.title, Math.abs(pub - Date.parse(k.published)) / 3.6e6));
    if (hit) { hit.dups = (hit.dups || 0) + 1; urls.add(cu); dropped++; continue; }
    if (known.some(([t, kp]) => sameEvent(c.title, t, Math.abs(pub - kp) / 3.6e6))) { urls.add(cu); dropped++; continue; }
    urls.add(cu); kept.push(c);
  }
  return { kept, dropped };
}
