import { DurableObject, WorkerEntrypoint } from "cloudflare:workers";
import { egress, route } from "./policy.mjs";

export class TrialEgress extends WorkerEntrypoint {
  fetch(request) { return egress(request, this.env.GEMINI_API_KEY, this.env.TRIAL_ENABLED === "true"); }
}
export class NewsTrial extends DurableObject {
  busy = false;
  async fetch() {
    if (this.busy) return new Response("Trial already running", { status: 409 });
    if (this.env.TRIAL_ENABLED !== "true" || !this.env.GEMINI_API_KEY) return new Response("Trial disabled", { status: 409 });
    this.busy = true;
    const c = this.ctx.container;
    try {
      const seed = await this.env.TRIAL_STORE.get("trial/state.json") || await this.env.TRIAL_STORE.get("trial/seed.json");
      if (!seed || seed.size > 32 * 1024 * 1024) return new Response("Trial seed missing or too large", { status: 409 });
      if (c.running) await c.destroy();
      c.start({ image: c.images.base, instance: "lite", enableInternet: false });
      await c.setInactivityTimeout(15 * 60 * 1000);
      await c.interceptOutboundHttps("*", this.ctx.exports.TrialEgress({ props: {} }));
      const port = c.getTcpPort(8080);
      let ready = false;
      for (let i = 0; i < 60; i++) {
        try { ready = (await port.fetch("http://container/health")).ok; } catch {}
        if (ready) break;
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      if (!ready) throw new Error("Container unavailable");
      const response = await port.fetch("http://container/run", { method: "POST", body: await seed.arrayBuffer() });
      if (!response.ok) throw new Error("Producer failed");
      const result = await response.text();
      if (new TextEncoder().encode(result).length > 32 * 1024 * 1024) throw new Error("Result too large");
      const data = JSON.parse(result);
      if (data.summary?.trial !== true || !data.files) throw new Error("Invalid result");
      // Save the review artifact first; a failed generation never advances trial state.
      await this.env.TRIAL_STORE.put("trial/latest.json", result);
      await this.env.TRIAL_STORE.put("trial/state.json", JSON.stringify({ files: data.files }));
      return Response.json(data.summary);
    } catch {
      return new Response("Trial failed; production untouched", { status: 502 });
    } finally {
      try { if (c.running) await c.destroy(); } finally { this.busy = false; }
    }
  }
}
export default { fetch: route };
