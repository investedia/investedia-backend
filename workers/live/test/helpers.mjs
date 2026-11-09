export const fakeKV = (init = {}) => { const m = new Map(Object.entries(init)); return { m, puts: 0, async get(k) { return m.has(k) ? m.get(k) : null; }, async put(k, v) { this.puts++; m.set(k, v); } }; };
// Fake Yahoo spark response for the requested symbols; price = base + i
export const fakeFetch = (opts = {}) => async (url) => {
  const syms = decodeURIComponent(new URL(url).searchParams.get('symbols')).split(',');
  if (opts.status) return { ok: false, status: opts.status, json: async () => ({}) };
  const out = {}; syms.forEach((s, i) => { out[s] = { timestamp: [1793212394], symbol: s, close: [opts.close?.[s] ?? 100 + i], chartPreviousClose: opts.prev ?? 99 + i }; });
  if (opts.junk) out[syms[0]] = null;
  return { ok: true, status: 200, json: async () => out };
};
export const rssXml = (items) => `<?xml version="1.0"?><rss><channel><title>t</title>${items.map(i => `<item><title><![CDATA[${i.title}]]></title><link>${i.url}</link><pubDate>${new Date(i.t).toUTCString()}</pubDate><description><![CDATA[<p>${i.desc || ''}</p>]]></description></item>`).join('')}</channel></rss>`;
