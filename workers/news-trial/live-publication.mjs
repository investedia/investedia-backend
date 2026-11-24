// Existing authenticated live API only; the Container never receives the ingest token.
import { bounded } from "./index-publication.mjs";
const TARGETS = {
  news: ["/v1/ingest/news", 400000], connections: ["/v1/ingest/connections", 2 * 1024 * 1024],
  library: ["/v1/ingest/library", 900000], calendar: ["/v1/ingest/calendar", 2 * 1024 * 1024]
};
export async function prepareLiveInputs(port, job) {
  const kinds = job === "news" ? ["news", "connections", "library"] : job === "calendar" ? ["calendar"] : null;
  if (!kinds) throw new Error("Unsupported live job");
  const inputs = {};
  for (const kind of kinds) {
    const response = await port.fetch("http://container/output?kind=" + kind);
    if (kind === "library" && response.status === 404) { await response.body?.cancel(); continue; }
    inputs[kind] = await bounded(response, TARGETS[kind][1]);
  }
  return inputs;
}
export async function postLiveInputs(inputs, env, fetchFn) {
  const token = env.LIVE_INGEST_TOKEN?.trim();
  if (env.LIVE_INGEST_ENABLED !== "true" || !token || /[\r\n]/.test(token)) throw new Error("Live ingestion disabled");
  const send = fetchFn || (env.LIVE_API && ((url, options) => env.LIVE_API.fetch(url, options)));
  if (!send) throw new Error("Live API binding missing");
  const kinds = Object.keys(inputs);
  if (!(kinds.length === 1 && kinds[0] === "calendar")
      && !(kinds.includes("news") && kinds.includes("connections") && kinds.every(k => ["news", "connections", "library"].includes(k))))
    throw new Error("Invalid live input set");
  // Check the whole set before sending even the first request.
  for (const kind of kinds) if (!(inputs[kind] instanceof Uint8Array) || !inputs[kind].byteLength || inputs[kind].byteLength > TARGETS[kind][1]) throw new Error("Invalid live payload");
  const results = {};
  for (const kind of kinds) {
    let response, status = 0;
    try {
      response = await send("https://api.investedia.com" + TARGETS[kind][0], {
        method: "POST", redirect: "manual", signal: AbortSignal.timeout(30000), body: inputs[kind],
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + token, "User-Agent": "InvestediaRobot/1.0" }
      });
      status = response.status;
      if (status !== 200) { await response.body?.cancel(); throw new Error("Live request rejected"); }
      const result = JSON.parse(new TextDecoder().decode(await bounded(response, 1024 * 1024)));
      if (result?.ok !== true) throw new Error("Live request not acknowledged");
      results[kind] = { ok: true, ...(typeof result.written === "boolean" || (Number.isSafeInteger(result.written) && result.written >= 0) ? { written: result.written } : {}),
        ...(Number.isSafeInteger(result.count) && result.count >= 0 ? { count: result.count } : {}) };
    } catch {
      console.warn("live_ingest_failure", JSON.stringify({ kind, http_status: status }));
      if (kind !== "library") throw new Error("Live " + kind + " ingestion failed");
      // Preserve the original pipeline's best-effort compact-day sync; full R2 articles are already published.
      results.library = { ok: false };
    }
  }
  return results;
}
