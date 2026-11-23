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
    const source = new URL(url);
    if (source.protocol === "http:" && !source.port && SOURCE_HOSTS.has(source.hostname) && request.method === "GET") {
      source.protocol = "https:"; url = source.href;
    }
    const type = destination(url, request.method);
    if (!type) return new Response("Trial destination denied", { status: 403 });
    // Do not forward caller headers, cookies or credentials to publisher sites.
    const headers = new Headers({ "User-Agent": "InvestediaNews/1.0 (+https://investedia.com; info@investedia.com)" });
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
export function trialTier(request) {
  const values = new URL(request.url).searchParams.getAll("tier");
  if (values.length > 1) return null;
  const tier = values[0] || "priority";
  return ["priority", "broad"].includes(tier) ? tier : null;
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
  const tier = trialTier(request);
  if (!tier) return new Response("Unknown news tier", { status: 400 });
  return env.TRIAL_CONTAINER.getByName("priority-trial").fetch(`http://trial/run?tier=${tier}`, { method: "POST" });
}
