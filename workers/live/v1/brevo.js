// Brevo transactional email (API v3). Key in the Worker secret BREVO_API_KEY; sender in vars BREVO_SENDER_EMAIL / BREVO_SENDER_NAME.
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const SITE = 'https://investedia.com';
// One email can carry several items: [{title, line, url, why}]
export function alertEmail(items, unsubUrl) {
  // Dark by default (12 Nov 2026): Gmail and most apps ignore prefers-color-scheme, so the email is dark everywhere.
  const n = items.length, subject = n === 1 ? items[0].title : `${n} alerts: ${items[0].title}`;
  const rows = items.map(i => `<tr><td style="padding:18px 0;border-top:1px solid #26262b">
    <div style="font-size:12px;color:#ff7a1a;font-weight:600;letter-spacing:.06em;text-transform:uppercase">${esc(i.why)}</div>
    <div style="font-size:18px;line-height:1.35;font-weight:600;color:#f4f4f5;margin:6px 0">${esc(i.title)}</div>
    ${i.line ? `<div style="font-size:14px;color:#a1a1aa;line-height:1.55">${esc(i.line)}</div>` : ''}
    <a href="${esc(i.url)}" style="display:inline-block;margin-top:12px;background:#ff7a1a;color:#111111;font-weight:600;font-size:14px;text-decoration:none;padding:9px 14px;border-radius:9px">Read the article →</a></td></tr>`).join('');
  const html = `<!doctype html><html><head><meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark"><meta name="viewport" content="width=device-width"></head>
  <body style="margin:0;background:#050506;font-family:Inter,-apple-system,Segoe UI,Roboto,Arial,sans-serif" bgcolor="#050506">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#050506" style="background:#050506"><tr><td align="center" style="padding:28px 12px">
  <table role="presentation" width="560" cellpadding="0" cellspacing="0" bgcolor="#0f0f12" style="max-width:560px;width:100%;background:#0f0f12;border:1px solid #26262b;border-radius:16px;padding:26px">
  <tr><td style="padding-bottom:14px"><span style="font-size:20px;font-weight:700;color:#f4f4f5">Invested<span style="color:#ff7a1a">i</span>a</span><span style="float:right;font-size:12px;color:#71717a;padding-top:5px">Alert</span></td></tr>${rows}
  <tr><td style="padding-top:20px;border-top:1px solid #26262b;font-size:12px;color:#71717a;line-height:1.7">You get this because you turned on alerts at investedia.com.<br>
  <a href="${SITE}/watchlist.html" style="color:#a1a1aa">Manage alerts</a> · <a href="${esc(unsubUrl)}" style="color:#a1a1aa">Unsubscribe</a><br>Not investment advice.</td></tr>
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
