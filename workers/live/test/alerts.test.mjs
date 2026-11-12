import test from 'node:test';
import assert from 'node:assert/strict';
import { encrypt, _test } from '../v1/webpush.js';
import { plan, match, isoWeek, FREE_PER_WEEK, alertsReady } from '../v1/alerts.js';
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
const story = (id, t, extra = {}) => ({ id, headline: 'H ' + id, published_at: t, location: { country: 'Brazil' }, impacts: [], entities: [], ...extra });
const NOW = Date.parse('2026-11-12T10:00:00Z'), W = isoWeek(NOW);
test('matching: followed country or asset; ISO week', () => {
  assert.equal(W, '2026-W46');
  assert.equal(match({ c: [{ k: 'Brazil' }] }, story('a', '2026-11-12T09:00:00Z')), 'Brazil');
  assert.equal(match({ a: [{ s: 'NVDA', n: 'Nvidia' }] }, story('b', '2026-11-12T09:00:00Z', { location: { country: 'United States' }, impacts: [{ ticker: 'NVDA', name: 'NVIDIA' }] })), 'Nvidia');
  assert.equal(match({ c: [{ k: 'United States' }] }, story('c', '2026-11-12T09:00:00Z', { location: { country: 'United States of America' } })), 'United States');
  assert.equal(match({ c: [{ k: 'Chile' }] }, story('d', '2026-11-12T09:00:00Z')), null);
});
test('free cap: 3 per week, one per run, never the same article twice', () => {
  const watch = [{ user_id: 'u1', items: { c: [{ k: 'Brazil' }] } }, { user_id: 'u2', items: { c: [{ k: 'Brazil' }] } }, { user_id: 'u3', items: { c: [{ k: 'Chile' }] } }];
  const logs = [{ user_id: 'u2', week: W, sent: FREE_PER_WEEK, article_ids: [] }, { user_id: 'u1', week: W, sent: 1, article_ids: ['new'] }];
  const p = plan([story('old', '2026-11-12T08:00:00Z'), story('new', '2026-11-12T09:30:00Z')], watch, logs, NOW);
  assert.deepEqual(p.map(x => [x.user_id, x.story.id, x.sent]), [['u1', 'old', 2]]);
  const lastWeek = plan([story('x', '2026-11-12T09:00:00Z')], [watch[1]], [{ user_id: 'u2', week: '2026-W45', sent: 3, article_ids: [] }], NOW);
  assert.equal(lastWeek.length, 1, 'counter resets with a new week');
});
test('alerts stay off without the switch and keys', () => {
  assert.ok(!alertsReady({})); assert.ok(!alertsReady({ ALERTS_ENABLED: 'false', SUPABASE_URL: 'x', SUPABASE_SERVICE_KEY: 'x', VAPID_PUBLIC_KEY: 'x', VAPID_PRIVATE_KEY: 'x' }));
});
