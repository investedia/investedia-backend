import test from 'node:test';
import assert from 'node:assert/strict';
import { fakeKV, rssXml } from './helpers.mjs';
import { parseFeed, parseTime } from '../providers/feeds.js';
import { refreshNews, handleNews, handleGlobe, buildStories, validateImpacts } from '../v1/news.js';

const NOW = Date.UTC(2026, 9, 28, 14, 0, 0);
const items = (n, base = 'Central bank decision') => Array.from({ length: n }, (_, i) => ({ title: `${base} number ${i} on interest rates and inflation`, url: `https://example.org/a${i}?utm_source=x`, t: NOW - (i + 1) * 60e3, desc: 'Policy makers met today' }));
const feedFetch = (its, status = 200) => async (url) => ({ ok: status === 200, status, text: async () => rssXml(its) });
const geminiRows = (cands) => cands.slice(0, 3).map((c, i) => ({ members: [i], headline: 'Rates decision ' + i, summary: 's', why: 'w', category: 'economy', importance: 2, market_moving: true, place: 'Frankfurt', country: 'DE', lat: 50.1, lon: 8.6, entities: [{ name: 'ECB', ticker: null }],
  impacts: [{ kind: 'asset', name: 'Euro', country: 'DE', ticker: 'EURUSD=X', direction: 'up', why: 'Higher rates support the currency' }, { kind: 'bad' }], why_moved: 'Moved on the decision' }));
const genOk = async (prompt) => { const m = JSON.parse(prompt.slice(prompt.indexOf('[{"i":0'))); return { model: 'm1', json: geminiRows(m) }; };

test('parseFeed: newest items only, CDATA decoded, tracking kept for later canonicalisation, future times clamped, bad rows skipped', () => {
  const xml = rssXml([...items(3), { title: 'no link', url: 'ftp://x', t: NOW }, { title: 'future', url: 'https://f.com/1', t: NOW + 9e6 }, { title: 'ancient', url: 'https://f.com/2', t: NOW - 9 * 86400e3 }]);
  const out = parseFeed(xml, { nowMs: NOW });
  assert.equal(out.length, 4); assert.equal(out[0].desc, 'Policy makers met today'); assert.equal(out[3].published, new Date(NOW).toISOString().replace(/\.\d+Z$/, 'Z'));
  assert.equal(parseFeed('<html>broken', { nowMs: NOW }).length, 0); assert.equal(parseFeed(null).length, 0); assert.equal(parseTime('garbage', NOW), null);
  assert.equal(parseFeed(xml, { nowMs: NOW, max: 2 }).length, 2);
});
test('validateImpacts bounds and drops bad rows', () => {
  const v = validateImpacts({ impacts: [{ kind: 'bad' }, { kind: 'asset', name: 'X', country: 'ZZ', why: 'w' }, { kind: 'asset', name: 'Y', country: 'US', why: 'w'.repeat(300), direction: ['x'], ticker: '<s>' }], why_moved: 'ok' }, true);
  assert.equal(v.impacts.length, 1); assert.equal(v.impacts[0].direction, 'unclear'); assert.equal(v.impacts[0].ticker, null); assert.equal(v.impacts[0].why.length, 200);
  assert.equal(validateImpacts({ why_moved: 'x' }, false).why_moved, null);
});
test('buildStories rejects invalid country/category/coordinates', () => {
  const c = [{ source: 'S', url: 'https://a.com/1', kind: 'news', published: '2026-10-28T13:00:00Z', score: 50 }];
  const good = { members: [0], headline: 'h', category: 'economy', country: 'US', lat: 38.9, lon: -77 };
  assert.equal(buildStories([good], c, 'x').length, 1);
  for (const bad of [{ country: 'ZZ' }, { category: 'sports' }, { lat: 999 }, { members: [5] }, { headline: 7 }]) assert.equal(buildStories([{ ...good, ...bad }], c, 'x').length, 0);
  assert.equal(buildStories('nope', c, 'x').length, 0);
});
test('a run writes one blob, serves /v1/news and /v1/globe, and never reprocesses seen candidates', async () => {
  const env = { PRICES: fakeKV() }, its = items(5);
  const r = await refreshNews(env, NOW, { fetch: feedFetch(its), generate: genOk });
  assert.ok(r.added > 0 && r.wrote); assert.equal(env.PRICES.puts, 2);  // stories blob + small index
  const n = await handleNews(env, NOW + 1000); assert.equal(n.status, 200); assert.equal(n.body.meta.state, 'delayed'); assert.ok(n.body.data.stories[0].via === 'worker');
  const g = await handleGlobe(env, NOW + 1000); assert.ok(g.body.data.events[0].lat);
  let calls = 0; const r2 = await refreshNews(env, NOW + 300e3, { fetch: feedFetch(its), generate: async (...a) => { calls++; return genOk(...a); } });
  assert.equal(calls, 0); assert.equal(r2.candidates, 0); assert.equal(r2.wrote, false); assert.equal(env.PRICES.puts, 2);
});
test('Gemini failure: candidates stay unjudged and nothing is written over good data', async () => {
  const env = { PRICES: fakeKV() };
  await refreshNews(env, NOW, { fetch: feedFetch(items(5)), generate: genOk });
  const before = env.PRICES.m.get('news') + env.PRICES.m.get('newsx');
  const r = await refreshNews(env, NOW + 300e3, { fetch: feedFetch(items(5, 'Different wording about exports')), generate: async () => { throw new Error('quota'); } });
  assert.equal(r.gemini_ok, false); assert.equal(r.wrote, false); assert.equal(env.PRICES.m.get('news') + env.PRICES.m.get('newsx'), before);
  const r3 = await refreshNews(env, NOW + 600e3, { fetch: feedFetch(items(5, 'Different wording about exports')), generate: genOk });
  assert.ok(r3.candidates > 0);
});
test('all feeds failing keeps the previous data and writes nothing', async () => {
  const env = { PRICES: fakeKV() };
  await refreshNews(env, NOW, { fetch: feedFetch(items(3)), generate: genOk }); const before = env.PRICES.m.get('news') + env.PRICES.m.get('newsx');
  const r = await refreshNews(env, NOW + 300e3, { fetch: feedFetch([], 500), generate: genOk });
  assert.equal(r.fetched, 0); assert.equal(r.wrote, false); assert.equal(env.PRICES.m.get('news') + env.PRICES.m.get('newsx'), before);
  assert.equal((await handleNews({ PRICES: fakeKV() }, NOW)).status, 503);
});
test('malformed Gemini output adds nothing and does not crash', async () => {
  const env = { PRICES: fakeKV() };
  const r = await refreshNews(env, NOW, { fetch: feedFetch(items(3)), generate: async () => ({ model: 'm', json: { not: 'an array' } }) });
  assert.equal(r.added, 0); assert.ok(env.PRICES.puts <= 1);  // at most the index (candidates were judged, nothing usable came back)
});
test('daily news write budget is respected', async () => {
  const env = { PRICES: fakeKV() }; let t = NOW;
  await refreshNews(env, t, { fetch: feedFetch(items(3)), generate: genOk });
  const st = JSON.parse(env.PRICES.m.get('newsx')); st.stats.writes = 200; env.PRICES.m.set('newsx', JSON.stringify(st));
  const r = await refreshNews(env, t + 300e3, { fetch: feedFetch(items(4, 'New topic about oil exports')), generate: genOk }); assert.equal(r.wrote, false);
});

import { ingestNews, validateIngest, timingSafeEqual } from '../v1/news.js';
const story = (id, t = '2026-10-28T13:00:00Z') => ({ id, headline: 'h', category: 'economy', published_at: t, source: { name: 's' }, location: { lat: 1, lon: 2 } });
const post = (body, token = 'tok') => ({ headers: new Headers(token ? { Authorization: 'Bearer ' + token } : {}), text: async () => typeof body === 'string' ? body : JSON.stringify(body) });
test('ingest: auth, validation, empty refusal, unchanged skip, write', async () => {
  const env = { PRICES: fakeKV(), INGEST_TOKEN: 'tok' };
  assert.equal((await ingestNews(post({ stories: [story('a')] }, 'bad'), env)).status, 401);
  assert.equal((await ingestNews(post({ stories: [story('a')] }, ''), env)).status, 401);
  assert.equal((await ingestNews(post({ stories: [story('a')] }), { PRICES: fakeKV() })).status, 503);
  assert.equal((await ingestNews(post('{bad'), env)).status, 400);
  assert.equal((await ingestNews(post({ stories: [] }), env)).status, 422);
  assert.equal((await ingestNews(post({ stories: [story('a'), story('a')] }), env)).status, 422);
  assert.equal((await ingestNews(post({ stories: [{ id: 'x' }] }), env)).status, 422);
  assert.equal(env.PRICES.puts, 0);
  const ok = await ingestNews(post({ stories: [story('a'), story('b', '2026-10-28T12:00:00Z')] }), env); assert.equal(ok.body.written, true); assert.equal(env.PRICES.puts, 1);
  const again = await ingestNews(post({ stories: [story('b', '2026-10-28T12:00:00Z'), story('a')] }), env); assert.equal(again.body.written, false); assert.equal(env.PRICES.puts, 1);
  assert.equal((await handleNews(env, Date.parse('2026-10-28T13:01:00Z'))).body.meta.state, 'delayed');
  assert.ok(timingSafeEqual('abc', 'abc') && !timingSafeEqual('abc', 'abd') && !timingSafeEqual('abc', 'ab'));
  assert.equal(validateIngest({ stories: Array.from({ length: 81 }, (_, i) => story('i' + i)) }), 'too many stories');
});
