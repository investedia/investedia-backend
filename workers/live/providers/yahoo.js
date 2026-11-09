// Provider adapter: Yahoo Finance free "spark" feed. NOT licensed for commercial use (see DATA-LICENSING.md): replace this one file
// with a licensed provider before Investedia earns revenue. Every provider returns the same shape: { [yahooSymbol]: { p, prev, t } }.
export const PROVIDER = { id: 'yahoo-spark', name: 'Yahoo Finance (free)', licensed: false, delayed: true };
const UA = 'Mozilla/5.0 (compatible; Investedia/1.0; +https://investedia.com)';
export const MAX_SYMBOLS = 20; // spark rejects more than 20 symbols per call

// Pure: raw spark JSON -> normalised quotes. Bad rows are skipped, never thrown.
export function parseSpark(json) {
  const out = {};
  if (!json || typeof json !== 'object') return out;
  for (const [k, v] of Object.entries(json)) {
    if (!v || typeof v !== 'object') continue;
    const closes = Array.isArray(v.close) ? v.close.filter(x => typeof x === 'number' && x > 0) : [];
    const p = closes[closes.length - 1], prev = v.chartPreviousClose ?? v.previousClose;
    const ts = Array.isArray(v.timestamp) ? v.timestamp[v.timestamp.length - 1] : 0;
    if (!(p > 0) || !(prev > 0) || !Number.isFinite(p) || !Number.isFinite(prev)) continue;
    out[v.symbol || k] = { p, prev, t: (ts || 0) * 1000 };
  }
  return out;
}

export async function fetchQuotes(symbols, fetchFn = fetch) {
  const r = await fetchFn(`https://query1.finance.yahoo.com/v8/finance/spark?range=1d&interval=1d&symbols=${encodeURIComponent(symbols.join(','))}`, { headers: { 'User-Agent': UA } });
  if (!r.ok) throw new Error('yahoo ' + r.status);
  return parseSpark(await r.json());
}
