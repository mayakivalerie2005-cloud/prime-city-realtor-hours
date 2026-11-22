-- Run this in Supabase SQL Editor. Disable public sign-ups in Authentication settings.
create extension if not exists pgcrypto;
create table if not exists public.agents (
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(trim(name)) between 1 and 100),
  contact text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);
create table if not exists public.sales (
  id uuid primary key default gen_random_uuid(),
  agent_id uuid not null references public.agents(id) on delete restrict,
  property_ref text not null check (length(trim(property_ref)) between 1 and 120),
  amount numeric(14,2) not null check (amount > 0),
  sold_at date not null,
  status text not null default 'pending' check (status in ('pending','sold')),
  created_at timestamptz not null default now()
);
create index if not exists sales_sold_at_status_idx on public.sales(sold_at,status);
create index if not exists sales_agent_id_idx on public.sales(agent_id);
create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null check (role in ('admin','agent')),
  agent_id uuid unique references public.agents(id) on delete cascade,
  created_at timestamptz not null default now(),
  check ((role='admin' and agent_id is null) or (role='agent' and agent_id is not null))
);
create table if not exists public.payroll_agent_rows (
  id uuid primary key default gen_random_uuid(),
  week_start date not null,
  week_end date not null,
  agent_id uuid not null references public.agents(id) on delete restrict,
  properties_sold integer not null,
  sales_total numeric(14,2) not null,
  commission_rate numeric(5,4) not null default 0.15,
  commission_total numeric(14,2) not null,
  created_at timestamptz not null default now(),
  unique (week_start, agent_id)
);
create table if not exists public.payroll_runs (
  id uuid primary key default gen_random_uuid(),
  week_start date not null unique,
  week_end date not null,
  properties_sold integer not null,
  sales_total numeric(14,2) not null,
  commission_rate numeric(5,4) not null default 0.15,
  commission_total numeric(14,2) not null,
  breakdown jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);
alter table public.profiles enable row level security;
alter table public.agents enable row level security;
alter table public.sales enable row level security;
alter table public.payroll_runs enable row level security;
alter table public.payroll_agent_rows enable row level security;

-- Helper: the signed-in user's role. Security-definer avoids recursive RLS checks.
create or replace function public.current_user_role()
returns text language sql stable security definer set search_path = public
as $$ select role from public.profiles where user_id = auth.uid() $$;
create or replace function public.current_agent_id()
returns uuid language sql stable security definer set search_path = public
as $$ select agent_id from public.profiles where user_id = auth.uid() and role='agent' $$;

create policy "users read own profile" on public.profiles for select to authenticated
using (user_id = auth.uid());
create policy "admins manage profiles" on public.profiles for all to authenticated
using (public.current_user_role()='admin') with check (public.current_user_role()='admin');

create policy "admins manage agents" on public.agents for all to authenticated
using (public.current_user_role()='admin') with check (public.current_user_role()='admin');
create policy "agents read own agent record" on public.agents for select to authenticated
using (id = public.current_agent_id());

create policy "admins manage all sales" on public.sales for all to authenticated
using (public.current_user_role()='admin') with check (public.current_user_role()='admin');
create policy "agents read own sales" on public.sales for select to authenticated
using (agent_id = public.current_agent_id());

create policy "admins read payroll" on public.payroll_runs for select to authenticated
using (public.current_user_role()='admin');
create policy "agents read own payroll rows" on public.payroll_agent_rows for select to authenticated
using (agent_id = public.current_agent_id());
