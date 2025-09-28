from flask import render_template_string

def render_page(title: str, body_html: str, status: int = 200) -> tuple[str, int]:
    return render_template_string(f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{{{{ title }}}}</title>
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <style>
      :root {{
        --bg:#f6f7fb; --card:#ffffff; --text:#1f2937; --muted:#6b7280;
        --ok:#10b981; --warn:#f59e0b; --err:#ef4444; --link:#2563eb;
        --border:#e5e7eb;
      }}
      /* ...existing CSS... */
      .footer {{
        margin-top: 28px;
        text-align: center;
        font-size: 0.9rem;
        color: var(--muted);
      }}
      .footer a {{
        color: var(--link);
        text-decoration: none;
      }}
      .footer a:hover {{
        text-decoration: underline;
      }}
    </style>
  </head>
  <body>
    <main class="card">
      <div class="head">
        <img class="logo" alt="Rephrasely" src="https://avatars.slack-edge.com/2025-07-27/9256789801219_5f9092f24cb6e34a01a0_192.png" />
        <div>
          <h1>{{{{ title }}}}</h1>
          <div class="muted">Rephrasely • Your AI Slack Assistant</div>
        </div>
      </div>
      {{{{ body_html|safe }}}}
      <footer class="footer">
        <p>
          <a href="https://github.com/bueltan/rephrasely" target="_blank">Rephrasely on GitHub</a> · 
          <a href="https://bueltan.github.io/" target="_blank">About me</a>
        </p>
      </footer>
    </main>
  </body>
</html>
    """, title=title), status
