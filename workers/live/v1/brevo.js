// Brevo transactional email (API v3). Key in the Worker secret BREVO_API_KEY; sender in vars BREVO_SENDER_EMAIL / BREVO_SENDER_NAME.
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const SITE = 'https://investedia.com';
// One email can carry several items: [{title, line, url, why}]
export function alertEmail(items, unsubUrl) {
  const n = items.length, subject = n === 1 ? items[0].title : `${n} alerts: ${items[0].title}`;
  const rows = items.map(i => `<tr><td style="padding:16px 0;border-top:1px solid #e4e4e7">
    <div style="font-size:12px;color:#ea6a0c;font-weight:600;letter-spacing:.04em;text-transform:uppercase">${esc(i.why)}</div>
    <div style="font-size:17px;font-weight:600;color:#18181b;margin:4px 0">${esc(i.title)}</div>
    ${i.line ? `<div style="font-size:14px;color:#52525b;line-height:1.5">${esc(i.line)}</div>` : ''}
    <a href="${esc(i.url)}" style="display:inline-block;margin-top:10px;color:#ea6a0c;font-weight:600;text-decoration:none">Read the article →</a></td></tr>`).join('');
  const html = `<!doctype html><html><body style="margin:0;background:#f4f4f5;font-family:Inter,-apple-system,Segoe UI,Roboto,Arial,sans-serif">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
  <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#fff;border-radius:14px;padding:24px">
  <tr><td style="font-size:18px;font-weight:700;color:#18181b;padding-bottom:12px">Investedia</td></tr>${rows}
  <tr><td style="padding-top:18px;border-top:1px solid #e4e4e7;font-size:12px;color:#71717a;line-height:1.6">You get this because you turned on alerts at investedia.com.
  <a href="${SITE}/watchlist.html" style="color:#71717a">Manage alerts</a> · <a href="${esc(unsubUrl)}" style="color:#71717a">Unsubscribe</a><br>Not investment advice.</td></tr>
  </table></td></tr></table></body></html>`;
  const text = items.map(i => `${i.why}\n${i.title}\n${i.line || ''}\n${i.url}`).join('\n\n') + `\n\nManage alerts: ${SITE}/watchlist.html\nUnsubscribe: ${unsubUrl}\nNot investment advice.`;
  return { subject: subject.slice(0, 150), html, text };
}
export async function sendEmail(env, to, mail, unsubUrl, fetchImpl = fetch) {
  const r = await fetchImpl('https://api.brevo.com/v3/smtp/email', { method: 'POST', headers: { 'api-key': env.BREVO_API_KEY, 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ sender: { email: env.BREVO_SENDER_EMAIL, name: env.BREVO_SENDER_NAME || 'Investedia' }, to: [{ email: to }], subject: mail.subject, htmlContent: mail.html, textContent: mail.text,
      headers: { 'List-Unsubscribe': `<${unsubUrl}>`, 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click' }, tags: ['alert'] }) });
  return r.status;
}
