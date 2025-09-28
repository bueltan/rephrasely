support_html = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Rephrasely • Support</title>
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <style>
      :root {
        --bg:#f6f7fb; --card:#ffffff; --text:#1f2937; --muted:#6b7280;
        --link:#2563eb; --border:#e5e7eb; --shadow:0 10px 25px rgba(0,0,0,.06);
      }
      * { box-sizing: border-box; }
      body {
        margin:0; font-family: system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
        background:var(--bg); color:var(--text);
        display:flex; align-items:center; justify-content:center; min-height:100vh; padding:24px;
      }
      main {
        width:100%; max-width:820px; background:var(--card); border:1px solid var(--border);
        border-radius:16px; padding:28px; box-shadow: var(--shadow);
      }
      .head { display:flex; gap:16px; align-items:center; margin-bottom:12px; }
      .logo { width:64px; height:64px; border-radius:50%; box-shadow:0 2px 6px rgba(0,0,0,.12); }
      h1 { font-size:1.6rem; margin:0; }
      .muted { color:var(--muted); margin-top:2px; }
      p { line-height:1.6; }
      .card {
        background:#fff; border:1px solid var(--border); border-radius:12px; padding:16px 18px;
        margin:16px 0;
      }
      .btn {
        display:inline-block; padding:10px 14px; border-radius:10px; border:1px solid var(--border);
        text-decoration:none; color:var(--text); background:#fff;
      }
      .btn.primary { background:#111827; color:#fff; border-color:#111827; }
      a { color:var(--link); text-decoration:none; }
      a:hover { text-decoration:underline; }
      .row { display:flex; gap:12px; flex-wrap:wrap; align-items:center; }
      .hr { height:1px; background:var(--border); margin:22px 0; }
      footer { margin-top:8px; color:var(--muted); font-size:.95rem; }
    </style>
  </head>
  <body>
    <main>
      <div class="head">
        <img class="logo" alt="Rephrasely" src="https://avatars.slack-edge.com/2025-07-27/9256789801219_5f9092f24cb6e34a01a0_192.png" />
        <div>
          <h1>Support</h1>
          <div class="muted">How can we help you?</div>
        </div>
      </div>

      <div class="card">
        <p>
          Need help with installing or using Rephrasely? Feel free to reach out.
        </p>
        <div class="row">
          <a class="btn primary"
             href="mailto:denisbueltan@gmail.com?subject=Rephrasely%20Support&body=Hello%20Denis%2C%0A%0AI%20need%20help%20with%3A%0A-%20Workspace%20(Team%20ID)%3A%0A-%20Command%20or%20flow%20that%20failed%3A%0A-%20Error%20details%20(if%20any)%3A%0A%0AThank%20you!">
             📧 Contact Support
          </a>
          <a class="btn" href="{{ url_for('home') }}">↩︎ Back to Home</a>
          <a class="btn" href="{{ url_for('privacy') }}">Privacy Policy</a>
          <a class="btn" href="{{ url_for('install') }}">Install to Slack</a>
        </div>
      </div>

      <div class="hr"></div>

      <div class="card">
        <p class="muted"><strong>Quick Tips</strong></p>
        <ul>
          <li>To use: type <code>/re</code> followed by your message in Slack.</li>
          <li>If you want messages to be sent <em>as you</em>, make sure you grant <code>user_scope</code> (e.g. <code>chat:write</code>) during installation.</li>
          <li>Common issues: redirect URI mismatch, missing scopes (<code>commands</code>, <code>chat:write</code>), or invalid token.</li>
        </ul>
      </div>

      <footer>
        Open Source: <a href="https://github.com/bueltan/rephrasely" target="_blank">GitHub Repo</a> ·
        <a href="https://bueltan.github.io/" target="_blank">About me</a>
      </footer>
    </main>
  </body>
</html>
    """