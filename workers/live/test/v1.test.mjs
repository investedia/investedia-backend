import test from 'node:test';
import assert from 'node:assert/strict';
import { fakeKV, fakeFetch } from './helpers.mjs';
import { parseSpark } from '../providers/yahoo.js';
import { toRow, entry, merge, unchanged, shouldWrite, envelope, stateOf, KEEP_MS, WRITE_BUDGET, rollStats } from '../v1/core.js';
import { refresh, handlePrices, handleStatus, SYMBOLS_BY_GROUP } from '../v1/prices.js';

const NOW = Date.UTC(2026, 9, 28, 14, 0, 0);

test('parseSpark skips bad rows and keeps good ones', () => {
  const q = parseSpark({ A: { symbol: 'A', timestamp: [1], close: [10, null, 11], chartPreviousClose: 10 }, B: null, C: { symbol: 'C', close: [], chartPreviousClose: 5 }, D: { symbol: 'D', close: [0], chartPreviousClose: 5 }, E: 'x' });
  assert.deepEqual(Object.keys(q), ['A']); assert.equal(q.A.p, 11);
  assert.deepEqual(parseSpark(null), {}); assert.deepEqual(parseSpark('x'), {});
});
test('toRow computes the change, inverts when asked, rejects absurd moves', () => {
  assert.deepEqual(toRow({ p: 110, prev: 100, t: 5 }, false, NOW), [110, 10, 5, NOW]);
  assert.equal(toRow({ p: 110, prev: 100, t: 5 }, true, NOW)[1], -10);
  assert.equal(toRow({ p: 1000, prev: 100, t: 5 }, false, NOW), null);
});
test('toRow applies the unit scale (pence and cents quotes) and entry() parses it', () => {
  assert.equal(toRow({ p: 10050, prev: 10000, t: 1 }, false, NOW, 0.01)[0], 100.5);
  assert.equal(entry('SHEL|SHEL.L|0|s|0.01').k, 0.01); assert.equal(entry('AAPL|AAPL|0|s|1').k, 1); assert.equal(entry('X|X|0|s').k, 1);
});
test('merge keeps old rows (stale) up to 7 days and lets fresh rows win', () => {
  const prev = { A: [1, 0, 0, NOW - 1000], OLD: [1, 0, 0, NOW - KEEP_MS - 1] };
  const out = merge(prev, { B: [2, 0, 0, NOW] }, NOW);
  assert.deepEqual(Object.keys(out).sort(), ['A', 'B']);
});
test('unchanged ignores fetch time but sees price changes and new symbols', () => {
  assert.ok(unchanged({ A: [1, 1, 0, 1] }, { A: [1, 1, 0, 999] }));
  assert.ok(!unchanged({ A: [1, 1, 0, 1] }, { A: [2, 1, 0, 1] }));
  assert.ok(!unchanged({ A: [1, 1, 0, 1] }, { A: [1, 1, 0, 1], B: [1, 1, 0, 1] }));
});
test('shouldWrite: changed or heartbeat, and slowed past the daily budget', () => {
  assert.ok(shouldWrite({ changed: true, lastWrite: NOW - 1000, writesToday: 5, now: NOW }));
  assert.ok(!shouldWrite({ changed: false, lastWrite: NOW - 60e3, writesToday: 5, now: NOW }));
  assert.ok(shouldWrite({ changed: false, lastWrite: NOW - 11 * 60e3, writesToday: 5, now: NOW }));
  assert.ok(!shouldWrite({ changed: true, lastWrite: NOW - 5 * 60e3, writesToday: WRITE_BUDGET, now: NOW }));
  assert.ok(shouldWrite({ changed: true, lastWrite: NOW - 16 * 60e3, writesToday: WRITE_BUDGET, now: NOW }));
});
test('state labels', () => { assert.equal(stateOf(NOW - 60e3, NOW), 'delayed'); assert.equal(stateOf(NOW - 20 * 60e3, NOW), 'stale'); assert.equal(stateOf(0, NOW), 'unavailable'); });

test('refresh writes one combined snapshot and /v1/prices serves it with metadata', async () => {
  const env = { PRICES: fakeKV() };
  const r = await refresh(env, NOW, fakeFetch());
  assert.ok(r.ok > 100); assert.equal(env.PRICES.puts, 1);
  const res = await handlePrices(new URL('https://x/v1/prices?group=indices'), env, {}, NOW + 5000);
  assert.equal(res.status, 200); assert.equal(res.body.meta.state, 'delayed'); assert.equal(res.body.meta.group, 'indices');
  assert.ok(Object.keys(res.body.data).every(k => SYMBOLS_BY_GROUP.indices.includes(k)));
  assert.equal(res.body.meta.provider, 'yahoo-spark'); assert.equal(res.body.meta.licensed, false);
});
test('unchanged data is not rewritten (KV budget) until the heartbeat is due', async () => {
  const env = { PRICES: fakeKV() };
  await refresh(env, NOW, fakeFetch()); await refresh(env, NOW + 1000, fakeFetch());  // same 2-minute slot: same symbols, same prices
  assert.equal(env.PRICES.puts, 1);
  const r = await refresh(env, NOW + 11 * 60e3 + 1000, fakeFetch({ prev: 99 })); assert.ok(r.wrote); assert.equal(env.PRICES.puts, 2);
});
test('upstream failure keeps the last good snapshot and counts the failure', async () => {
  const env = { PRICES: fakeKV() };
  await refresh(env, NOW, fakeFetch());
  const before = env.PRICES.m.get('px');
  const r = await refresh(env, NOW + 120e3, fakeFetch({ status: 503 }));
  assert.equal(r.ok, 0); assert.equal(r.wrote, false); assert.equal(env.PRICES.m.get('px'), before);
  const res = await handlePrices(new URL('https://x/v1/prices'), env, {}, NOW + 30 * 60e3);
  assert.equal(res.status, 200); assert.equal(res.body.meta.state, 'stale'); assert.ok(Object.keys(res.body.data).length > 100);
});
test('empty or junk upstream never overwrites; first run with nothing writes nothing', async () => {
  const env = { PRICES: fakeKV() };
  const r = await refresh(env, NOW, fakeFetch({ status: 500 })); assert.equal(env.PRICES.puts, 0); assert.equal(r.wrote, false);
  const res = await handlePrices(new URL('https://x/v1/prices'), env, {}, NOW); assert.equal(res.status, 503);
});
test('junk rows from the provider are skipped, the rest is kept', async () => {
  const env = { PRICES: fakeKV() }; const r = await refresh(env, NOW, fakeFetch({ junk: true })); assert.ok(r.ok > 0 && env.PRICES.puts === 1);
});
test('bad group is a 400; corrupt KV value is a 503, not a crash', async () => {
  const env = { PRICES: fakeKV({ px: JSON.stringify({ t: NOW, p: { A: [1, 1, 0, NOW] } }) }) };
  assert.equal((await handlePrices(new URL('https://x/v1/prices?group=nope'), env, {}, NOW)).status, 400);
  const bad = { PRICES: fakeKV({ px: '{not json' }) }; assert.equal((await handlePrices(new URL('https://x/v1/prices'), bad, {}, NOW)).status, 503);
});
test('status reports exact KV writes and cron counters', async () => {
  const env = { PRICES: fakeKV() }; await refresh(env, NOW, fakeFetch());
  const s = await handleStatus(env, NOW + 1000);
  assert.equal(s.body.kv.writes_today, 1); assert.equal(s.body.cron.runs_today, 1); assert.equal(s.body.cron.failures_today, 0); assert.equal(s.body.limits.cpu_ms_per_invocation_free, 10);
});
test('stats roll over at UTC midnight', () => { assert.equal(rollStats({ day: '2026-10-27', writes: 800 }, NOW).writes, 0); });
test('a run stays well inside the free subrequest limit', async () => {
  let calls = 0; const f = async (...a) => { calls++; return fakeFetch()(...a); };
  await refresh({ PRICES: fakeKV() }, NOW, f); assert.ok(calls <= 20, 'calls ' + calls);
});

test('rows of symbols that left the list are purged from the served snapshot', async () => {
  const env = { PRICES: fakeKV({ px: JSON.stringify({ t: NOW - 1000, p: { OLDGONE: [1, 1, 0, NOW - 1000] }, stats: null }) }) };
  await refresh(env, NOW, fakeFetch());
  const res = await handlePrices(new URL('https://x/v1/prices'), env, {}, NOW + 1000);
  assert.ok(!('OLDGONE' in res.body.data));
});
