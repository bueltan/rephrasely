terms_html = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Rephrasely • Terms of Service</title>
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <style>
      :root {
        --bg:#f6f7fb; --card:#ffffff; --text:#1f2937; --muted:#6b7280;
        --link:#2563eb; --border:#e5e7eb; --shadow:0 10px 25px rgba(0,0,0,.06);
      }
      body {
        margin:0; font-family: system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
        background:var(--bg); color:var(--text);
        display:flex; justify-content:center; padding:40px 20px;
      }
      main {
        width:100%; max-width:820px; background:var(--card); border:1px solid var(--border);
        border-radius:16px; padding:32px; box-shadow: var(--shadow);
      }
      h1 { font-size:1.8rem; margin-top:0; }
      p { line-height:1.6; margin:1em 0; }
      a { color:var(--link); text-decoration:none; }
      a:hover { text-decoration:underline; }
      footer { margin-top:24px; font-size:0.9rem; color:var(--muted); }
    </style>
  </head>
  <body>
    <main>
      <h1>Terms of Service</h1>
      <p>
        By installing and using Rephrasely, you agree to the following terms:
      </p>
      <p>
        Rephrasely is provided as-is, without warranties of any kind. While we make every
        effort to ensure reliability and security, we do not guarantee uninterrupted service
        or error-free operation.
      </p>
      <p>
        You are responsible for how you use the app within Slack, including compliance with
        your organization’s policies and Slack’s <a href="https://slack.com/terms-of-service" target="_blank">Terms of Service</a>.
      </p>
      <p>
        Rephrasely does not store your message content. Minimal installation data
        (such as team IDs, user IDs, and OAuth tokens) is kept only to provide the app’s
        functionality. You may revoke access at any time by uninstalling the app from Slack.
      </p>
      <p>
        We reserve the right to update these Terms at any time. Continued use of the app
        after changes indicates your acceptance of the new Terms.
      </p>
      <footer>
        Open Source: <a href="https://github.com/bueltan/rephrasely" target="_blank">GitHub Repo</a> ·
        <a href="https://bueltan.github.io/" target="_blank">About me</a>
      </footer>
    </main>
  </body>
</html>
    """