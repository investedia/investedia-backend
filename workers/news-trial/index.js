import { DurableObject, WorkerEntrypoint } from "cloudflare:workers";
import { prepareLiveInputs, postLiveInputs } from "./live-publication.mjs";
import { readIndexInput, publishedIds, publishIndexExports } from "./index-publication.mjs";
import { storeTrialLibrary, publishLibraryPage } from "./library.mjs";
import { egress, route, trialTier, trialJob, safeDiagnostic } from "./policy.mjs";

export class TrialEgress extends WorkerEntrypoint {
  fetch(request) { if (this.ctx.props.job === "library-index") return readIndexInput(request, this.env); return egress(request, this.ctx.props.job === "news" ? this.env.GEMINI_API_KEY : "", this.env.TRIAL_ENABLED === "true", fetch, this.ctx.props.job === "calendar" ? this.env.FRED_API_KEY : ""); }
}
export class NewsTrial extends DurableObject {
  busy = false;
  async startContainer(job) {
    const c = this.ctx.container;
    if (c.running) await c.destroy();
    c.start({ image: c.images.base, instance: "basic", enableInternet: false });
    await c.setInactivityTimeout(15 * 60 * 1000);
    const proxy = this.ctx.exports.TrialEgress({ props: { job } });
    await c.interceptOutboundHttps("*", proxy);
    await c.interceptAllOutboundHttp(proxy);
    for (let i = 0; i < 60; i++) {
      try { if ((await c.getTcpPort(8080).fetch("http://container/health")).ok) return c; } catch {}
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    throw new Error("Container unavailable");
  }
  async buildIndex() {
    const ids = await publishedIds(this.env.TRIAL_STORE);
    const c = await this.startContainer("library-index");
    const result = await c.getTcpPort(8080).fetch("http://container/run?job=library-index", { method: "POST", body: JSON.stringify({ ids }) });
    if (!result.ok) { await result.body?.cancel(); throw new Error("Index generation failed"); }
    const summary = JSON.parse(result.headers.get("X-Trial-Summary"));
    await result.body?.cancel();
    const published = await publishIndexExports({ fetch: request => c.getTcpPort(8080).fetch(request) }, this.env.TRIAL_STORE);
    return { ...summary, ...published };
  }
  async publishIndex() {
    if (this.env.PUBLISH_LIBRARY_ENABLED !== "true") return new Response("Article publication disabled", { status: 409 });
    if (this.busy) return new Response("Trial already running", { status: 409 });
    this.busy = true;
    try { return Response.json(await this.buildIndex()); }
    catch { return Response.json({ error: "index_publication_failed", previous_index_preserved: true }, { status: 502 }); }
    finally { try { if (this.ctx.container.running) await this.ctx.container.destroy(); } finally { this.busy = false; } }
  }
  async publishLibrary() {
    if (this.env.PUBLISH_LIBRARY_ENABLED !== "true") return new Response("Article publication disabled", { status: 409 });
    if (this.busy) return new Response("Trial already running", { status: 409 });
    this.busy = true;
    try {
      const cursor = await this.ctx.storage.get("library:publish:cursor");
      const result = await publishLibraryPage(this.env.TRIAL_STORE, cursor);
      if (result.cursor) await this.ctx.storage.put("library:publish:cursor", result.cursor);
      else await this.ctx.storage.delete("library:publish:cursor");
      return Response.json({ examined: result.examined, written: result.written, done: result.cursor === null });
    } catch {
      return Response.json({ error: "article_publication_failed", existing_articles_preserved: true }, { status: 502 });
    } finally { this.busy = false; }
  }
  async fetch(request = new Request("http://trial/run")) {
    if (new URL(request.url).pathname === "/publish-library-index") return this.publishIndex();
    if (new URL(request.url).pathname === "/publish-library") return this.publishLibrary();
    const job = trialJob(request);
    if (!job) return new Response("Unknown trial job", { status: 400 });
    const prefix = job === "news" ? "trial" : `trial/${job}`;
    const tier = trialTier(request);
    if (!tier) return new Response("Unknown news tier", { status: 400 });
    if (this.busy) return new Response("Trial already running", { status: 409 });
    if (this.env.TRIAL_ENABLED !== "true" || (job === "news" && !this.env.GEMINI_API_KEY)) return new Response("Trial disabled", { status: 409 });
    if (["news", "calendar"].includes(job) && this.env.LIVE_INGEST_ENABLED === "true"
        && (!this.env.LIVE_API || !this.env.LIVE_INGEST_TOKEN?.trim() || /[\r\n]/.test(this.env.LIVE_INGEST_TOKEN.trim()) || (job === "news" && this.env.PUBLISH_LIBRARY_ENABLED !== "true")))
      return new Response("Live ingestion prerequisites missing", { status: 409 });
    this.busy = true;
    const c = this.ctx.container;
    let stage = "seed";
    try {
      const seed = await this.env.TRIAL_STORE.get(`${prefix}/state.json.gz`) || await this.env.TRIAL_STORE.get(`${prefix}/state.json`)
        || await this.env.TRIAL_STORE.get(`${prefix}/seed.json.gz`) || await this.env.TRIAL_STORE.get(`${prefix}/seed.json`);
      if (!seed || seed.size > 32 * 1024 * 1024) return new Response("Trial seed missing or too large", { status: 409 });
      stage = "container";
      await this.startContainer(job);
      const port = c.getTcpPort(8080);
      stage = "producer";
      const response = await port.fetch(`http://container/run?tier=${tier}&job=${job}`, { method: "POST", body: await seed.arrayBuffer(), headers: { "X-Fred-Enabled": job === "calendar" && this.env.FRED_API_KEY ? "1" : "0", "X-Live-Export": ["news", "calendar"].includes(job) && this.env.LIVE_INGEST_ENABLED === "true" ? "1" : "0" } });
      if (!response.ok) {
        let failure; try { failure = await response.json(); } catch {}
        const diagnostic = failure?.error === "generation_failed" ? safeDiagnostic(failure.diagnostic) : null;
        if (diagnostic) return Response.json({ error: "trial_failed", stage, tier, diagnostic, production_untouched: true }, { status: 502 });
        throw new Error("Producer failed");
      }
      const result = await response.arrayBuffer();
      const bytes = new Uint8Array(result);
      if (bytes.length > 32 * 1024 * 1024 || bytes[0] !== 31 || bytes[1] !== 139) throw new Error("Invalid compressed result");
      const header = response.headers.get("X-Trial-Summary");
      if (!header || header.length > 4096) throw new Error("Invalid summary");
      const summary = JSON.parse(header);
      if (summary?.trial !== true || (job === "news" ? summary.tier !== tier : summary.job !== job)) throw new Error("Invalid result");
      let liveInputs;
      if (["news", "calendar"].includes(job) && this.env.LIVE_INGEST_ENABLED === "true") {
        stage = "live-export";
        liveInputs = await prepareLiveInputs({ fetch: request => c.getTcpPort(8080).fetch(request) }, job);
      }
      if (["news", "library"].includes(job)) {
        stage = "library";
        // Reacquire the port after each HTTP/1.0 response closes its connection.
        const library = await storeTrialLibrary({ fetch: request => c.getTcpPort(8080).fetch(request) }, this.env.TRIAL_STORE, summary.library_articles);
        summary.library_written = library.written;
        if (job === "news" && this.env.PUBLISH_LIBRARY_ENABLED === "true") {
          const published = await storeTrialLibrary({ fetch: request => c.getTcpPort(8080).fetch(request) }, this.env.TRIAL_STORE, summary.library_articles, "published", this.env.LIVE_INGEST_ENABLED === "true" ? "export" : "saved");
          summary.published_articles_written = published.written;
          stage = "index";
          summary.library_index = await this.buildIndex();
        }
      }
      if (liveInputs) {
        stage = "live-ingest";
        summary.live_ingest = await postLiveInputs(liveInputs, this.env);
      }
      // Keep the large archive opaque here; parsing it in the Worker can exhaust memory.
      stage = "storage";
      await this.env.TRIAL_STORE.put(`${prefix}/latest.json.gz`, result, { httpMetadata: { contentType: "application/gzip" } });
      await this.env.TRIAL_STORE.put(`${prefix}/state.json.gz`, result, { httpMetadata: { contentType: "application/gzip" } });
      return Response.json(summary);
    } catch {
      return Response.json({ error: "trial_failed", stage, tier, production_untouched: this.env.PUBLISH_LIBRARY_ENABLED !== "true" && this.env.LIVE_INGEST_ENABLED !== "true" }, { status: 502 });
    } finally {
      try { if (c.running) await c.destroy(); } finally { this.busy = false; }
    }
  }
}
export default { fetch: route };
