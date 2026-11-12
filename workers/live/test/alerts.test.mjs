import test from 'node:test';
import assert from 'node:assert/strict';
import { encrypt, _test } from '../v1/webpush.js';
import { plan, match, alertsReady } from '../v1/alerts.js';
const { b64u, unb64u, hkdf } = _test, te = new TextEncoder();
test('push payload decrypts like a browser would (RFC 8291 aes128gcm)', async () => {
  const ua = await crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
  const uaPub = new Uint8Array(await crypto.subtle.exportKey('raw', ua.publicKey)), auth = crypto.getRandomValues(new Uint8Array(16));
  const body = await encrypt({ p256dh: b64u(uaPub), auth: b64u(auth) }, 'hello alert');
  const salt = body.slice(0, 16), idlen = body[20], asPub = body.slice(21, 21 + idlen), ct = body.slice(21 + idlen);
  const asKey = await crypto.subtle.importKey('raw', asPub, { name: 'ECDH', namedCurve: 'P-256' }, false, []);
  const shared = new Uint8Array(await crypto.subtle.deriveBits({ name: 'ECDH', public: asKey }, ua.privateKey, 256));
  const cat = (...a) => { const o = new Uint8Array(a.reduce((n, x) => n + x.length, 0)); let i = 0; for (const x of a) { o.set(x, i); i += x.length; } return o; };
  const ikm = await hkdf(auth, shared, cat(te.encode('WebPush: info\0'), uaPub, asPub), 32);
  const cek = await hkdf(salt, ikm, te.encode('Content-Encoding: aes128gcm\0'), 16), nonce = await hkdf(salt, ikm, te.encode('Content-Encoding: nonce\0'), 12);
  const pt = new Uint8Array(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce }, await crypto.subtle.importKey('raw', cek, 'AES-GCM', false, ['decrypt']), ct));
  assert.equal(new TextDecoder().decode(pt.slice(0, -1)), 'hello alert'); assert.equal(pt.at(-1), 2);
});
test('VAPID header signs with the private key and names the push service origin', async () => {
  const k = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
  const pub = b64u(await crypto.subtle.exportKey('raw', k.publicKey)), priv = (await crypto.subtle.exportKey('jwk', k.privateKey)).d;
  const h = await _test.vapidHeader('https://fcm.googleapis.com/fcm/send/abc', pub, priv, 'https://investedia.com', Date.parse('2026-11-12T00:00:00Z'));
  const [t, kk] = h.slice(6).split(', k='); const [a, b, s] = t.replace(/^t=/, '').split('.');
  assert.equal(kk, pub); assert.equal(JSON.parse(atob(b.replace(/-/g, '+').replace(/_/g, '/'))).aud, 'https://fcm.googleapis.com');
  assert.ok(await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, k.publicKey, unb64u(s), te.encode(a + '.' + b)));
});
import { followHits, smartArticleHit, priceHit, channelsFor } from '../v1/alerts.js';
import { alertEmail, sendEmail } from '../v1/brevo.js';
const story = (id, t, extra = {}) => ({ id, headline: 'H ' + id, summary: 'S ' + id, published_at: t, category: 'economy', location: { country: 'Brazil' }, impacts: [], entities: [], ...extra });
const member = (id, extra = {}) => ({ user_id: id, email: id + '@x.test', unsubscribe_token: '00000000-0000-0000-0000-000000000000', alerts_on: true, muted: [], items: { c: [{ k: 'Brazil' }] }, plan: 'free', push: [], ...extra });
test('matching: followed country or asset, muted items skipped', () => {
  assert.equal(match({ c: [{ k: 'Brazil' }] }, story('a', '2026-11-12T09:00:00Z')), 'Brazil');
  assert.equal(match({ a: [{ s: 'NVDA', n: 'Nvidia' }] }, story('b', '2026-11-12T09:00:00Z', { location: { country: 'United States' }, impacts: [{ ticker: 'NVDA', name: 'NVIDIA' }] })), 'Nvidia');
  assert.equal(match({ c: [{ k: 'United States' }] }, story('c', '2026-11-12T09:00:00Z', { location: { country: 'United States of America' } })), 'United States');
  assert.deepEqual(followHits({ c: [{ k: 'Brazil' }] }, ['c:Brazil'], story('d', '2026-11-12T09:00:00Z')), []);
});
test('article alerts: free gets email only, one entry per article, never twice', () => {
  const s1 = story('s1', '2026-11-12T09:00:00Z'), s2 = story('s2', '2026-11-12T09:30:00Z');
  const g = plan([s1, s2], [member('u1'), member('u2', { plan: 'pro', push: [{ endpoint: 'e' }] })], [], new Set(['u1|follow|s2|email']));
  const u1 = g.find(x => x.member.user_id === 'u1'), u2 = g.find(x => x.member.user_id === 'u2');
  assert.deepEqual(u1.email.map(e => e.item), ['s1']); assert.equal(u1.push.length, 0);
  assert.deepEqual(u2.email.map(e => e.item), ['s2', 's1']); assert.deepEqual(u2.push.map(e => e.item), ['s2', 's1']);
});
test('smart alerts: market-moving, sector, price; free forced to email', () => {
  const mm = story('m', '2026-11-12T09:00:00Z', { market_moving: true, category: 'commodities' });
  assert.equal(smartArticleHit({ type: 'market_moving', params: {} }, mm), 'Market-moving');
  assert.equal(smartArticleHit({ type: 'market_moving', params: { scope: 'follows' } }, mm, { c: [{ k: 'Chile' }] }), null);
  assert.equal(smartArticleHit({ type: 'sector', params: { category: 'commodities' } }, mm), 'Sector · Commodities');
  assert.equal(smartArticleHit({ type: 'sector', params: { category: 'crypto' } }, mm), null);
  const pa = { type: 'price', params: { symbol: 'NVDA', name: 'Nvidia', dir: 'either', pct: 5 } }, t = Date.parse('2026-11-12T15:00:00Z');
  assert.equal(priceHit(pa, [180, -6.2, t, t]).item, 'NVDA:2026-11-12'); assert.equal(priceHit(pa, [180, 3.1, t, t]), null);
  assert.equal(priceHit({ ...pa, params: { ...pa.params, dir: 'up' } }, [180, -6.2, t, t]), null);
  assert.deepEqual(channelsFor({ channels: ['push', 'email'] }, member('f')), ['email']);
  assert.deepEqual(channelsFor({ channels: ['push'] }, member('p', { plan: 'pro', push: [{}] })), ['push']);
  const g = plan([mm], [member('u3', { items: {} })], [{ id: 'sa1', user_id: 'u3', type: 'market_moving', params: {}, channels: ['push'] }], new Set());
  assert.deepEqual(g[0].email.map(e => [e.key, e.item]), [['sa1', 'm']]); assert.equal(g[0].push.length, 0);
});
test('email: Brevo request shape, unsubscribe link and headers, no real send', async () => {
  const mail = alertEmail([{ why: 'You follow Brazil', title: 'Brazil <holds> rates', line: 'x', url: 'https://investedia.com/story.html?id=1' }], 'https://api.investedia.com/v1/alerts/unsubscribe?u=a&t=b');
  assert.match(mail.html, /Brazil &lt;holds&gt; rates/); assert.match(mail.html, /Unsubscribe/); assert.match(mail.text, /Not investment advice/);
  let seen; const st = await sendEmail({ BREVO_API_KEY: 'k', BREVO_SENDER_EMAIL: 'alerts@investedia.com' }, 'm@x.test', mail, 'https://u', async (u, o) => { seen = { u, o }; return { status: 201 }; });
  const b = JSON.parse(seen.o.body); assert.equal(st, 201); assert.equal(seen.u, 'https://api.brevo.com/v3/smtp/email'); assert.equal(seen.o.headers['api-key'], 'k');
  assert.deepEqual(b.to, [{ email: 'm@x.test' }]); assert.equal(b.headers['List-Unsubscribe'], '<https://u>');
});
test('alerts stay off without the switch and keys', () => {
  assert.ok(!alertsReady({})); assert.ok(!alertsReady({ ALERTS_ENABLED: 'true', SUPABASE_URL: 'x', SUPABASE_SERVICE_KEY: 'x' }));
  assert.ok(alertsReady({ ALERTS_ENABLED: 'true', SUPABASE_URL: 'x', SUPABASE_SERVICE_KEY: 'x', BREVO_API_KEY: 'k', BREVO_SENDER_EMAIL: 'a@b.c' }));
});
