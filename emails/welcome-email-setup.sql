-- Investedia welcome email: sent by Resend when someone confirms their email (or signs up with Google).
-- 1) Replace PASTE_YOUR_RESEND_API_KEY below with your Resend API key (only here, in Supabase; never in the website code).
-- 2) Run this whole file once in Supabase -> SQL Editor.
create extension if not exists pg_net;
delete from vault.secrets where name = 'resend_api_key';
select vault.create_secret('PASTE_YOUR_RESEND_API_KEY', 'resend_api_key', 'Resend key for the welcome email');

create or replace function public.send_welcome_email() returns trigger
language plpgsql security definer set search_path = public, extensions as $fn$
declare
  k text;
  nm text := split_part(coalesce(new.raw_user_meta_data->>'name', new.raw_user_meta_data->>'full_name', ''), ' ', 1);
  msg text := $html$<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark"><title>Welcome to Investedia</title>
<style>:root{color-scheme:light dark;supported-color-schemes:light dark}
.wm-d{display:none;max-height:0;overflow:hidden}
@media (prefers-color-scheme:dark){ .wm-l{display:none!important;max-height:0!important} .wm-d{display:inline-block!important;max-height:none!important}
 .bg{background:#0A0A0B!important} .h1{color:#FFFFFF!important} .h2{color:#71717A!important} .p{color:#A1A1AA!important} .p2,.ft{color:#71717A!important} .ft a{color:#A1A1AA!important} .rule{border-color:#29292D!important} .track{background:#29292D!important} .ring{border-color:#52525B!important} }</style></head>
<body class="bg" style="margin:0;padding:0;background:#FFFFFF;-webkit-text-size-adjust:100%">
<div style="display:none;max-height:0;overflow:hidden">Your free Investedia account is ready. Here's where to start.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="bg" style="background:#FFFFFF"><tr><td align="center" style="padding:32px 16px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Helvetica,Arial,sans-serif">
<tr><td style="padding:0 8px 28px"><img class="wm-l" src="https://investedia.com/assets/email/wordmark-black.png" width="128" height="36" alt="Investedia" style="display:inline-block"><img class="wm-d" src="https://investedia.com/assets/email/wordmark-white.png" width="128" height="36" alt="Investedia"></td></tr>
<tr><td style="padding:0 8px">
<h1 class="h1" style="margin:0 0 14px;font-size:40px;line-height:1.05;letter-spacing:-.04em;color:#111111">Every market.<br><span class="h2" style="color:#9AA0A6">One clear place.</span></h1>
<p class="p" style="margin:0 0 30px;font-size:15px;line-height:1.6;color:#5F6368">Welcome, {{FIRST_NAME}}. Your email is confirmed and your free account is ready.</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td width="33%" valign="top" class="rule" style="padding:18px 0 0;border-top:1px solid #E5E5E2"><p class="h1" style="margin:0;font-size:28px;font-weight:600;letter-spacing:-.03em;color:#111111">800+</p><p class="p2" style="margin:2px 0 0;font-size:13px;color:#80868B">assets</p></td><td width="33%" valign="top" class="rule" style="padding:18px 0 0;border-top:1px solid #E5E5E2"><p class="h1" style="margin:0;font-size:28px;font-weight:600;letter-spacing:-.03em;color:#111111">136</p><p class="p2" style="margin:2px 0 0;font-size:13px;color:#80868B">countries</p></td><td width="33%" valign="top" class="rule" style="padding:18px 0 0;border-top:1px solid #E5E5E2"><p class="h1" style="margin:0;font-size:28px;font-weight:600;letter-spacing:-.03em;color:#111111">$0</p><p class="p2" style="margin:2px 0 0;font-size:13px;color:#80868B">forever</p></td></tr></table>
<div style="height:30px"></div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td class="p2" style="font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#80868B">Your setup</td><td align="right" class="p2" style="font-size:12px;color:#80868B">1 of 4 done</td></tr></table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:10px 0 6px"><tr><td class="track" style="background:#EDEDEA;border-radius:4px;height:4px;line-height:4px;font-size:0"><div style="width:25%;height:4px;background:#FF7A1A;border-radius:4px"></div></td></tr></table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td class="rule" style="padding:16px 0;border-top:1px solid #E5E5E2"><table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr><td width="40" valign="top" style="padding-top:1px"><div style="width:22px;height:22px;border-radius:50%;background:#FF7A1A;color:#0A0A0B;font-size:12px;font-weight:700;line-height:22px;text-align:center">&#10003;&#xFE0E;</div></td><td><p class="p2" style="margin:0 0 3px;font-size:15px;font-weight:600;color:#80868B;text-decoration:line-through">Confirm your email</p><p class="p2" style="margin:0;font-size:14px;color:#80868B">Done. Your account is safe.</p></td></tr></table></td></tr><tr><td class="rule" style="padding:16px 0;border-top:1px solid #E5E5E2"><a href="https://investedia.com/markets.html?setup=star" style="display:block;text-decoration:none"><table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr><td width="40" valign="top" style="padding-top:1px"><div class="ring" style="width:22px;height:22px;border-radius:50%;border:1.5px solid #BDBDB8;box-sizing:border-box"></div></td><td><p class="h1" style="margin:0 0 3px;font-size:15px;font-weight:600;color:#111111">Star 3 assets</p><p class="p" style="margin:0;font-size:14px;line-height:1.5;color:#5F6368">Your dashboard builds itself around them.</p></td><td width="40" align="right" valign="middle" style="font-size:18px;color:#FF7A1A">&rarr;</td></tr></table></a></td></tr><tr><td class="rule" style="padding:16px 0;border-top:1px solid #E5E5E2"><a href="https://investedia.com/watchlist.html?setup=alert" style="display:block;text-decoration:none"><table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr><td width="40" valign="top" style="padding-top:1px"><div class="ring" style="width:22px;height:22px;border-radius:50%;border:1.5px solid #BDBDB8;box-sizing:border-box"></div></td><td><p class="h1" style="margin:0 0 3px;font-size:15px;font-weight:600;color:#111111">Set a price alert</p><p class="p" style="margin:0;font-size:14px;line-height:1.5;color:#5F6368">Know the moment something moves.</p></td><td width="40" align="right" valign="middle" style="font-size:18px;color:#FF7A1A">&rarr;</td></tr></table></a></td></tr><tr><td class="rule" style="padding:16px 0;border-top:1px solid #E5E5E2"><a href="https://investedia.com/about.html?setup=app#app" style="display:block;text-decoration:none"><table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr><td width="40" valign="top" style="padding-top:1px"><div class="ring" style="width:22px;height:22px;border-radius:50%;border:1.5px solid #BDBDB8;box-sizing:border-box"></div></td><td><p class="h1" style="margin:0 0 3px;font-size:15px;font-weight:600;color:#111111">Add to home screen</p><p class="p" style="margin:0;font-size:14px;line-height:1.5;color:#5F6368">Investedia like an app, one tap away.</p></td><td width="40" align="right" valign="middle" style="font-size:18px;color:#FF7A1A">&rarr;</td></tr></table></a></td></tr></table>
<div style="height:30px"></div>
<table role="presentation" cellpadding="0" cellspacing="0"><tr><td style="border-radius:10px;background:#FF7A1A"><a href="https://investedia.com/dashboard.html" style="display:inline-block;background:#FF7A1A;border-radius:10px;padding:14px 26px;font-weight:600;font-size:15px;color:#120800;text-decoration:none">Open Investedia</a></td></tr></table>
<div style="height:40px"></div></td></tr>
<tr><td class="ft rule" style="padding:24px 8px 0;border-top:1px solid #E5E5E2;font-size:12px;line-height:1.6;color:#80868B">
<p style="margin:0 0 6px">You're receiving this because you created an Investedia account. <a href="{{UNSUBSCRIBE_URL}}" style="color:#5F6368">Unsubscribe</a></p>
<p style="margin:0 0 6px">Information and education only. Not investment advice.</p>
<p style="margin:0">Investedia · <a href="mailto:info@investedia.com" style="color:#5F6368">info@investedia.com</a></p></td></tr>
</table></td></tr></table></body></html>$html$;
begin
  if (tg_op = 'INSERT' and new.email_confirmed_at is not null)
     or (tg_op = 'UPDATE' and old.email_confirmed_at is null and new.email_confirmed_at is not null) then
    nm := replace(replace(replace(nm, '&', '&amp;'), '<', '&lt;'), '>', '&gt;');
    select decrypted_secret into k from vault.decrypted_secrets where name = 'resend_api_key' limit 1;
    if k is null then return new; end if;
    msg := replace(msg, 'Welcome, {{FIRST_NAME}}.', case when nm <> '' then 'Welcome, ' || nm || '.' else 'Welcome!' end);
    msg := replace(msg, '{{UNSUBSCRIBE_URL}}', 'https://investedia.com/profile.html#notifications');
    perform net.http_post(
      url := 'https://api.resend.com/emails',
      headers := jsonb_build_object('Authorization', 'Bearer ' || k, 'Content-Type', 'application/json'),
      body := jsonb_build_object('from', 'Investedia <info@investedia.com>', 'to', jsonb_build_array(new.email),
                                 'subject', 'Welcome to Investedia', 'html', msg));
  end if;
  return new;
exception when others then
  return new;  -- never block a sign-up because of the welcome email
end $fn$;

drop trigger if exists on_email_confirmed on auth.users;
create trigger on_email_confirmed after insert or update of email_confirmed_at on auth.users
  for each row execute function public.send_welcome_email();
