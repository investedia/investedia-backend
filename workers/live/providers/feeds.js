// Provider adapter: RSS/Atom feeds. Reads only the newest items of each feed with cheap string scanning (the free plan allows 10 ms of CPU per run),
// and keeps only headline, link, time and the feed's own short description: never article text.
const decode = (s) => s.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#0?39;|&apos;/g, "'").replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n)).trim();
const tag = (block, name) => { const m = block.match(new RegExp(`<${name}(?:\\s[^>]*)?>([\\s\\S]*?)</${name}>`, 'i')); return m ? decode(m[1]) : ''; };
export function parseTime(text, nowMs) {
  const ms = Date.parse((text || '').trim()); if (!Number.isFinite(ms)) return null; return Math.min(ms, nowMs); // never in the future
}
export function parseFeed(xml, { max = 12, nowMs = Date.now(), maxAgeMs = 3 * 86400e3 } = {}) {
  const out = []; if (typeof xml !== 'string') return out;
  const re = /<(item|entry)[\s>][\s\S]*?<\/\1>/gi; let m;
  while ((m = re.exec(xml)) && out.length < max) {
    const b = m[0], title = tag(b, 'title');
    let link = tag(b, 'link'); if (!link) { const l = b.match(/<link[^>]*href=["']([^"']+)["']/i); link = l ? decode(l[1]) : ''; }
    if (!title || !/^https?:\/\//i.test(link)) continue;
    const ts = parseTime(tag(b, 'pubDate') || tag(b, 'dc:date') || tag(b, 'updated') || tag(b, 'published'), nowMs) ?? nowMs;
    if (nowMs - ts > maxAgeMs) continue;
    out.push({ title, url: link, published: new Date(ts).toISOString().replace(/\.\d+Z$/, 'Z'), desc: tag(b, 'description').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 400) });
  }
  return out;
}
export async function fetchFeed(f, nowMs, fetchFn = fetch) {
  const r = await fetchFn(f.url, { headers: { 'User-Agent': 'InvestediaNews/1.0 (+https://investedia.com; info@investedia.com)' }, signal: AbortSignal.timeout(8000) });
  if (!r.ok) throw new Error(f.name + ' ' + r.status);
  return parseFeed((await r.text()).slice(0, 400_000), { nowMs }).map(x => ({ ...x, source: f.name, kind: f.kind, hint: f.hint }));
}
