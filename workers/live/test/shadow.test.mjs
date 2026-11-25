// Shadow mode: the price cron must write to 'px-shadow' and never change the live 'px' key the site reads.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fakeKV, fakeFetch } from './helpers.mjs';
import { refresh } from '../v1/prices.js';

const NOW = Date.UTC(2026, 9, 28, 14, 0, 0);

test('shadow mode writes px-shadow and leaves live px untouched', async () => {
  const live = JSON.stringify({ t: 1, p: {} });
  const env = { PRICES: fakeKV({ px: live }), PRICE_SHADOW: 'true' };
  const r = await refresh(env, NOW, fakeFetch({ prev: 98 }));
  assert.ok(r.ok > 0);
  assert.equal(env.PRICES.m.get('px'), live);
  assert.ok(env.PRICES.m.has('px-shadow'));
});

test('without the switch the live key is written as before', async () => {
  const env = { PRICES: fakeKV() };
  await refresh(env, NOW, fakeFetch({ prev: 98 }));
  assert.ok(env.PRICES.m.has('px'));
  assert.ok(!env.PRICES.m.has('px-shadow'));
});
