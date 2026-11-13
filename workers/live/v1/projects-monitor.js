// Weekly project-source monitor (local build; OFF unless PROJECTS_MONITOR === 'on'; cron not added until approved).
// Reads the source list the backend publishes (url, sha256 of visible text, validators, affected project ids),
// sends conditional requests, and records only CHANGES in the existing PRICES KV under 'projmon:*'.
// It never edits project data: changes go to a review queue a person checks; accepted changes run through
// the normal Python batch + audit + owner approval.
export const PROJECTS_CRON = '17 3 * * 0'; // proposal: Sundays 03:17 UTC
const MAX = 400; // stays under Workers Paid subrequest limits per invocation

export function visibleText(html) {
  return html.replace(/<(script|style|noscript)[^>]*>[\s\S]*?<\/\1>/gi, ' ').replace(/<[^>]+>/g, ' ')
    .replace(/\b\d{1,2}:\d{2}(:\d{2})?\b|\b(csrf|token|nonce|session)\S*/gi, ' ').replace(/\s+/g, ' ').trim();
}
async function sha(buf) { return [...new Uint8Array(await crypto.subtle.digest('SHA-256', buf))].map(b => b.toString(16).padStart(2, '0')).join(''); }

export async function runProjectsMonitor(env, { fetchImpl = fetch, now = new Date() } = {}) {
  const srcUrl = env.PROJECTS_SOURCES_URL || 'https://investedia.com/assets/globe/projects-monitor-sources.json';
  const list = await (await fetchImpl(srcUrl)).json();
  const state = JSON.parse((await env.PRICES.get('projmon:state')) || '{}');
  const queue = JSON.parse((await env.PRICES.get('projmon:queue')) || '[]');
  const out = { checked: 0, unchanged: 0, changed: 0, errors: 0, queued: 0 };
  for (const s of (list.sources || []).slice(0, MAX)) {
    const prev = state[s.url] || { sha256: s.sha256 };
    const h = { 'User-Agent': 'Investedia project monitor (+https://investedia.com)' };
    if (prev.etag) h['If-None-Match'] = prev.etag;
    if (prev.last_modified) h['If-Modified-Since'] = prev.last_modified;
    out.checked++;
    let r;
    try { r = await fetchImpl(s.url, { headers: h, cf: { cacheTtl: 0 } }); } catch (e) { out.errors++; state[s.url] = { ...prev, last_error: String(e).slice(0, 100) }; continue; }
    if (r.status === 304) { out.unchanged++; continue; }
    if (!r.ok) { out.errors++; state[s.url] = { ...prev, last_error: 'HTTP ' + r.status }; continue; } // refusals recorded, never retried around
    const isHtml = (r.headers.get('content-type') || '').includes('html');
    const digest = isHtml ? 'text:' + await sha(new TextEncoder().encode(visibleText(await r.text()))) : await sha(await r.arrayBuffer());
    const next = { sha256: digest, etag: r.headers.get('etag'), last_modified: r.headers.get('last-modified'), checked_at: now.toISOString().slice(0, 10), version: (prev.version || 0) };
    if (prev.sha256 && prev.sha256 !== digest && prev.sha256.startsWith('text:') === digest.startsWith('text:')) {
      out.changed++; next.version++;
      queue.push({ type: 'source_changed', url: s.url, affected_projects: s.projects || [], old: prev.sha256, new: digest, at: next.checked_at, status: 'needs_review' });
      out.queued++;
    } else out.unchanged++;
    state[s.url] = next;
  }
  for (const d of list.due || []) if (!queue.some(q => q.type === 'expected_date_passed' && q.project === d.project)) { queue.push({ type: 'expected_date_passed', ...d, status: 'needs_review' }); out.queued++; }
  await env.PRICES.put('projmon:state', JSON.stringify(state)); // 2 KV writes per weekly run
  await env.PRICES.put('projmon:queue', JSON.stringify(queue.slice(-500)));
  return out;
}
