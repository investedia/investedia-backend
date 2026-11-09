// CPU benchmark of one cron run with realistic payloads and a full ~900-symbol KV snapshot. Network waiting is excluded because the fake fetch resolves instantly.
// Node's process.cpuUsage is only an estimate of Cloudflare's isolate CPU (same V8, no network): real CPU is confirmed from the dashboard after deploy.
import { fakeKV, fakeFetch } from './helpers.mjs';
import { refresh, handlePrices } from '../v1/prices.js';
const NOW = Date.UTC(2026, 9, 28, 14, 0, 0);
const env = { PRICES: fakeKV() };
await refresh(env, NOW - 3600e3, fakeFetch());                // warm snapshot
for (let i = 0; i < 30; i++) await refresh(env, NOW + i * 120e3, fakeFetch({ prev: 98 + (i % 3) })); // JIT warm-up
const run = async (label, fn, n = 40) => { const c = []; for (let i = 0; i < n; i++) { const t = process.cpuUsage(); await fn(i); const u = process.cpuUsage(t); c.push((u.user + u.system) / 1000); } c.sort((a, b) => a - b); console.log(label.padEnd(26), 'median', c[n >> 1].toFixed(2), 'ms  p95', c[Math.floor(n * .95)].toFixed(2), 'ms  max', c[n - 1].toFixed(2), 'ms'); return c; };
const cold = (async () => { const e = { PRICES: fakeKV() }; await refresh(e, NOW - 3600e3, fakeFetch()); const t = process.cpuUsage(); await refresh(e, NOW, fakeFetch({ prev: 90 })); const u = process.cpuUsage(t); console.log('first run after warm-up   ', ((u.user + u.system) / 1000).toFixed(2), 'ms'); })();
await cold;
await run('cron refresh (changed)', i => refresh(env, NOW + (100 + i) * 120e3, fakeFetch({ prev: 80 + i })));
await run('cron refresh (unchanged)', i => refresh(env, NOW + 99 * 120e3, fakeFetch({ prev: 80 + 39 })));
await run('GET /v1/prices (all)', () => handlePrices(new URL('https://x/v1/prices'), env, {}, NOW));
await run('GET /v1/prices?group=indices', () => handlePrices(new URL('https://x/v1/prices?group=indices'), env, {}, NOW));
console.log('snapshot size', (env.PRICES.m.get('px').length / 1024).toFixed(0), 'KB');
