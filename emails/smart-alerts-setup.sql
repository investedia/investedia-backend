-- Investedia Smart alerts (free: 5 follows · Pro: unlimited). Run this whole file once in Supabase -> SQL Editor.
-- Before running:
--   1) Replace PASTE_A_LONG_RANDOM_TOKEN below with a long random text (40+ characters). Put the SAME text in GitHub
--      (investedia-backend -> Settings -> Secrets and variables -> Actions -> New secret) named ALERTS_INGEST_TOKEN.
--   2) Leave sending off (the last lines). Turn it on later with:  update public.alert_config set sending = true;
-- Uses the Resend key already stored for the welcome email (vault secret 'resend_api_key'). No new keys in website code.

create extension if not exists pg_net;
delete from vault.secrets where name = 'alerts_ingest_token';
select vault.create_secret('PASTE_A_LONG_RANDOM_TOKEN', 'alerts_ingest_token', 'News robot -> Smart alerts');

-- What a user follows: a country (ISO2), an asset (site symbol, e.g. NVDA) or a topic (article category).
create table if not exists public.alert_follows (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  kind text not null check (kind in ('country','asset','topic')),
  ref text not null check (length(ref) between 1 and 40),
  label text not null check (length(label) between 1 and 80),
  created_at timestamptz not null default now(),
  unique (user_id, kind, ref)
);
-- Pro members (empty until Pro launches; only the owner/service adds rows).
create table if not exists public.pro_members (user_id uuid primary key references auth.users(id) on delete cascade, since timestamptz not null default now());
-- One row per user per article.
create table if not exists public.alert_events (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  article_id text not null,
  kind text not null, ref text not null, label text not null,
  headline text not null, source text, url text, published_at timestamptz,
  created_at timestamptz not null default now(), seen_at timestamptz, emailed_at timestamptz,
  unique (user_id, article_id)
);
create index if not exists alert_events_user_created on public.alert_events (user_id, created_at desc);
create table if not exists public.alert_settings (
  user_id uuid primary key default auth.uid() references auth.users(id) on delete cascade,
  instant_email boolean not null default true, digest boolean not null default true,
  updated_at timestamptz not null default now()
);
create table if not exists public.alert_config (id int primary key default 1 check (id = 1), sending boolean not null default false, free_limit int not null default 5, max_instant_per_day int not null default 10);
insert into public.alert_config (id) values (1) on conflict (id) do nothing;

-- Free limit, enforced in the database (the website shows the "Follow more with Pro" card before this triggers).
create or replace function public.alert_follow_limit() returns trigger language plpgsql security definer set search_path = public as $$
declare n int; lim int;
begin
  if exists (select 1 from public.pro_members where user_id = new.user_id) then return new; end if;
  select free_limit into lim from public.alert_config where id = 1;
  select count(*) into n from public.alert_follows where user_id = new.user_id;
  if n >= coalesce(lim, 5) then raise exception 'free_follow_limit' using errcode = 'P0001'; end if;
  return new;
end $$;
drop trigger if exists alert_follow_limit on public.alert_follows;
create trigger alert_follow_limit before insert on public.alert_follows for each row execute function public.alert_follow_limit();

-- Row-level security: everyone sees and changes only their own rows.
alter table public.alert_follows enable row level security;
alter table public.alert_events enable row level security;
alter table public.alert_settings enable row level security;
alter table public.pro_members enable row level security;
alter table public.alert_config enable row level security;
drop policy if exists "own follows" on public.alert_follows;
create policy "own follows" on public.alert_follows for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own events read" on public.alert_events;
create policy "own events read" on public.alert_events for select to authenticated using (user_id = auth.uid());
drop policy if exists "own events seen" on public.alert_events;
create policy "own events seen" on public.alert_events for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own settings" on public.alert_settings;
create policy "own settings" on public.alert_settings for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own pro row" on public.pro_members;
create policy "own pro row" on public.pro_members for select to authenticated using (user_id = auth.uid());
drop policy if exists "read config" on public.alert_config;
create policy "read config" on public.alert_config for select to authenticated using (true);
revoke update (user_id, article_id, kind, ref, label, headline, source, url, published_at, created_at, emailed_at) on public.alert_events from authenticated;

-- The news robot calls this after each run with the new articles. The token protects it; no service key is needed.
-- articles: [{id, headline, source, url, published_at, country (ISO2), assets: [symbols], topic, importance}]
create or replace function public.ingest_alert_articles(token text, articles jsonb, dry_run boolean default true)
returns jsonb language plpgsql security definer set search_path = public, extensions as $$
declare
  ok text; cfg record; a jsonb; inserted int := 0; matched int := 0; mailed int := 0; f record; e_id bigint; k text; today int;
begin
  select decrypted_secret into ok from vault.decrypted_secrets where name = 'alerts_ingest_token' limit 1;
  if ok is null or token is distinct from ok then raise exception 'bad_token' using errcode = '28000'; end if;
  select * into cfg from public.alert_config where id = 1;
  for a in select * from jsonb_array_elements(coalesce(articles, '[]'::jsonb)) loop
    for f in
      select af.user_id, af.kind, af.ref, af.label from public.alert_follows af
      where (af.kind = 'country' and af.ref = upper(coalesce(a->>'country', '')))
         or (af.kind = 'topic' and af.ref = lower(coalesce(a->>'topic', '')))
         or (af.kind = 'asset' and a->'assets' ? upper(af.ref))
    loop
      matched := matched + 1;
      if dry_run then continue; end if;
      insert into public.alert_events (user_id, article_id, kind, ref, label, headline, source, url, published_at)
      values (f.user_id, a->>'id', f.kind, f.ref, f.label, left(a->>'headline', 300), left(a->>'source', 120), left(a->>'url', 600), (a->>'published_at')::timestamptz)
      on conflict (user_id, article_id) do nothing returning id into e_id;
      if e_id is null then continue; end if;
      inserted := inserted + 1;
      if cfg.sending and coalesce((select instant_email from public.alert_settings s where s.user_id = f.user_id), true) then
        select count(*) into today from public.alert_events where user_id = f.user_id and emailed_at > now() - interval '1 day';
        if today < cfg.max_instant_per_day then
          select decrypted_secret into k from vault.decrypted_secrets where name = 'resend_api_key' limit 1;
          if k is not null then
            perform net.http_post(url := 'https://api.resend.com/emails',
              headers := jsonb_build_object('Authorization', 'Bearer ' || k, 'Content-Type', 'application/json'),
              body := jsonb_build_object('from', 'Investedia Alerts <info@investedia.com>',
                'to', jsonb_build_array((select email from auth.users u where u.id = f.user_id)),
                'subject', f.label || ': ' || left(a->>'headline', 120),
                'html', '<p style="font:15px/1.5 -apple-system,Inter,Arial;color:#111">You follow <b>' || replace(replace(f.label, '<', '&lt;'), '>', '&gt;') || '</b>.</p><p style="font:600 17px/1.4 -apple-system,Inter,Arial;color:#111">' || replace(replace(left(a->>'headline', 300), '<', '&lt;'), '>', '&gt;') || '</p><p style="font:13px/1.5 Arial;color:#666">' || replace(replace(coalesce(a->>'source', ''), '<', '&lt;'), '>', '&gt;') || ' · <a href="https://investedia.com/story.html?id=' || (a->>'id') || '">Read on Investedia</a></p><p style="font:12px/1.5 Arial;color:#888">Manage or stop alerts: <a href="https://investedia.com/alerts.html">investedia.com/alerts</a>. Information only, not investment advice.</p>'));
            update public.alert_events set emailed_at = now() where id = e_id; mailed := mailed + 1;
          end if;
        end if;
      end if;
    end loop;
  end loop;
  return jsonb_build_object('articles', jsonb_array_length(coalesce(articles, '[]'::jsonb)), 'matched', matched, 'inserted', inserted, 'emailed', mailed, 'dry_run', dry_run, 'sending', cfg.sending);
end $$;
revoke all on function public.ingest_alert_articles(text, jsonb, boolean) from public;
grant execute on function public.ingest_alert_articles(text, jsonb, boolean) to anon, authenticated;

-- Sending stays OFF until you decide (no emails are sent while false):
update public.alert_config set sending = false where id = 1;
