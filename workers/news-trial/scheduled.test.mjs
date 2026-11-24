import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { DATA_SCHEDULES, scheduledJobs, runScheduled } from "./scheduled.mjs";
const time = Date.UTC(2026, 10, 24, 15, 37);
const result = job => ({ trial: true, job, gemini_calls: 0, ...(job === "calendar" ? { live_ingest: { calendar: { ok: true } } } : job === "economy-history" ? { review_only: true } : { published_snapshot: { written: true } }) });
function fixture(job) {
  const calls = [], writes = new Map();
  const env = { SCHEDULED_JOBS: job, TRIAL_ENABLED: "true", DATA_PUBLICATION_ENABLED: "true", LIVE_INGEST_ENABLED: "true", LIVE_INGEST_TOKEN: "offline-control", FRED_API_KEY: "offline-fred", LIVE_API: {},
    TRIAL_CONTAINER: { getByName: name => ({ fetch: async (url, options) => { calls.push({ name, url, options }); return Response.json(result(job)); } }) },
    TRIAL_STORE: { put: async (key, body) => writes.set(key, JSON.parse(body)) }
  };
  return { env, calls, writes };
}
test("default-off and unselected jobs do not touch bindings; unknown or repeated jobs fail closed", async () => {
  for (const value of [undefined, "off", ""]) {
    assert.deepEqual(scheduledJobs({ SCHEDULED_JOBS: value }), []);
    await runScheduled({ cron: "37 15 * * MON-FRI", scheduledTime: time }, { SCHEDULED_JOBS: value });
  }
  for (const value of ["news", "markets,markets", "calendar,", "country-basics", "../private"]) assert.throws(() => scheduledJobs({ SCHEDULED_JOBS: value }));
  const b = fixture("markets"); await runScheduled({ cron: "37 15 * * MON-FRI", scheduledTime: time }, b.env);
  assert.equal(b.calls.length, 0); assert.equal(b.writes.size, 0);
});
test("each exact existing UTC schedule calls only its private job and records success", async () => {
  for (const [cron, job] of Object.entries(DATA_SCHEDULES)) {
    const b = fixture(job); await runScheduled({ cron, scheduledTime: time }, b.env);
    assert.equal(b.calls.length, 1); assert.equal(b.calls[0].name, job + "-trial");
    assert.equal(b.calls[0].url, "http://trial/run?job=" + job); assert.deepEqual(b.calls[0].options, { method: "POST" });
    assert.equal(b.writes.size, 2);
    const saved = b.writes.get(`operations/schedules/${job}/last-success.json`);
    assert.equal(saved.ok, true); assert.equal(saved.scheduled_at, new Date(time).toISOString());
    assert.equal(JSON.stringify(saved).includes("offline-control"), false);
  }
});
test("missing activation/publication prerequisites stop before a paid Container call", async () => {
  for (const [job, key] of [["markets", "TRIAL_ENABLED"], ["markets", "DATA_PUBLICATION_ENABLED"], ["calendar", "LIVE_INGEST_TOKEN"], ["calendar", "FRED_API_KEY"], ["calendar", "LIVE_API"]]) {
    const b = fixture(job); delete b.env[key];
    await assert.rejects(runScheduled({ cron: Object.keys(DATA_SCHEDULES).find(c => DATA_SCHEDULES[c] === job), scheduledTime: time }, b.env));
    assert.equal(b.calls.length, 0); assert.equal([...b.writes.keys()].some(key => key.includes("last-success")), false);
  }
});
test("failed and unacknowledged runs retain last success, log fixed fields and fail the cron event", async () => {
  const original = console.warn, logs = []; console.warn = (...args) => logs.push(args);
  try {
    for (const response of [new Response("private response must not leak", { status: 503 }), new Response("busy", { status: 409 }), Response.json({ trial: true, job: "fx", gemini_calls: 0 })]) {
      const b = fixture("fx"), key = "operations/schedules/fx/last-success.json"; b.writes.set(key, { previous: true });
      b.env.TRIAL_CONTAINER.getByName = () => ({ fetch: async () => response });
      await assert.rejects(runScheduled({ cron: "37 15 * * MON-FRI", scheduledTime: time }, b.env));
      assert.deepEqual(b.writes.get(key), { previous: true }); assert.equal(b.writes.get("operations/schedules/fx/last-attempt.json").ok, false);
    }
  } finally { console.warn = original; }
  assert.equal(JSON.stringify(logs).includes("private response"), false);
  for (const [marker, payload] of logs) { assert.equal(marker, "scheduled_job_failure"); assert.deepEqual(Object.keys(JSON.parse(payload)).sort(), ["http_status", "job", "stage"]); }
});
test("review jobs cannot acknowledge accidental publication and monitoring errors remain failures", async () => {
  const b = fixture("economy-history"); b.env.TRIAL_CONTAINER.getByName = () => ({ fetch: async () => Response.json({ ...result("economy-history"), review_only: false }) });
  await assert.rejects(runScheduled({ cron: "12 6 * * SUN", scheduledTime: time }, b.env));
  assert.equal(b.writes.has("operations/schedules/economy-history/last-success.json"), false);
  const c = fixture("markets"); c.env.TRIAL_STORE.put = async () => { throw Error("private storage error"); };
  await assert.rejects(runScheduled({ cron: "43 21 * * MON-FRI", scheduledTime: time }, c.env), /Scheduled markets failed/);
});
test("Cloudflare named weekdays preserve intended weekdays/Sunday and scheduler defaults off", async () => {
  const config = await readFile(new URL("./wrangler.toml", import.meta.url), "utf8");
  assert.match(config, /SCHEDULED_JOBS = "off"/);
  for (const cron of Object.keys(DATA_SCHEDULES)) assert.ok(config.includes('"' + cron + '"'));
  const calendar = await readFile(new URL("../../.github/workflows/calendar.yml", import.meta.url), "utf8");
  assert.ok(calendar.includes("23 */6 * * *")); assert.ok(calendar.includes("github.event_name != 'schedule' || vars.CLOUDFLARE_CALENDAR_ENABLED != 'true'"));
  assert.ok(calendar.includes("workflow_dispatch:"));
});

test("Cloudflare weekday dialect cannot copy GitHub zero-based numeric days", () => {
  const intended = { calendar: "*", markets: "MON-FRI", fx: "MON-FRI", "economy-history": "SUN" };
  for (const [cron, job] of Object.entries(DATA_SCHEDULES)) assert.equal(cron.split(" ")[4], intended[job]);
  assert.equal(DATA_SCHEDULES["43 21 * * 1-5"], undefined);
  assert.equal(DATA_SCHEDULES["12 6 * * 0"], undefined);

});
