# How patet works

patet does what a curious stranger could do with your website, and stops short of reading your data.

## 1. Read the page

It downloads your page and every script on the same site, the same files a browser gets. It follows code that loads later, which apps built with Vite split into several files.

## 2. Find the project, the key and the tables

In that code it looks for:

- the project address, such as `https://abcd....supabase.co`;
- the key the browser uses to talk to Supabase. A browser key is expected. A server key is a critical mistake;
- every `.from("table")` call, which names a table the app reads or writes;
- storage buckets and database functions the app uses.

Supabase stopped giving the list of tables to browser keys in April 2026, so the code is the starting point. `--tables` and `--guess` add names the code does not show.

## 3. Ask how many rows a stranger would get

Nothing goes to Supabase unless you pass `--i-own-this`. With it, patet asks each table for a row count with the browser key, just as a stranger could. Supabase answers with a number and no rows.

- A number above zero means the table is **open**.
- Zero means **no rows** are visible. Either row rules hide them or the table is empty.
- A refusal means the table is **closed** to strangers.
- Not found means the table does not exist, or is not offered through the API.

## 4. Grade what is open

An open table is graded by the personal data its column names suggest. The names come from the app's code, or from one row when you pass `--columns`. patet keeps the names and drops the values at once.

## 5. Check the doors around the tables

It asks storage whether a stranger can list files in each bucket, one file at most. It reads the public sign-up settings, because "signed-in users only" means everyone when anyone can sign up without confirming an email.

## 6. Report

Each finding says what a stranger could do and how to stop it. `--fix` adds SQL to close each open table, for you to read before you run it.
