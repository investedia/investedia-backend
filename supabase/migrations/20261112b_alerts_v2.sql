-- Alerts v2 (12 Nov 2026): article alerts (unlimited, email) + smart alerts (Free: 3 per 7-day period from first use; Pro: unlimited).
-- Run once in Supabase: Dashboard > SQL editor > paste > Run (after 20261112_push_alerts.sql).

-- Member plan. Members can read their own; only the owner (service key / dashboard) changes it. Default free.
create table if not exists public.member_plans (
  user_id uuid primary key references auth.users(id) on delete cascade,
  plan text not null default 'free' check (plan in ('free','pro')),
  updated_at timestamptz not null default now()
);
alter table public.member_plans enable row level security;
create policy "own plan: read" on public.member_plans for select using (auth.uid() = user_id);
create or replace function public.member_plan(uid uuid) returns text language sql stable security definer set search_path = public as
$$ select coalesce((select plan from public.member_plans where user_id = uid), 'free') $$;

-- Where and whether to email a member. The address must be the signed-in account's own address.
create table if not exists public.alert_contacts (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  alerts_on boolean not null default true,      -- article alerts for followed items
  muted text[] not null default '{}',           -- followed items with article alerts turned off, e.g. 'c:Brazil', 'a:NVDA'
  unsubscribe_token uuid not null default gen_random_uuid(),
  unsubscribed_at timestamptz,
  updated_at timestamptz not null default now()
);
alter table public.alert_contacts enable row level security;
create policy "own contact: read" on public.alert_contacts for select using (auth.uid() = user_id);
create policy "own contact: add" on public.alert_contacts for insert with check (auth.uid() = user_id and lower(email) = lower(auth.jwt() ->> 'email'));
create policy "own contact: change" on public.alert_contacts for update using (auth.uid() = user_id) with check (auth.uid() = user_id and lower(email) = lower(auth.jwt() ->> 'email'));
create policy "own contact: remove" on public.alert_contacts for delete using (auth.uid() = user_id);

-- Smart alerts. Free members can only use email; the quota is enforced in the database, not the browser.
create table if not exists public.smart_alerts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  type text not null check (type in ('price','market_moving','sector','country_price','release','combined')),
  params jsonb not null default '{}',
  channels text[] not null default '{email}',
  active boolean not null default true,
  created_at timestamptz not null default now()
);
alter table public.smart_alerts enable row level security;
create policy "own smart alerts: read" on public.smart_alerts for select using (auth.uid() = user_id);
create policy "own smart alerts: add" on public.smart_alerts for insert with check (auth.uid() = user_id);
create policy "own smart alerts: change" on public.smart_alerts for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own smart alerts: remove" on public.smart_alerts for delete using (auth.uid() = user_id);

-- Free quota: 3 smart alerts per 7-day period; the first period starts when the member creates their first smart alert.
create table if not exists public.smart_alert_quota (
  user_id uuid primary key references auth.users(id) on delete cascade,
  period_start timestamptz not null,
  used int not null default 0
);
alter table public.smart_alert_quota enable row level security;
create policy "own quota: read" on public.smart_alert_quota for select using (auth.uid() = user_id);

create or replace function public.smart_alert_guard() returns trigger language plpgsql security definer set search_path = public as $$
declare q public.smart_alert_quota; pro boolean := public.member_plan(new.user_id) = 'pro'; periods int;
begin
  if not pro then
    new.channels := '{email}';                                   -- Free: email only
    select * into q from public.smart_alert_quota where user_id = new.user_id for update;
    if not found then
      insert into public.smart_alert_quota(user_id, period_start, used) values (new.user_id, now(), 1);
    else
      if now() >= q.period_start + interval '7 days' then
        periods := floor(extract(epoch from (now() - q.period_start)) / 604800);
        q.period_start := q.period_start + make_interval(days => 7 * periods); q.used := 0;
      end if;
      if q.used >= 3 then raise exception 'smart_alert_quota_reached' using hint = 'Free members can create 3 smart alerts per 7 days'; end if;
      update public.smart_alert_quota set period_start = q.period_start, used = q.used + 1 where user_id = new.user_id;
    end if;
  end if;
  return new;
end $$;
drop trigger if exists smart_alert_guard on public.smart_alerts;
create trigger smart_alert_guard before insert on public.smart_alerts for each row execute function public.smart_alert_guard();
create or replace function public.smart_alert_channels_guard() returns trigger language plpgsql security definer set search_path = public as $$
begin if public.member_plan(new.user_id) <> 'pro' then new.channels := '{email}'; end if; return new; end $$;
drop trigger if exists smart_alert_channels_guard on public.smart_alerts;
create trigger smart_alert_channels_guard before update on public.smart_alerts for each row execute function public.smart_alert_channels_guard();

-- What was sent, so nothing is sent twice. Written only by the news service.
create table if not exists public.alert_sends (
  user_id uuid not null references auth.users(id) on delete cascade,
  alert_key text not null,       -- 'follow' or the smart alert id
  item_id text not null,         -- article id, or e.g. 'NVDA:2026-11-12' for a price move
  channel text not null,
  sent_at timestamptz not null default now(),
  primary key (user_id, alert_key, item_id, channel)
);
alter table public.alert_sends enable row level security;
create policy "own sends: read" on public.alert_sends for select using (auth.uid() = user_id);
create index if not exists alert_sends_day on public.alert_sends (sent_at);
