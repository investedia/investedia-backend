// Reuse the existing authenticated producer path through private Durable Object bindings.
import { bounded } from "./index-publication.mjs";
export const DATA_SCHEDULES = {
  "23 */6 * * *": "calendar", "43 21 * * 1-5": "markets",
  "37 15 * * 1-5": "fx", "12 6 * * 0": "economy-history"
};
export function scheduledJobs(env) {
  const raw = env.SCHEDULED_JOBS?.trim();
  if (!raw || raw === "off") return [];
  const jobs = raw.split(",").map(value => value.trim());
  if (new Set(jobs).size !== jobs.length || jobs.some(job => !Object.values(DATA_SCHEDULES).includes(job))) throw Error("Invalid scheduled jobs");
  return jobs;
}
export async function runScheduled(event, env) {
  const jobs = scheduledJobs(env), job = DATA_SCHEDULES[event.cron];
  if (!jobs.length || !job || !jobs.includes(job)) return;
  if (!Number.isFinite(event.scheduledTime) || event.scheduledTime < 0) throw Error("Invalid scheduled time");
  const started = new Date(event.scheduledTime).toISOString();
  let status = 0, stage = "prerequisites";
  const record = ok => ({ job, ok, scheduled_at: started, finished_at: new Date().toISOString(), http_status: status, stage });
  try {
    if (env.TRIAL_ENABLED !== "true" || !env.TRIAL_STORE || !env.TRIAL_CONTAINER
        || (job === "calendar" && (env.LIVE_INGEST_ENABLED !== "true" || !env.LIVE_API || !env.LIVE_INGEST_TOKEN?.trim() || !env.FRED_API_KEY?.trim()))
        || (["markets", "fx"].includes(job) && env.DATA_PUBLICATION_ENABLED !== "true")) throw Error("Scheduler prerequisites missing");
    stage = "producer";
    const response = await env.TRIAL_CONTAINER.getByName(job + "-trial").fetch("http://trial/run?job=" + job, { method: "POST" });
    status = response.status;
    if (status !== 200) { await response.body?.cancel(); throw Error("Scheduled producer failed"); }
    const result = JSON.parse(new TextDecoder().decode(await bounded(response, 16384)));
    if (result?.trial !== true || result.job !== job
        || (job === "calendar" ? result.live_ingest?.calendar?.ok !== true : result.gemini_calls !== 0)
        || (["markets", "fx"].includes(job) && typeof result.published_snapshot?.written !== "boolean")
        || (job === "economy-history" && result.review_only !== true)) throw Error("Scheduled result not acknowledged");
    stage = "monitoring";
    const body = JSON.stringify({ ...record(true), stage: "complete" }), options = { httpMetadata: { contentType: "application/json" } };
    await env.TRIAL_STORE.put(`operations/schedules/${job}/last-success.json`, body, options);
    await env.TRIAL_STORE.put(`operations/schedules/${job}/last-attempt.json`, body, options);
    console.log("scheduled_job_success", JSON.stringify({ job, http_status: status }));
  } catch {
    try { await env.TRIAL_STORE?.put(`operations/schedules/${job}/last-attempt.json`, JSON.stringify(record(false)), { httpMetadata: { contentType: "application/json" } }); } catch {}
    console.warn("scheduled_job_failure", JSON.stringify({ job, http_status: status, stage }));
    throw Error("Scheduled " + job + " failed");
  }
}
