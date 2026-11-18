# Live test

This runs patet against real Postgres and PostgREST, the engine behind Supabase's data API. CI does it on every push.

To run it yourself you need Postgres and PostgREST on your machine, or Docker:

```bash
docker run -d --name pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:17
PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres -d postgres -f live/setup.sql
docker run -d --name pgrst --network host \
  -e PGRST_DB_URI=postgres://authenticator:authenticator@127.0.0.1:5432/postgres \
  -e PGRST_DB_SCHEMAS=public -e PGRST_DB_ANON_ROLE=anon \
  -e PGRST_JWT_SECRET=patet-live-test-secret-at-least-32-chars \
  postgrest/postgrest:v16.5
python live/run.py
```

`setup.sql` plants seven tables in known states. `run.py` puts a small stand-in for Supabase's gateway in front of PostgREST, serves a tiny website that names the tables, runs patet three ways and checks every answer. It prints one line per check and exits 1 if any fails.

Supabase's sign-up and storage services are not part of this test.
