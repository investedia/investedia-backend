-- Push alerts (12 Nov 2026). Run once in Supabase: Dashboard > SQL editor > paste > Run.
-- push_subscriptions: one row per browser/device that turned alerts on. Members manage only their own rows.
create table if not exists public.push_subscriptions (
  endpoint text primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  p256dh text not null,
  auth text not null,
  user_agent text,
  created_at timestamptz not null default now()
);
alter table public.push_subscriptions enable row level security;
create policy "own push subscriptions: read" on public.push_subscriptions for select using (auth.uid() = user_id);
create policy "own push subscriptions: add" on public.push_subscriptions for insert with check (auth.uid() = user_id);
create policy "own push subscriptions: remove" on public.push_subscriptions for delete using (auth.uid() = user_id);

-- alert_log: how many alerts a member got this week (free: 3 per week, resets Monday 00:00 UTC) and which articles were sent.
-- Written only by the news service (service key); members can read their own row to see "2 of 3 this week".
create table if not exists public.alert_log (
  user_id uuid not null references auth.users(id) on delete cascade,
  week text not null,               -- ISO week, e.g. 2026-W46
  sent int not null default 0,
  article_ids text[] not null default '{}',
  updated_at timestamptz not null default now(),
  primary key (user_id, week)
);
alter table public.alert_log enable row level security;
create policy "own alert log: read" on public.alert_log for select using (auth.uid() = user_id);
