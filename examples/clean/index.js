// A built bundle that carries only the browser key. patet scan passes it.
const s = createClient("https://abcdefghijklmnopqrst.supabase.co", window.SUPABASE_ANON_KEY);
s.from("posts").select("id, title, body");
