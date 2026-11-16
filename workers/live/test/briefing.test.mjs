import assert from 'node:assert/strict';
import test from 'node:test';
import { cleanName, handleGreeting } from '../v1/briefing.js';

test('first names are cleaned and validated', () => {
  assert.equal(cleanName('adonay kabeya'), 'Adonay');
  assert.equal(cleanName('Zoë'), 'Zoë');
  assert.equal(cleanName("O'Brien"), "O'Brien");
  assert.equal(cleanName('<script>'), '');
  assert.equal(cleanName('a'.repeat(30)), '');
  assert.equal(cleanName(''), '');
});

test('no key: endpoint is off', async () => {
  const r = await handleGreeting(new Request('https://x/v1/briefing/greeting?name=Ann'), { PRICES: { get: async () => null } }, {});
  assert.equal(r.status, 404);
});

test('cached clip is served without calling Azure', async () => {
  const env = { AZURE_SPEECH_KEY: 'k', PRICES: { get: async k => (assert.equal(k, 'bg:v1:evening:ann'), new Uint8Array([1, 2, 3]).buffer) } };
  const r = await handleGreeting(new Request('https://x/v1/briefing/greeting?name=ann&tod=evening'), env, {});
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('Content-Type'), 'audio/mpeg');
});

test('bad name is refused', async () => {
  const r = await handleGreeting(new Request('https://x/v1/briefing/greeting?name=%3Cb%3E'), { AZURE_SPEECH_KEY: 'k', PRICES: { get: async () => null } }, {});
  assert.equal(r.status, 400);
});
