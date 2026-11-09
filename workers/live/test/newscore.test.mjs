import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { canon, sameEvent, score, dedupe } from '../v1/newscore.js';
const V = JSON.parse(readFileSync(new URL('../../../tests/fixtures/news-core-vectors.json', import.meta.url)));
const NOW = Date.parse(V.now);
test('canonical URLs match the Python implementation', () => { for (const [u, want] of V.canon) assert.equal(canon(u), want, u); });
test('title similarity matches the Python implementation', () => { for (const [a, b, h, want] of V.same) assert.equal(sameEvent(a, b, h), want, a); });
test('scores match the Python implementation', () => { for (const [c, want] of V.score) assert.equal(score({ title: c.title, kind: c.kind, desc: c.desc || '', published: new Date(NOW - c.mins * 60000).toISOString() }, NOW), want, c.title); });
test('dedupe keeps the official copy and drops known titles', () => {
  const mk = (title, url, kind, mins) => ({ title, url, kind, published: new Date(NOW - mins * 60000).toISOString() });
  const { kept, dropped } = dedupe([mk('ECB holds interest rates steady at 2%', 'https://a.com/1', 'news', 30), mk('ECB holds interest rates steady at 2%', 'https://ecb.eu/p', 'official', 5), mk('Copper mine strike hits Chile output', 'https://c.com/2', 'news', 9)], [], NOW);
  assert.equal(kept.length, 2); assert.equal(dropped, 1); assert.ok(kept.some(k => k.kind === 'official'));
  assert.equal(dedupe([mk('Copper mine strike hits Chile output', 'https://z.com/3', 'news', 5)], [['Copper mine strike hits Chile output', NOW - 3600e3]], NOW).kept.length, 0);
});
