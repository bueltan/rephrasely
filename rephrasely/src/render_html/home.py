home_html = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Rephrasely • Your AI Slack Assistant</title>
    <style>
      body {
        margin: 0;
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
        background: #f9fafb;
        color: #333;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        min-height: 100vh;
        padding: 40px 20px;
        text-align: center;
      }
      h1 {
        font-size: 2.2rem;
        margin: 1rem 0 0.5rem;
      }
      p {
        max-width: 640px;
        font-size: 1.1rem;
        line-height: 1.5;
      }
      .logo {
        width: 96px;
        height: 96px;
        border-radius: 50%;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
      }
      .slack-btn {
        margin-top: 20px;
      }
      .usage {
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 12px 18px;
        margin: 24px auto;
        font-family: monospace;
        font-size: 1rem;
        color: #222;
        display: inline-block;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
      }
      iframe {
        margin-top: 40px;
        width: 560px;
        max-width: 100%;
        aspect-ratio: 16 / 9;
        border: none;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
      }
      .ai-disclaimer {
        margin: 20px auto 0;
        max-width: 640px;
        background: #fff3cd;
        border: 1px solid #ffe69c;
        color: #664d03;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 0.95rem;
        line-height: 1.4;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
      }
      .footer-links {
        margin-top: 24px;
        font-size: .95rem;
        color: #555;
      }
      .footer-links a {
        color: #555;
        text-decoration: none;
        margin: 0 6px;
      }
      .footer-links a:hover {
        text-decoration: underline;
      }
    </style>
  </head>
  <body>
    <img src="https://avatars.slack-edge.com/2025-07-27/9256789801219_5f9092f24cb6e34a01a0_192.png"
         alt="Rephrasely Logo"
         class="logo" />

    <h1>Rephrasely</h1>
    <p>
      Rephrasely is an intelligent assistant that helps you send clearer,
      more thoughtful messages. Before your message goes out, Rephrasely uses AI
      to refine your text—whether that means rephrasing for tone, improving clarity,
      or aligning with your communication goals.
    </p>

    <div class="ai-disclaimer">
      ⚠️ <strong>AI Disclaimer:</strong> Rephrasely uses artificial intelligence to generate message
      suggestions. These responses may be inaccurate, incomplete, or misleading and should not be
      relied upon as a sole source of truth. Always review and verify important information before
      sending.
    </div>

    <div class="usage">/rephrasely Your original message here</div>

    <div class="slack-btn">
      <a href="{{ url_for('install') }}">
        <img alt="Add to Slack" height="40" width="139"
             src="https://platform.slack-edge.com/img/add_to_slack.png"
             srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x,
                     https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" />
      </a>
    </div>

    <iframe src="https://www.youtube.com/embed/DN5VTZUfhE4"
            title="Rephrasely how to use"
            allowfullscreen></iframe>

    <div class="footer-links">
      <a href="{{ url_for('support') }}">Support</a> ·
      <a href="{{ url_for('privacy') }}">Privacy</a> ·
      <a href="{{ url_for('terms') }}">Terms</a> ·
      <a href="https://github.com/bueltan/rephrasely" target="_blank">GitHub</a> ·
      <a href="https://bueltan.github.io/" target="_blank">About</a>
    </div>
  </body>
</html>
"""
