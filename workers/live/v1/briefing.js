// Briefing greeting (owner 16 Nov 2026): a short clip "Good morning, <first name>." spoken by the Briefing voice.
// Made once per name and time of day with Azure Speech, then kept in KV and the edge cache, so each name costs about once.
// The Azure key stays in the Worker secret AZURE_SPEECH_KEY; the browser never sees it.
// GET /v1/briefing/greeting?name=Adonay&tod=morning|afternoon|evening -> audio/mpeg
const VOICE = 'en-US-NovaTurboMultilingualNeural';
const HI = { morning: 'Good morning', afternoon: 'Good afternoon', evening: 'Good evening' };

// First names only: letters (any alphabet), hyphen, apostrophe; 1 to 24 characters.
export const cleanName = raw => {
  const n = String(raw || '').normalize('NFC').trim().split(/\s+/)[0] || '';
  return /^[\p{L}][\p{L}'’-]{0,23}$/u.test(n) ? n[0].toUpperCase() + n.slice(1) : '';
};

const xml = s => s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c]));

export async function handleGreeting(req, env, h) {
  const url = new URL(req.url), name = cleanName(url.searchParams.get('name')), tod = HI[url.searchParams.get('tod')] ? url.searchParams.get('tod') : 'morning';
  if (!env.AZURE_SPEECH_KEY) return new Response('briefing voice not configured', { status: 404, headers: h });
  if (!name) return new Response('invalid name', { status: 400, headers: h });
  const key = `bg:v1:${tod}:${name.toLowerCase()}`, headers = { ...h, 'Content-Type': 'audio/mpeg', 'Cache-Control': 'public, max-age=2592000' };
  const cached = await env.PRICES.get(key, 'arrayBuffer');
  if (cached) return new Response(cached, { headers });
  const region = env.AZURE_SPEECH_REGION || 'germanywestcentral';
  const ssml = `<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'><voice name='${VOICE}'>${HI[tod]}, ${xml(name)}.<break time='400ms'/></voice></speak>`;
  const r = await fetch(`https://${region}.tts.speech.microsoft.com/cognitiveservices/v1`, {
    method: 'POST', body: ssml,
    headers: { 'Ocp-Apim-Subscription-Key': env.AZURE_SPEECH_KEY, 'Content-Type': 'application/ssml+xml', 'X-Microsoft-OutputFormat': 'audio-24khz-96kbitrate-mono-mp3', 'User-Agent': 'investedia-briefing' }
  });
  if (!r.ok) return new Response('voice unavailable', { status: 502, headers: h });
  const buf = await r.arrayBuffer();
  if (buf.byteLength > 0 && buf.byteLength < 200000) await env.PRICES.put(key, buf);
  return new Response(buf, { headers });
}
