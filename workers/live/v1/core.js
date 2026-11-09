// Pure logic for the /v1 API: envelopes, merging, change detection, KV write budget. No Cloudflare globals, so it runs under node --test.
export const GROUPS = { i: 'indices', s: 'stocks', f: 'currencies', c: 'commodities' };
export const KEEP_MS = 7 * 86400e3;       // a symbol that keeps failing stays available (marked stale) for 7 days
export const FRESH_MS = 6 * 60e3;         // snapshot younger than this is "delayed" (the provider itself is 15 min delayed), older is "stale"
export const HEARTBEAT_MS = 10 * 60e3;    // an unchanged snapshot is still rewritten this often, so checked_at stays honest
export const WRITE_BUDGET = 900;          // free plan allows 1000 KV writes a day: past this, writes are slowed to one per 15 minutes
export const day = (now) => new Date(now).toISOString().slice(0, 10);

export const entry = (line) => { const [site, y, inv, g, k] = line.split('|'); return { site, y, inv: inv === '1', g: g || 's', k: +k || 1 }; };

// quote {p, prev, t} -> stored row [price, day%, providerTime, fetchedAt]
export function toRow(q, inv, now, k = 1) {  // k = unit scale (0.01 for quotes in pence or cents)
  const d = (q.p / q.prev - 1) * 100 * (inv ? -1 : 1);
  if (!Number.isFinite(d) || Math.abs(d) > 60) return null;      // implausible move: treat as bad data
  return [+(q.p * k).toFixed(6), +d.toFixed(2), q.t || 0, now];
}

// Merge fresh rows over the previous snapshot; drops rows older than KEEP_MS. Never returns less than it was given.
export function merge(prev, fresh, now) {
  const out = {};
  for (const [k, r] of Object.entries(prev || {})) if (now - r[3] < KEEP_MS) out[k] = r;
  for (const [k, r] of Object.entries(fresh)) out[k] = r;
  return out;
}

// Same prices and changes (fetch times ignored)?
export function unchanged(a, b) {
  const ka = Object.keys(a || {}), kb = Object.keys(b || {});
  if (ka.length !== kb.length) return false;
  for (const k of ka) { const x = a[k], y = b[k]; if (!y || x[0] !== y[0] || x[1] !== y[1]) return false; }
  return true;
}

// Decide whether to write: changed data, or heartbeat due; slowed down when the daily write budget is nearly spent.
export function shouldWrite({ changed, lastWrite, writesToday, now }) {
  if (!lastWrite) return true;
  const since = now - lastWrite;
  if (writesToday >= WRITE_BUDGET) return since >= 15 * 60e3;
  return changed || since >= HEARTBEAT_MS;
}

export function stateOf(snapT, now) { return !snapT ? 'unavailable' : now - snapT <= FRESH_MS ? 'delayed' : 'stale'; }

export function envelope(data, { provider, snapT, now, ttl, extra }) {
  return { data, meta: { state: stateOf(snapT, now), fetched_at: snapT ? new Date(snapT).toISOString() : null, age_s: snapT ? Math.round((now - snapT) / 1000) : null,
    provider: provider.id, licensed: provider.licensed, ttl_s: ttl, upstream_ok: snapT ? now - snapT <= FRESH_MS : false, version: 1, ...extra } };
}

// rows -> { SYMBOL: [price, change%, providerTime, fetchedAt] } for one group (or all)
export function select(rows, symbolsByGroup, group) {
  if (!group || group === 'all') return rows;
  const want = new Set(symbolsByGroup[group] || []), out = {};
  for (const k of want) if (rows[k]) out[k] = rows[k];
  return out;
}

export const emptyStats = (now) => ({ day: day(now), writes: 0, cron_runs: 0, cron_failures: 0, upstream_calls: 0, upstream_failures: 0, skipped_unchanged: 0 });
export function rollStats(s, now) { return s && s.day === day(now) ? s : emptyStats(now); }
