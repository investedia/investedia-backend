import { TIER_A, TIER_B } from '../symbols.js';
import { fetchQuotes, MAX_SYMBOLS, PROVIDER } from '../providers/yahoo.js';
import { GROUPS, entry, toRow, merge, unchanged, shouldWrite, rollStats, envelope, select } from './core.js';

const A = TIER_A.map(entry), B = TIER_B.map(entry), ALL = [...A, ...B];
export const SYMBOLS_BY_GROUP = {};
for (const e of ALL) (SYMBOLS_BY_GROUP[GROUPS[e.g]] ||= []).push(e.site);
const chunks = (list, n) => { const o = []; for (let i = 0; i < list.length; i += n) o.push(list.slice(i, i + n)); return o; };
const B_PER_RUN = 160;  // 8 spark calls: with tier A (7 calls) one run uses about 15 of the 50 free subrequests

// One cron run: all of tier A plus one rotating slice of tier B (the slice depends on the clock, so no state is needed between runs).
export async function refresh(env, now = Date.now(), fetchFn = fetch) {
  const slot = Math.floor(now / 120e3), nB = Math.ceil(B.length / B_PER_RUN), sliceB = nB ? B.slice((slot % nB) * B_PER_RUN, (slot % nB + 1) * B_PER_RUN) : [];  // tier B is empty while the whole site list fits in tier A
  const batch = [...A, ...sliceB], byY = new Map(batch.map(e => [e.y, e]));
  let snap = {}; try { snap = JSON.parse(await env.PRICES.get('px')) || {}; } catch {}
  const stats = rollStats(snap.stats, now); stats.cron_runs++;
  const fresh = {};
  const calls = chunks(batch.map(e => e.y), MAX_SYMBOLS);
  const results = await Promise.allSettled(calls.map(c => fetchQuotes(c, fetchFn)));
  results.forEach(r => { stats.upstream_calls++; if (r.status === 'fulfilled') for (const [y, q] of Object.entries(r.value)) { const e = byY.get(y); const row = e && toRow(q, e.inv, now, e.k); if (row) fresh[e.site] = row; } else stats.upstream_failures++; });
  const got = Object.keys(fresh).length;
  if (!got) { stats.cron_failures++; return { ok: 0, wrote: false, stats, snapshot: snap, reason: 'no valid quotes: previous snapshot kept' }; } // never overwrite good data with nothing
  const known = new Set(ALL.map(e => e.site)), prevP = Object.fromEntries(Object.entries(snap.p || {}).filter(([k]) => known.has(k)));  // rows of symbols that are no longer in the list are dropped, never served
  const p = merge(prevP, fresh, now), changed = !unchanged(snap.p, p);
  if (!changed) stats.skipped_unchanged++;
  const write = shouldWrite({ changed, lastWrite: snap.t, writesToday: stats.writes, now });
  let next = snap;
  if (write) { stats.writes++; next = { t: now, p, stats, provider: PROVIDER.id }; await env.PRICES.put('px', JSON.stringify(next)); }
  return { ok: got, sent: batch.length, wrote: write, changed, stats, snapshot: next };
}

export async function handlePrices(url, env, ctx, now = Date.now()) {
  let snap = null; try { snap = JSON.parse(await env.PRICES.get('px')); } catch {}
  if (!snap || !snap.p) return { status: 503, body: { error: 'no data yet', meta: { state: 'unavailable', provider: PROVIDER.id, version: 1 } } };
  const group = url.searchParams.get('group') || 'all';
  if (group !== 'all' && !SYMBOLS_BY_GROUP[group]) return { status: 400, body: { error: 'unknown group', groups: ['all', ...Object.keys(SYMBOLS_BY_GROUP)] } };
  const data = select(snap.p, SYMBOLS_BY_GROUP, group);
  return { status: 200, body: envelope(data, { provider: PROVIDER, snapT: snap.t, now, ttl: 15, extra: { group, count: Object.keys(data).length, format: ['price', 'change_pct', 'provider_time_ms', 'fetched_at_ms'] } }) };
}

export async function handleStatus(env, now = Date.now()) {
  let snap = null; try { snap = JSON.parse(await env.PRICES.get('px')); } catch {}
  const stats = snap ? rollStats(snap.stats, now) : null;
  return { status: 200, body: { now: new Date(now).toISOString(), prices: snap ? { fetched_at: new Date(snap.t).toISOString(), age_s: Math.round((now - snap.t) / 1000), symbols: Object.keys(snap.p).length, provider: snap.provider } : null,
    kv: stats && { day: stats.day, writes_today: stats.writes, write_budget: 900, free_limit: 1000, note: 'writes are exact (counted at write time); reads are served from a 15 s edge cache, so at most one KV read per 15 s per Cloudflare location' },
    cron: stats && { runs_today: stats.cron_runs, failures_today: stats.cron_failures, upstream_calls: stats.upstream_calls, upstream_failures: stats.upstream_failures, skipped_unchanged: stats.skipped_unchanged },
    limits: { cpu_ms_per_invocation_free: 10, subrequests_per_invocation_free: 50 }, version: 1 } };
}
