// Exact producer bytes; only these two public snapshots may leave private trial storage.
import { readProducerOutput } from "./live-publication.mjs";
const FILES = { markets: "markets.json", fx: "fx-ecb.json" };
export const SNAPSHOT_LIMIT = 4 * 1024 * 1024;

export function snapshotDate(data, job) {
  const value = job === "markets" ? data?.asof : job === "fx" ? data?.as_of : null;
  const pattern = job === "markets" ? /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/ : /^\d{4}-\d{2}-\d{2}$/;
  const time = typeof value === "string" && pattern.test(value) ? Date.parse(value) : NaN;
  if (!Number.isFinite(time) || new Date(time).toISOString().slice(0, 10) !== value.slice(0, 10) || time > Date.now() + 300000)
    throw new Error("Invalid snapshot date");
  if (job === "markets") {
    if (!Array.isArray(data.assets) || !data.assets.length || data.assets.length > 1000
        || data.assets.some(a => typeof a?.s !== "string" || !a.s || a.s.length > 80)
        || new Set(data.assets.map(a => a.s)).size !== data.assets.length) throw new Error("Invalid markets snapshot");
  } else if (job === "fx") {
    if (data.schema !== "investedia.fx-ecb/v1" || !data.usd || Object.keys(data.usd).length < 20
        || Object.entries(data.usd).some(([code, rate]) => !/^[A-Z]{3}$/.test(code) || !Number.isFinite(rate) || rate <= 0))
      throw new Error("Invalid FX snapshot");
  } else throw new Error("Unsupported snapshot");
  return value;
}

export async function publishSnapshot(port, env, job) {
  if (env.DATA_PUBLICATION_ENABLED !== "true" || !Object.hasOwn(FILES, job) || !env.TRIAL_STORE)
    throw new Error("Snapshot publication disabled");
  const bytes = await readProducerOutput(port, job, SNAPSHOT_LIMIT);
  const asOf = snapshotDate(JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)), job);
  const sha256 = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), x => x.toString(16).padStart(2, "0")).join("");
  const key = "published/data/" + FILES[job], old = await env.TRIAL_STORE.head(key);
  if (old) {
    const previous = old.customMetadata?.asof;
    if (!previous || !Number.isFinite(Date.parse(previous)) || Date.parse(previous) > Date.parse(asOf)) throw new Error("Newer snapshot preserved");
    if (old.size === bytes.byteLength && previous === asOf && old.customMetadata?.sha256 === sha256) return { written: false, as_of: asOf, sha256 };
  }
  await env.TRIAL_STORE.put(key, bytes, { httpMetadata: { contentType: "application/json; charset=utf-8" }, customMetadata: { asof: asOf, sha256 } });
  return { written: true, as_of: asOf, sha256 };
}
