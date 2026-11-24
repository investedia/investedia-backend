// Reuse the existing authenticated producer path through private Durable Object bindings.
import { bounded } from "./index-publication.mjs";
export const DATA_SCHEDULES = {
  "23 */6 * * *": "calendar", "43 21 * * MON-FRI": "markets",
  "37 15 * * MON-FRI": "fx", "12 6 * * SUN": "economy-history"
};
// Stagger broad by ten minutes; both tiers use one locked producer/state.
export const NEWS_SCHEDULES = { "17,47 * * * *": "priority", "7 */2 * * *": "broad" };
const SCHEDULES = { ...DATA_SCHEDULES, ...NEWS_SCHEDULES };
export function scheduledJobs(env) {
  const raw = env.SCHEDULED_JOBS?.trim();
  if (!raw || raw === "off") return [];
  const jobs = raw.split(",").map(value => value.trim());
  if (new Set(jobs).size !== jobs.length || jobs.some(job => !Object.values(SCHEDULES).includes(job))) throw Error("Invalid scheduled jobs");
  return jobs;
}
export async function runScheduled(event, env) {
  const jobs = scheduledJobs(env), job = SCHEDULES[event.cron];
  if (!jobs.length || !job || !jobs.includes(job)) return;
  if (!Number.isFinite(event.scheduledTime) || event.scheduledTime < 0) throw Error("Invalid scheduled time");
  const started = new Date(event.scheduledTime).toISOString();
  const news = ["priority", "broad"].includes(job);
  let status = 0, stage = "prerequisites";
  const record = ok => ({ job, ok, scheduled_at: started, finished_at: new Date().toISOString(), http_status: status, stage });
  try {
    if (env.TRIAL_ENABLED !== "true" || !env.TRIAL_STORE || !env.TRIAL_CONTAINER
        || (news && (env.PUBLISH_LIBRARY_ENABLED !== "true" || !env.GEMINI_API_KEY?.trim()))
        || ((news || job === "calendar") && (env.LIVE_INGEST_ENABLED !== "true" || !env.LIVE_API || !env.LIVE_INGEST_TOKEN?.trim()))
        || (job === "calendar" && !env.FRED_API_KEY?.trim())
        || (["markets", "fx"].includes(job) && env.DATA_PUBLICATION_ENABLED !== "true")) throw Error("Scheduler prerequisites missing");
    stage = "producer";
    const response = await env.TRIAL_CONTAINER.getByName(news ? "news-trial" : job + "-trial").fetch(news ? "http://trial/run?job=news&tier=" + job : "http://trial/run?job=" + job, { method: "POST" });
    status = response.status;
    if (status !== 200) { await response.body?.cancel(); throw Error("Scheduled producer failed"); }
    const result = JSON.parse(new TextDecoder().decode(await bounded(response, 16384)));
    if (result?.trial !== true || (news ? result.tier !== job : result.job !== job)
        || (news ? result.live_ingest?.news?.ok !== true || result.live_ingest?.connections?.ok !== true
          || !Number.isSafeInteger(result.published_articles_written) || result.published_articles_written < 0
          || !/^[0-9a-f]{64}$/.test(result.library_index?.version)
          : job === "calendar" ? result.live_ingest?.calendar?.ok !== true : result.gemini_calls !== 0)
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
