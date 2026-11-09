// Investedia live crypto relay (Cloudflare Worker, free plan).
// Visitors call THIS worker (our own subdomain), not Coinbase, so no third party sees their IP.
// One edge-cached snapshot of Coinbase's public market data (top 100 coins) is shared by everyone and refreshed at most every 3 seconds.
const ALLOWED = ['https://investedia.com', 'https://www.investedia.com'];
const TTL = 3, TOP = 100;

const cors = (req) => {
  const o = req.headers.get('Origin') || '';
  const ok = ALLOWED.includes(o) || /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(o);
  return { 'Access-Control-Allow-Origin': ok ? o : ALLOWED[0], 'Vary': 'Origin', 'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Access-Control-Allow-Headers': 'If-None-Match', 'Access-Control-Max-Age': '86400' };
};

// One call returns every Coinbase spot product with price, 24h change, 24h range, volume and market cap.
async function snapshot() {
  const out = {};
  try {
    const r = await fetch('https://api.coinbase.com/api/v3/brokerage/market/products?product_type=SPOT&limit=1000', { headers: { 'User-Agent': 'Investedia live relay (info@investedia.com)' } });
    if (!r.ok) throw new Error(String(r.status));
    const rows = ((await r.json()).products || []).filter(x => x.quote_currency_id === 'USD' && !x.is_disabled && !x.trading_disabled && +x.price > 0 && +x.approximate_quote_24h_volume > 0 && !/^(USDT|USDC|DAI|PYUSD|EURC|GUSD|PAX|TUSD)$/.test(x.base_currency_id));
    rows.sort((x, y) => (+y.market_cap || 0) - (+x.market_cap || 0) || (+y.approximate_quote_24h_volume) - (+x.approximate_quote_24h_volume));
    for (const x of rows.slice(0, TOP)) out[x.product_id] = { p: +x.price, pc: +x.price_percentage_change_24h || 0, h: +x.high_24h || null, l: +x.low_24h || null, v: Math.round(+x.approximate_quote_24h_volume || 0), mc: Math.round(+x.market_cap || 0), n: (x.base_name || x.base_currency_id).replace(/\s+/g, ' ').trim() };
  } catch { /* upstream error: return what we have (nothing) so the caller serves 503 and the page falls back */ }
  return { t: Date.now(), source: 'Coinbase public market data', ttl: TTL, p: out };
}

// ---- Non-crypto prices, news and globe: /v1 (see v1/). Provider adapters live in providers/. ----
import { refresh, handlePrices, handleStatus } from './v1/prices.js';
import { refreshNews, handleNews, handleGlobe, ingestNews } from './v1/news.js';
import { ingestCalls, readCalls } from './v1/calls.js';
export { refresh };
const json = (h, status, body, cache = 'no-store') => new Response(JSON.stringify(body), { status, headers: { ...h, 'Content-Type': 'application/json', 'Cache-Control': cache } });

export default {
  async scheduled(event, env, ctx) {
    const log = (o) => console.log(JSON.stringify(o)), fail = (k) => (e) => log({ cron: k, error: String(e).slice(0, 200) });
    if (event.cron === '*/5 * * * *') { ctx.waitUntil(dispatch(env, event.scheduledTime).then(r => log({ cron: 'dispatch', ...r })).catch(fail('dispatch'))); if (env.NEWS_CRON === 'on') ctx.waitUntil(refreshNews(env).then(r => log({ cron: 'news', fetched: r.fetched, candidates: r.candidates, added: r.added, wrote: r.wrote, gemini_ok: r.gemini_ok, feeds_failed: r.feeds_failed })).catch(fail('news'))); }
    else ctx.waitUntil(refresh(env).then(r => log({ cron: 'prices', ok: r.ok, sent: r.sent, wrote: r.wrote, changed: r.changed, reason: r.reason })).catch(fail('prices')));
  },
  async fetch(req, env, ctx) {
    const h = cors(req), url = new URL(req.url);
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: h });
    if (req.method === 'POST' && url.pathname === '/v1/ingest/news') {
      let r; try { r = await ingestNews(req, env); } catch (e) { console.log(JSON.stringify({ route: 'ingest', error: String(e).slice(0, 200) })); r = { status: 500, body: { error: 'internal' } }; }
      if (r.status === 200 && r.body.written) ctx.waitUntil(Promise.all(['/v1/news', '/v1/globe'].map(path => caches.default.delete(new Request(url.origin + path + '#v1', { method: 'GET' })))));
      return json({}, r.status, r.body);
    }
    if (req.method === 'POST' && url.pathname === '/v1/ingest/calls') {
      let r; try { r = await ingestCalls(req, env); } catch (e) { console.log(JSON.stringify({ route: 'ingest-calls', error: String(e).slice(0, 200) })); r = { status: 500, body: { error: 'internal' } }; }
      if (r.status === 200 && r.body.written) ctx.waitUntil(caches.default.delete(new Request(url.origin + '/v1/calls#v1', { method: 'GET' })));
      return json({}, r.status, r.body);
    }
    if (req.method === 'GET' && url.pathname === '/v1/calls') {
      // 10 s edge cache; ETag so a browser that already has the latest list gets a tiny 304
      const cache = caches.default, key = new Request(url.origin + '/v1/calls#v1', { method: 'GET' });
      let text, etag, hit = await cache.match(key);
      if (hit) { text = await hit.text(); etag = hit.headers.get('ETag'); }
      else { const r = await readCalls(env); if (!r) return json(h, 404, { error: 'no live calls yet' });
        text = r.text; etag = r.etag ? `"${r.etag}"` : null;
        ctx.waitUntil(cache.put(key, new Response(text, { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=10', ...(etag ? { ETag: etag } : {}) } }))); }
      const base = { ...h, 'Cache-Control': 'public, max-age=10', ...(etag ? { ETag: etag } : {}), 'Access-Control-Expose-Headers': 'ETag' };
      if (etag && req.headers.get('If-None-Match') === etag) return new Response(null, { status: 304, headers: base });
      return new Response(text, { headers: { ...base, 'Content-Type': 'application/json' } });
    }
    if (req.method === 'GET' && ['/v1/prices', '/v1/status', '/v1/news', '/v1/globe'].includes(url.pathname)) {
      // 15 s shared edge cache in front of KV: many visitors cost one KV read per location per 15 s
      const cache = caches.default, key = new Request(url.origin + url.pathname + url.search + '#v1', { method: 'GET' });
      const hit = await cache.match(key);
      if (hit) return new Response(await hit.text(), { headers: { ...h, 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=15', 'X-Inv-Cache': 'hit' } });
      let r;
      try { r = url.pathname === '/v1/prices' ? await handlePrices(url, env, ctx) : url.pathname === '/v1/news' ? await handleNews(env) : url.pathname === '/v1/globe' ? await handleGlobe(env) : await handleStatus(env); }
      catch (e) { console.log(JSON.stringify({ route: url.pathname, error: String(e).slice(0, 200) })); r = { status: 500, body: { error: 'internal', meta: { state: 'unavailable', version: 1 } } }; }
      const res = json(h, r.status, r.body, r.status === 200 ? 'public, max-age=15' : 'no-store');
      if (r.status === 200) { res.headers.set('X-Inv-State', r.body.meta?.state || 'ok'); ctx.waitUntil(cache.put(key, new Response(JSON.stringify(r.body), { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=15' } }))); }
      return res;
    }
    if (req.method !== 'GET' || url.pathname !== '/ticker') return new Response('Not found', { status: 404, headers: h });
    const cache = caches.default, key = new Request(url.origin + '/__ticker', { method: 'GET' });
    let res = await cache.match(key);
    if (!res) {
      const snap = await snapshot();
      if (!Object.keys(snap.p).length) return new Response(JSON.stringify({ error: 'upstream unavailable' }), { status: 503, headers: { ...h, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
      res = new Response(JSON.stringify(snap), { headers: { 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${TTL}` } });
      ctx.waitUntil(cache.put(key, res.clone()));
    }
    const body = await res.text();
    return new Response(body, { headers: { ...h, 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${TTL}` } });
  }
};

// Alarm clock for the GitHub robots: GitHub's own schedule often starts runs 10-40 minutes late. Every 5 minutes this starts the
// priority news run, and every 10 minutes the prediction engine (v5). Needs the DISPATCH_TOKEN secret (fine-grained, Actions: write
// on this repository only). Without it nothing happens.
async function dispatch(env, t) {
  if (env.DISPATCH_ENABLED !== 'true' || !env.DISPATCH_TOKEN || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(env.DISPATCH_REPOSITORY || '')) return { skipped: 'dispatch disabled or unconfigured' };
  const min = new Date(t || Date.now()).getUTCMinutes(), wf = ['priority-news.yml', 'engine-v5.yml'], out = {};
  for (const w of wf) {
    const r = await fetch(`https://api.github.com/repos/${env.DISPATCH_REPOSITORY}/actions/workflows/${w}/dispatches`, { method: 'POST',
      headers: { Authorization: `Bearer ${env.DISPATCH_TOKEN}`, Accept: 'application/vnd.github+json', 'User-Agent': 'investedia-live-alarm', 'Content-Type': 'application/json' },
      body: JSON.stringify({ ref: 'main' }) });
    out[w] = r.status;
  }
  return out;
}
