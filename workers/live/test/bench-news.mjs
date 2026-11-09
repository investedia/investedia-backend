// CPU benchmark of one priority-news cron run. Usage: node test/bench-news.mjs [dir-with-real-feed-xml]
// With a directory of saved real feeds (never committed: publisher content) it uses them, otherwise it generates feed-sized synthetic XML.
// Network waiting (feeds, Gemini) is excluded: the fake fetch answers instantly. Node CPU is an estimate of Cloudflare CPU; confirm in the dashboard.
import { readdirSync, readFileSync } from 'node:fs';
import { fakeKV, rssXml } from './helpers.mjs';
import { refreshNews } from '../v1/news.js';
import { FEEDS } from '../v1/feeds.js';
const NOW = Date.now(), dir = process.argv[2];
let xmls;
if (dir) { const f = readdirSync(dir).filter(x => x.endsWith('.xml')); xmls = FEEDS.map((_, i) => readFileSync(`${dir}/${f[i % f.length]}`, 'utf8')); console.log('real feeds:', f.length, 'avg', (xmls.reduce((a, x) => a + x.length, 0) / xmls.length / 1024).toFixed(0), 'KB'); }
else xmls = FEEDS.map((f, k) => rssXml(Array.from({ length: 40 }, (_, i) => ({ title: `${f.name} story ${k}-${i}: markets react to inflation, rates and oil in region ${i * 7}`, url: `https://example.org/${k}/${i}`, t: NOW - i * 600e3, desc: 'Short feed description. '.repeat(12) + '<img src="x"/>'.repeat(5) }))));
let idx = 0;
const feedFetch = async () => { const x = xmls[idx++ % xmls.length]; return { ok: true, status: 200, text: async () => x }; };
const gen = async (prompt) => { const m = JSON.parse(prompt.slice(prompt.indexOf('[{"i":0'))); return { model: 'm', json: m.slice(0, 10).map((c, i) => ({ members: [i], headline: 'Headline ' + i, summary: 'Summary '.repeat(10), why: 'Why '.repeat(20), category: 'economy', importance: 2, market_moving: true, place: 'Frankfurt', country: 'DE', lat: 50.1, lon: 8.6, entities: [{ name: 'ECB', ticker: 'EURUSD=X' }], impacts: [{ kind: 'asset', name: 'Euro', country: 'DE', ticker: 'EURUSD=X', direction: 'up', why: 'Support' }], why_moved: 'Moved' })) }; };
const env = { PRICES: fakeKV() };
// warm state, as in steady state: 40 stories, ~2500 seen hashes
const stories = Array.from({ length: 40 }, (_, i) => ({ id: 'w' + i, headline: 'Old headline ' + i + ' unrelated words', published_at: new Date(NOW - i * 3600e3).toISOString(), sources: [{ name: 's', url: 'https://old.example/' + i }], source: { name: 's' }, location: { place: 'p', country: 'DE', lat: 1, lon: 1, region: 'eu' }, summary: 'x'.repeat(300), why: 'y'.repeat(300), impacts: [], entities: [] }));
const warmIx = { t: NOW, seen: Array.from({ length: 2500 }, (_, i) => `h${i.toString(36)}.abcd1.${Math.floor(NOW / 6e4)}`).join(' '), known: stories.map(s => [s.headline, Date.parse(s.published_at)]), urls: '', stats: null };
const cpu = async (fn) => { const t = process.cpuUsage(); const r = await fn(); const u = process.cpuUsage(t); return [(u.user + u.system) / 1000, r]; };
const stat = (a) => { a = [...a].sort((x, y) => x - y); return `median ${a[a.length >> 1].toFixed(2)}  p95 ${a[Math.floor(a.length * .95)].toFixed(2)}  max ${a.at(-1).toFixed(2)}`; };
const busy = [], quiet = [];
for (let i = 0; i < 30; i++) {
  env.PRICES.m.set('news', JSON.stringify({ t: NOW, stories })); env.PRICES.m.set('newsx', JSON.stringify(warmIx));
  idx = 0; const [c1, r1] = await cpu(() => refreshNews(env, NOW, { fetch: feedFetch, generate: gen }));        // new articles: parse, dedupe, Gemini JSON, 2 KV writes
  idx = 0; const [c2, r2] = await cpu(() => refreshNews(env, NOW + 60e3, { fetch: feedFetch, generate: gen })); // same feeds again: nothing new
  if (i >= 8) { busy.push(c1); quiet.push(c2); }
  if (i === 8) console.log('busy run:', JSON.stringify({ fetched: r1.fetched, candidates: r1.candidates, added: r1.added, wrote: r1.wrote }), ' quiet run:', JSON.stringify({ candidates: r2.candidates, wrote: r2.wrote }));
}
console.log('CPU ms, run with new articles :', stat(busy));
console.log('CPU ms, run with nothing new  :', stat(quiet), ' (free-plan limit 10 ms)');
console.log('KV: stories blob', (env.PRICES.m.get('news').length / 1024).toFixed(0), 'KB, index', (env.PRICES.m.get('newsx').length / 1024).toFixed(0), 'KB');
