// Provider adapter: Gemini. The key is a Worker secret (GEMINI_API_KEY) and never leaves the Worker. Only used for enrichment of articles that passed the cheap filters.
const BASE = 'https://generativelanguage.googleapis.com/v1beta/models/';
export async function generate(prompt, env, fetchFn = fetch) {
  if (!env.GEMINI_API_KEY) throw new Error('GEMINI_API_KEY is not set');
  const body = JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { temperature: 0.2, responseMimeType: 'application/json' } });
  const models = [env.GEMINI_MODEL, 'gemini-flash-latest', 'gemini-flash-lite-latest'].filter(Boolean);
  const tried = [];
  for (const m of models) {
    try {
      const r = await fetchFn(`${BASE}${m}:generateContent`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY }, body, signal: AbortSignal.timeout(90000) });
      if (!r.ok) { tried.push(`${m}: HTTP ${r.status}`); if ([400, 401, 403].includes(r.status)) throw new Error(tried.at(-1)); continue; }
      const j = await r.json(); const txt = j?.candidates?.[0]?.content?.parts?.[0]?.text; if (!txt) { tried.push(m + ': empty'); continue; }
      return { model: m, json: JSON.parse(txt.trim().replace(/^```(json)?|```$/g, '')) };
    } catch (e) { tried.push(`${m}: ${String(e.message || e).slice(0, 80)}`); if (/HTTP 40[013]/.test(tried.at(-1))) break; }
  }
  throw new Error(tried.join(' | ').slice(0, 300));
}
