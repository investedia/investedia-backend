// Exact priority-source hosts. Redirects must pass the same policy on every hop.
export const SOURCE_HOSTS = new Set([
  "ec.europa.eu", "feeds.bbci.co.uk", "feeds.content.dowjones.io", "oilprice.com", "rss.nytimes.com",
  "www.bankofcanada.ca", "www.bankofengland.co.uk", "www.banrep.gov.co", "www.bea.gov", "www.boj.or.jp",
  "www.bok.or.kr", "www.centralbank.go.ke", "www.coindesk.com", "www.ecb.europa.eu", "www.eia.gov",
  "www.federalreserve.gov", "www.nationalbanken.dk", "www.prnewswire.com", "www.rba.gov.au", "www.rbi.org.in",
  "www.rbnz.govt.nz", "www.riksbank.se", "www.sec.gov", "www.theguardian.com",
]);
export function destination(url, method) {
  const u = new URL(url);
  if (u.protocol !== "https:" || u.username || u.password || (u.port && u.port !== "443")) return null;
  if (SOURCE_HOSTS.has(u.hostname) && method === "GET") return "source";
  if (u.hostname !== "generativelanguage.googleapis.com") return null;
  if (method === "GET" && u.pathname === "/v1beta/models" && u.search === "?pageSize=200") return "gemini";
  if (method === "POST" && /^\/v1beta\/models\/[a-zA-Z0-9.-]+:generateContent$/.test(u.pathname) && !u.search) return "gemini";
  return null;
}
export async function egress(request, key, enabled, upstream = fetch) {
  if (!enabled || !key) return new Response("Trial egress disabled", { status: 403 });
  let url = request.url;
  for (let hop = 0; hop < 5; hop++) {
    const type = destination(url, request.method);
    if (!type) return new Response("Trial destination denied", { status: 403 });
    // Do not forward caller headers, cookies or credentials to publisher sites.
    const headers = new Headers({ "User-Agent": "InvestediaNewsTrial/1.0" });
    if (type === "gemini") { headers.set("x-goog-api-key", key); headers.set("Content-Type", "application/json"); }
    const response = await upstream(url, { method: request.method, headers,
      body: request.method === "POST" ? await request.clone().arrayBuffer() : undefined, redirect: "manual" });
    if (response.status >= 300 && response.status < 400) {
      const next = response.headers.get("location");
      if (!next || request.method !== "GET") return new Response("Trial redirect denied", { status: 502 });
      url = new URL(next, url).href;
      continue;
    }
    if (!response.ok) return new Response("Trial upstream failed", { status: response.status });
    return new Response(response.body, { status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/octet-stream" } });
  }
  return new Response("Trial redirect limit", { status: 502 });
}
export async function route(request, env) {
  if (!env.TRIAL_TOKEN || request.headers.get("Authorization") !== `Bearer ${env.TRIAL_TOKEN}`)
    return new Response("Unauthorized", { status: 401 });
  const path = new URL(request.url).pathname;
  if (path === "/health" && request.method === "GET") return Response.json({ trial: true, enabled: env.TRIAL_ENABLED === "true", scheduled: false });
  if (path === "/result" && request.method === "GET") {
    const compressed = await env.TRIAL_STORE.get("trial/latest.json.gz");
    const saved = compressed || await env.TRIAL_STORE.get("trial/latest.json");
    return saved ? new Response(saved.body, { headers: { "Content-Type": compressed ? "application/gzip" : "application/json", "Cache-Control": "no-store" } }) : new Response("No trial result", { status: 404 });
  }
  if (path !== "/run" || request.method !== "POST") return new Response("Not found", { status: 404 });
  if (env.TRIAL_ENABLED !== "true" || !env.GEMINI_API_KEY) return new Response("Trial disabled", { status: 409 });
  return env.TRIAL_CONTAINER.getByName("priority-trial").fetch("http://trial/run", { method: "POST" });
}
