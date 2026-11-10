import test from 'node:test'; import assert from 'node:assert/strict';
import { fakeKV } from './helpers.mjs'; import { joinWaitlist } from '../v1/waitlist.js';
const rq = (b, ip = '1.1.1.1') => new Request('https://api.investedia.com/v1/waitlist', { method: 'POST', body: JSON.stringify(b), headers: { 'CF-Connecting-IP': ip } });
test('waitlist is off unless enabled', async () => { assert.equal((await joinWaitlist(rq({ email: 'a@b.co', consent: true }), { PRICES: fakeKV() })).status, 404); });
test('waitlist stores once, requires consent and valid email, rate limits', async () => {
  const env = { PRICES: fakeKV(), WAITLIST_ENABLED: 'on' };
  assert.equal((await joinWaitlist(rq({ email: 'bad', consent: true }), env)).status, 422);
  assert.equal((await joinWaitlist(rq({ email: 'a@b.co' }), env)).status, 422);
  assert.equal((await joinWaitlist(rq({ email: 'A@B.co ', consent: true }), env)).status, 200);
  assert.equal((await joinWaitlist(rq({ email: 'a@b.co', consent: true }), env)).status, 200);
  const keys = [...env.PRICES.m.keys()].filter(k => k.startsWith('waitlist:')); assert.equal(keys.length, 1);
  assert.equal(JSON.parse(env.PRICES.m.get(keys[0])).email, 'a@b.co');
  for (let i = 0; i < 5; i++) await joinWaitlist(rq({ email: `x${i}@b.co`, consent: true }, '2.2.2.2'), env);
  assert.equal((await joinWaitlist(rq({ email: 'y@b.co', consent: true }, '2.2.2.2'), env)).status, 429);
  assert.equal((await joinWaitlist(rq({ email: 'z@b.co', consent: true, website: 'spam' }, '3.3.3.3'), env)).status, 200);
  assert.ok(![...env.PRICES.m.values()].some(v => String(v).includes('z@b.co')));
});
