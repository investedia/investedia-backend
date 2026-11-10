// Pro waitlist: stores an email + consent record in KV. Off unless WAITLIST_ENABLED === 'on'.
// No payments, no accounts, no emails sent from here. Records keyed by SHA-256 of the lowercase email (dedupe).
export const CONSENT_V = 'pro-waitlist-v1';
const EMAIL = /^[^\s@<>()]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}$/;
const hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
const sha = async s => hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)));
export async function joinWaitlist(req, env, now = Date.now()) {
  if (env.WAITLIST_ENABLED !== 'on') return { status: 404, body: { error: 'not found' } };
  let b; try { b = await req.json(); } catch { return { status: 400, body: { error: 'invalid body' } }; }
  const email = String(b?.email || '').trim().toLowerCase();
  if (!EMAIL.test(email) || email.length > 254) return { status: 422, body: { error: 'invalid email' } };
  if (b?.consent !== true) return { status: 422, body: { error: 'consent required' } };
  if (b?.website) return { status: 200, body: { ok: true } }; // honeypot: bots fill hidden field
  const ip = req.headers.get('CF-Connecting-IP') || 'x', day = new Date(now).toISOString().slice(0, 10);
  const rk = 'wl-rate:' + (await sha(ip + day)).slice(0, 32), n = +(await env.PRICES.get(rk) || 0);
  if (n >= 5) return { status: 429, body: { error: 'too many requests' } };
  await env.PRICES.put(rk, String(n + 1), { expirationTtl: 86400 });
  const key = 'waitlist:' + await sha(email);
  if (!(await env.PRICES.get(key))) await env.PRICES.put(key, JSON.stringify({ email, consent: CONSENT_V, source: String(b.source || '').slice(0, 40), created_at: new Date(now).toISOString() }));
  return { status: 200, body: { ok: true } }; // same answer whether new or existing (no account enumeration)
}
