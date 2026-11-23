// Exact producer feed hosts. Redirects must pass the same policy on every hop.
export const SOURCE_HOSTS = new Set([
  "addisfortune.news",
  "africa.businessinsider.com",
  "african.business",
  "agenciabrasil.ebc.com.br",
  "allafrica.com",
  "api.gdeltproject.org",
  "astanatimes.com",
  "boj.org.jm",
  "borsen.dk",
  "boss.gov.ss",
  "braziljournal.com",
  "businessday.ng",
  "businessinsider.com.pl",
  "businesstech.co.za",
  "cbl.gov.ly",
  "cbos.gov.sd",
  "colombiaone.com",
  "dailynewsegypt.com",
  "daryo.uz",
  "dominicantoday.com",
  "e.vnexpress.net",
  "e24.no",
  "ec.europa.eu",
  "economictimes.indiatimes.com",
  "egyptindependent.com",
  "elcomercio.pe",
  "en.antaranews.com",
  "en.globes.co.il",
  "en.hespress.com",
  "en.mercopress.com",
  "en.trend.az",
  "exame.com",
  "expansion.mx",
  "feeds.bbci.co.uk",
  "feeds.content.dowjones.io",
  "feeds.elpais.com",
  "feeds.thelocal.com",
  "gestion.pe",
  "home.treasury.gov",
  "hungarytoday.hu",
  "iol.co.za",
  "jamaica-gleaner.com",
  "japantoday.com",
  "kun.uz",
  "latinamericareports.com",
  "mexiconewsdaily.com",
  "nairametrics.com",
  "ngxgroup.com",
  "notesfrompoland.com",
  "oilprice.com",
  "panampost.com",
  "perureports.com",
  "rss.dw.com",
  "rss.nytimes.com",
  "rthk.hk",
  "saudigazette.com.sa",
  "stockhead.com.au",
  "techcabal.com",
  "theconversation.com",
  "ticotimes.net",
  "www.aa.com.tr",
  "www.abc.net.au",
  "www.africanews.com",
  "www.ambito.com",
  "www.ansa.it",
  "www.bangkokpost.com",
  "www.bankofcanada.ca",
  "www.bankofengland.co.uk",
  "www.banrep.gov.co",
  "www.batimes.com.ar",
  "www.bcb.gob.bo",
  "www.bcb.gov.br",
  "www.bcc.cd",
  "www.bce.fin.ec",
  "www.bceao.int",
  "www.bcn.gob.ni",
  "www.bcr.gob.sv",
  "www.bcrg-guinee.org",
  "www.bea.gov",
  "www.bloomberght.com",
  "www.bloomberglinea.com",
  "www.bls.gov",
  "www.bog.gov.gh",
  "www.boj.or.jp",
  "www.bok.or.kr",
  "www.brecorder.com",
  "www.brh.ht",
  "www.bundesbank.de",
  "www.businessdailyafrica.com",
  "www.businesstimes.com.sg",
  "www.bworldonline.com",
  "www.capitalfm.co.ke",
  "www.cbsl.gov.lk",
  "www.central-bank.org.tt",
  "www.centralbank.go.ke",
  "www.centralbank.org.sz",
  "www.cgtn.com",
  "www.channelnewsasia.com",
  "www.clarin.com",
  "www.coindesk.com",
  "www.dailysabah.com",
  "www.dawn.com",
  "www.df.cl",
  "www.di.se",
  "www.ecb.europa.eu",
  "www.eia.gov",
  "www.elfinanciero.com.mx",
  "www.euractiv.com",
  "www.euronews.com",
  "www.federalreserve.gov",
  "www.finews.com",
  "www.france24.com",
  "www.freemalaysiatoday.com",
  "www.ghanabusinessnews.com",
  "www.gov.uk",
  "www.handelsblatt.com",
  "www.hcp.ma",
  "www.hellenicshippingnews.com",
  "www.hurriyetdailynews.com",
  "www.ilsole24ore.com",
  "www.infobae.com",
  "www.infomoney.com.br",
  "www.investing.com",
  "www.iraq-businessnews.com",
  "www.irishtimes.com",
  "www.istat.it",
  "www.japantimes.co.jp",
  "www.jse.co.za",
  "www.khaleejtimes.com",
  "www.kyivpost.com",
  "www.lanacion.com.ar",
  "www.larepublica.co",
  "www.latercera.com",
  "www.lemonde.fr",
  "www.livemint.com",
  "www.malaymail.com",
  "www.moneytimes.com.br",
  "www.moneyweb.co.za",
  "www.myjoyonline.com",
  "www.namibian.com.na",
  "www.nationalbanken.dk",
  "www.nbb.be",
  "www.newsday.co.zw",
  "www.nzherald.co.nz",
  "www.ons.gov.uk",
  "www.pbs.gov.pk",
  "www.philstar.com",
  "www.politico.eu",
  "www.portafolio.co",
  "www.postcourier.com.pg",
  "www.premiumtimesng.com",
  "www.prnewswire.com",
  "www.rba.gov.au",
  "www.rbi.org.in",
  "www.rbnz.govt.nz",
  "www.riksbank.se",
  "www.riotimesonline.com",
  "www.rnz.co.nz",
  "www.romania-insider.com",
  "www.scb.se",
  "www.scmp.com",
  "www.sec.gov",
  "www.smh.com.au",
  "www.snb.ch",
  "www.ssb.no",
  "www.standardmedia.co.ke",
  "www.straitstimes.com",
  "www.tagesschau.de",
  "www.thedailystar.net",
  "www.theglobeandmail.com",
  "www.theguardian.com",
  "www.thehindubusinessline.com",
  "www.thenationalnews.com",
  "zimstat.co.zw"
]);
export function destination(url, method) {
  const u = new URL(url);
  if (u.protocol !== "https:" || u.username || u.password || (u.port && u.port !== "443")) return null;
  if (u.hostname === "api.stlouisfed.org" && method === "GET" && ["/fred/releases/dates", "/fred/series/observations"].includes(u.pathname)) return "fred";
  if (method === "GET" && ((u.hostname === "api.worldbank.org" && /^\/v2\/country\/all\/indicator\/[A-Z0-9.]+$/.test(u.pathname))
      || (u.hostname === "query1.finance.yahoo.com" && /^\/v8\/finance\/chart\/[^/]+$/.test(u.pathname)))) return "source";
  if (SOURCE_HOSTS.has(u.hostname) && method === "GET") return "source";
  if (u.hostname !== "generativelanguage.googleapis.com") return null;
  if (method === "GET" && u.pathname === "/v1beta/models" && u.search === "?pageSize=200") return "gemini";
  if (method === "POST" && /^\/v1beta\/models\/[a-zA-Z0-9.-]+:generateContent$/.test(u.pathname) && !u.search) return "gemini";
  return null;
}
// Return a fixed category only; provider messages may contain credentials.
async function fredFailure(response) {
  if (response.status === 429 || response.status >= 500) {
    if (response.body) await response.body.cancel().catch(() => {});
    return response.status === 429 ? "rate_limited" : "upstream_unavailable";
  }
  let message = "";
  if (response.body) {
    const reader = response.body.getReader();
    const chunks = []; let size = 0;
    try {
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        size += value.length; if (size > 16384) return "request_rejected";
        chunks.push(value);
      }
      const body = new Uint8Array(size); let offset = 0;
      for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.length; }
      const data = JSON.parse(new TextDecoder().decode(body));
      if (typeof data.error_message === "string") message = data.error_message.replace(/https?:\/\/\S+/g, "").toLowerCase();
    } catch {} finally { await reader.cancel().catch(() => {}); }
  }
  if (/api[_ ]key/.test(message) && /not registered|not set|invalid|32 character/.test(message)) return "key_rejected";
  if (/realtime_start|realtime_end|order_by|sort_order|limit|include_release_dates_with_no_data/.test(message)) return "request_parameters";
  return "request_rejected";
}
export async function egress(request, key, enabled, upstream = fetch, fredKey = "") {
  if (!enabled) return new Response("Trial egress disabled", { status: 403 });
  fredKey = typeof fredKey === "string" ? fredKey.trim() : "";
  let url = request.url;
  for (let hop = 0; hop < 5; hop++) {
    const source = new URL(url);
    if (source.protocol === "http:" && !source.port && SOURCE_HOSTS.has(source.hostname) && request.method === "GET") {
      source.protocol = "https:"; url = source.href;
    }
    const type = destination(url, request.method);
    if (!type || (type === "gemini" && !key)) return new Response("Trial destination denied", { status: 403 });
    // Preserve only the producer's public negotiation headers, never cookies or credentials.
    const headers = new Headers({ "User-Agent": (request.headers.get("User-Agent") || "InvestediaNews/1.0").slice(0, 256) });
    for (const name of ["Accept", "Accept-Language"]) {
      const value = request.headers.get(name); if (value) headers.set(name, value.slice(0, 256));
    }
    if (type === "gemini") { headers.set("x-goog-api-key", key); headers.set("Content-Type", "application/json"); }
    if (type === "fred") {
      if (!/^[a-z0-9]{32}$/.test(fredKey)) return Response.json({ trial_fred_reason: "key_format" }, { status: 400 });
      const target = new URL(url); target.searchParams.set("api_key", fredKey); url = target.href;
    }
    const response = await upstream(url, { method: request.method, headers,
      body: request.method === "POST" ? await request.clone().arrayBuffer() : undefined, redirect: "manual" });
    if (response.status >= 300 && response.status < 400) {
      const next = response.headers.get("location");
      if (!next || request.method !== "GET" || type === "fred") return new Response("Trial redirect denied", { status: 502 });
      url = new URL(next, url).href;
      continue;
    }
    if (!response.ok) {
      if (type === "fred") return Response.json({ trial_fred_reason: await fredFailure(response) }, { status: response.status });
      return new Response("Trial upstream failed", { status: response.status });
    }
    return new Response(response.body, { status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/octet-stream" } });
  }
  return new Response("Trial redirect limit", { status: 502 });
}
export function trialTier(request) {
  const values = new URL(request.url).searchParams.getAll("tier");
  if (values.length > 1) return null;
  const tier = values[0] || "priority";
  return ["priority", "broad"].includes(tier) ? tier : null;
}
export function safeDiagnostic(value) {
  if (!value || typeof value !== "object") return null;
  const out = {};
  for (const name of ["fetched", "candidates", "failed_source_count"]) {
    if (!Number.isSafeInteger(value[name]) || value[name] < 0 || value[name] > 1000000) return null;
    out[name] = value[name];
  }
  out.gemini_ok = value.gemini_ok === true;
  out.http_statuses = Array.isArray(value.http_statuses) ? value.http_statuses.filter(n => Number.isSafeInteger(n) && n >= 100 && n <= 599).slice(0, 10) : [];
  return out;
}
export function trialJob(request) {
  const values = new URL(request.url).searchParams.getAll("job");
  if (values.length > 1) return null;
  const job = values[0] || "news";
  return ["news", "calendar", "markets", "fx", "economy-history", "country-basics"].includes(job) ? job : null;
}
export async function route(request, env) {
  if (!env.TRIAL_TOKEN || request.headers.get("Authorization") !== `Bearer ${env.TRIAL_TOKEN}`)
    return new Response("Unauthorized", { status: 401 });
  const path = new URL(request.url).pathname;
  const job = trialJob(request);
  if (!job) return new Response("Unknown trial job", { status: 400 });
  const prefix = job === "news" ? "trial" : `trial/${job}`;
  if (path === "/health" && request.method === "GET") return Response.json({ trial: true, enabled: env.TRIAL_ENABLED === "true", scheduled: false });
  if (path === "/result" && request.method === "GET") {
    const compressed = await env.TRIAL_STORE.get(`${prefix}/latest.json.gz`);
    const saved = compressed || await env.TRIAL_STORE.get(`${prefix}/latest.json`);
    return saved ? new Response(saved.body, { headers: { "Content-Type": compressed ? "application/gzip" : "application/json", "Cache-Control": "no-store" } }) : new Response("No trial result", { status: 404 });
  }
  if (path !== "/run" || request.method !== "POST") return new Response("Not found", { status: 404 });
  if (env.TRIAL_ENABLED !== "true" || (job === "news" && !env.GEMINI_API_KEY)) return new Response("Trial disabled", { status: 409 });
  const tier = trialTier(request);
  if (!tier) return new Response("Unknown news tier", { status: 400 });
  return env.TRIAL_CONTAINER.getByName(job === "news" ? "priority-trial" : `${job}-trial`).fetch(`http://trial/run?tier=${tier}&job=${job}`, { method: "POST" });
}
