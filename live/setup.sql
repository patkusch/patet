-- A small copy of how Supabase sets up its data API, with six tables in known states.
-- Used by live/run.py against real Postgres and PostgREST. Every value is fake.

create role anon nologin noinherit;
create role authenticated nologin noinherit;
create role service_role nologin noinherit bypassrls;
create role authenticator noinherit login password 'authenticator';
grant anon, authenticated, service_role to authenticator;
grant usage on schema public to anon, authenticated, service_role;

create schema auth;
grant usage on schema auth to anon, authenticated;
create function auth.uid() returns uuid language sql stable as $$
  select nullif(current_setting('request.jwt.claims', true)::json ->> 'sub', '')::uuid
$$;

-- 1. No row rules at all: the Lovable case. Expect: open, 57 rows, critical (passport numbers).
create table public.profiles (
  id serial primary key, user_id uuid default gen_random_uuid(),
  full_name text, email text, passport_number text);
insert into public.profiles (full_name, email, passport_number)
  select 'Person ' || n, 'person' || n || '@example.com', 'X' || lpad(n::text, 7, '0') from generate_series(1, 57) n;
grant select on public.profiles to anon, authenticated;

-- 2. Row rules on, no policy: Supabase's safe default. Expect: no rows.
create table public.notes (id serial primary key, user_id uuid, body text);
insert into public.notes (body) select 'note ' || n from generate_series(1, 12) n;
alter table public.notes enable row level security;
grant select on public.notes to anon, authenticated;

-- 3. Not granted to anon at all. Expect: closed.
create table public.payroll (id serial primary key, amount numeric);
insert into public.payroll (amount) values (1000), (2000);
grant select on public.payroll to authenticated;

-- 4. Row rules on, a policy that lets everyone read: public by design. Expect: open, 5 rows, medium.
create table public.posts (id serial primary key, title text, published boolean default true);
insert into public.posts (title) select 'post ' || n from generate_series(1, 5) n;
alter table public.posts enable row level security;
create policy "posts are public" on public.posts for select to anon, authenticated using (true);
grant select on public.posts to anon, authenticated;

-- 5. Row rules on, owners only. Expect: no rows for a visitor.
create table public.messages (id serial primary key, user_id uuid, message text);
insert into public.messages (user_id, message) select gen_random_uuid(), 'hi ' || n from generate_series(1, 9) n;
alter table public.messages enable row level security;
create policy "owners read" on public.messages for select to authenticated using ((select auth.uid()) = user_id);
grant select on public.messages to anon, authenticated;

-- 6. Granted, no rules, but empty. Expect: no rows (indistinguishable from 2 and 5, by design).
create table public.waitlist (id serial primary key, email text);
grant select on public.waitlist to anon;

-- "orders" is named by the site's code but does not exist. Expect: missing.
