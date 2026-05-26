"""Login page HTML. Single string constant; the bot serves it from
GET /login. Same dark-theme palette as dashboard_html.py so the visual
shift between login and dashboard is seamless.

Vanilla HTML form -- no JS, no fetch. POSTs username + password to
/login, the server sets a session cookie and 303s to /dashboard/1.
"""

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FortyTwo Network: Sign in</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><g transform='rotate(-20 32 32)'><circle cx='32' cy='32' r='28' fill='none' stroke='%2360a5fa' stroke-width='2.5'/><circle cx='52' cy='32' r='3' fill='%234ade80'/></g><circle cx='32' cy='32' r='22' fill='%23141414'/><text x='32' y='42' text-anchor='middle' font-family='ui-monospace,monospace' font-weight='700' font-size='26' fill='%23e8e8e8'>42</text></svg>">
<style>
:root { --bg:#0a0a0a; --card:#141414; --text:#e8e8e8; --muted:#888; --red:#f87171; --blue:#60a5fa; --border:#2a2a2a; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.5;
  display: flex; align-items: center; justify-content: center; padding: 16px;
}
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 10px;
  padding: 28px 24px; width: 100%; max-width: 360px;
}
.card h1 { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.card .sub { color: var(--muted); font-size: 12px; margin-bottom: 20px; }
.field { display: block; margin-bottom: 14px; }
.field label {
  display: block; font-size: 11px; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
}
.field input {
  width: 100%; padding: 9px 12px; background: var(--bg); color: var(--text);
  border: 1px solid var(--border); border-radius: 6px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 13px;
}
.field input:focus { outline: none; border-color: var(--blue); }
.submit {
  width: 100%; padding: 10px 14px; margin-top: 6px;
  background: var(--blue); color: #000; border: none; border-radius: 6px;
  font-weight: 600; font-size: 13px; cursor: pointer;
}
.submit:hover { filter: brightness(1.05); }
.error {
  background: rgba(248,113,113,0.12); color: var(--red);
  border: 1px solid rgba(248,113,113,0.3); border-radius: 6px;
  padding: 8px 10px; font-size: 12px; margin-bottom: 14px;
}
.error.hidden { display: none; }
footer { color: var(--muted); font-size: 11px; text-align: center; margin-top: 18px; }
</style>
</head>
<body>
<div class="card">
  <h1>FortyTwo Network</h1>
  <div class="sub">Sign in to view node dashboards.</div>
  <div id="error-banner" class="error hidden">Wrong username or password.</div>
  <form method="post" action="/login" autocomplete="on">
    <label class="field">
      <label>Username</label>
      <input name="username" type="text" autocomplete="username" autofocus required>
    </label>
    <label class="field">
      <label>Password</label>
      <input name="password" type="password" autocomplete="current-password" required>
    </label>
    <button class="submit" type="submit">Sign in</button>
  </form>
  <footer>FortyTwo Network Node Analysis</footer>
</div>
<script>
  // Show error banner when redirected back here with ?error=1.
  // Done in JS so the static HTML stays the same regardless of query.
  if (new URLSearchParams(location.search).get('error') === '1') {
    document.getElementById('error-banner').classList.remove('hidden');
  }
</script>
</body>
</html>
"""
