import os
from pathlib import Path
from flask import (Flask, abort, redirect, request,session, json, render_template_string, jsonify, url_for)
from threading import Thread
import requests
import logging
from logging.handlers import RotatingFileHandler

from rephrasely.src.grok_llm_rephrasely import rephrasely_method
from rephrasely.src.os_env import get_user_environment_variable
from rephrasely.src.set_env_os import save_tokens, read_all_tokens
import secrets
from urllib.parse import urlencode
from werkzeug.middleware.proxy_fix import ProxyFix
from markupsafe import escape


REPO_ROOT = Path(__file__).resolve().parents[2]  # rephrasely/src/app.py → parents[2] = repo root
LOG_DIR = Path(os.environ.get("LOG_DIR", REPO_ROOT / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)  # <-- ensure folder exists
LOG_FILE = LOG_DIR / "flaskapp.log"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")

IS_PROD = os.getenv("FLASK_ENV") == "production"

app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY") or "",  # must be non-empty
    SESSION_PERMANENT=False,
    SESSION_COOKIE_HTTPONLY=True,
    # For OAuth redirects:
    # - PROD over HTTPS: cookies must be sent cross-site -> SameSite=None + Secure=True
    # - DEV on http://127.0.0.1:5000: use Lax (Secure=False)
    SESSION_COOKIE_SAMESITE="None" if IS_PROD else "Lax",
    SESSION_COOKIE_SECURE=IS_PROD,
)

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

if not app.debug:
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    if app.logger.hasHandlers():
        app.logger.handlers.clear()

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

SLACK_API_BASE = "https://slack.com/api"
SLACK_VIEWS_OPEN = f"{SLACK_API_BASE}/views.open"
SLACK_VIEWS_UPDATE = f"{SLACK_API_BASE}/views.update"
SLACK_CHAT_POST = f"{SLACK_API_BASE}/chat.postMessage"


CLIENT_ID = get_user_environment_variable("SLACK_CLIENT_ID") or ""
CLIENT_SECRET = get_user_environment_variable("SLACK_CLIENT_SECRET") or ""
REDIRECT_URI = ( get_user_environment_variable("SLACK_REDIRECT_URI") or
                "https://rephrasely.com.ar/slack/oauth/callback")


if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("SLACK_CLIENT_ID and SLACK_CLIENT_SECRET must be set in environment variables.")

TOKENS_FILE = Path("/home/d_gimenez/apps/rephrasely/tokens.yml")

@app.get("/_test/session")
def _test_session():
    session["ping"] = "pong"
    return {"stored": True, "state_present": bool(session.get("oauth_state"))}

# Configure the scopes you need
BOT_SCOPES  = ["commands"]                # minimal bot scope
USER_SCOPES = ["chat:write"]              # minimal user scope (add more if needed)



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


# ---------- pretty error pages ----------
@app.errorhandler(400)
def handle_400(e):
    body = f"""
      <p class="err">Installation error (400).</p>
      <div class="help"><strong>Details:</strong> {escape(getattr(e, "description", "Bad request"))}</div>
      <div class="cta">
        <a class="btn" href="{{{{ url_for('install') }}}}">Try again</a>
        <a class="btn" href="{{{{ url_for('home') }}}}">Back to Home</a>
      </div>
    """
    return render_page("Install error", body, status=400)

@app.errorhandler(502)
def handle_502(e):
    body = f"""
      <p class="err">Temporary gateway error (502).</p>
      <div class="help"><strong>Details:</strong> {escape(getattr(e, "description", "Upstream error"))}</div>
      <div class="cta">
        <a class="btn" href="{{{{ url_for('install') }}}}">Try again</a>
        <a class="btn" href="{{{{ url_for('home') }}}}">Back to Home</a>
      </div>
    """
    return render_page("Install error", body, status=502)



def require_env(*keys: str):
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")

require_env("SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET", "SLACK_REDIRECT_URI")


def load_team(team_id: str) -> dict:
    """ Load tokens for a given team_id. Returns {} if not found.
    """
    return read_all_tokens().get(team_id, {})

def get_bot_token(team_id: str) -> str:
    """ Load the bot token for a given team_id. Raises if not found.
    """
    team = load_team(team_id)
    token = (team.get("bot") or {}).get("access_token")
    if not token:
        raise RuntimeError(f"No bot_token for team_id={team_id}")
    return token

def get_user_token(team_id: str, user_id: str) -> str:
    """ Load the user token for (team_id, user_id).
        Raises if not found.
    """
    team = load_team(team_id)
    token = ((team.get("users") or {}).get(user_id) or {}).get("access_token")
    if not token:
        raise RuntimeError(f"No user_token for team_id={team_id}, user_id={user_id}")
    return token

def build_authorize_url(state: str) -> str:
    """ Build the Slack OAuth authorize URL with bot and user scopes."""
    params = {
        "client_id": CLIENT_ID,
        "scope": ",".join(BOT_SCOPES),
        "user_scope": ",".join(USER_SCOPES),
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }
    return "https://slack.com/oauth/v2/authorize?" + urlencode(params)

def exchange_oauth_code(code: str) -> dict:
    """
    Call Slack OAuth to exchange a temporary 'code' for tokens.
    Returns the parsed JSON dict from Slack.
    Raises on transport errors; returns {"ok": false, "error": "..."} if Slack rejects.
    """
    resp = requests.post(
        "https://slack.com/api/oauth.v2.access",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def mask(token: str | None) -> str:
    return token[:10] + "..." + token[-6:] if token else "—"


@app.route("/")
def home():
    return render_template_string("""
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
    </style>
  </head>
  <body>
    <img src="https://avatars.slack-edge.com/2025-07-27/9256789801219_5f9092f24cb6e34a01a0_192.png"
         alt="Rephrasely Logo"
         class="logo" />

    <h1>Rephrasely</h1>
    <p>
      Rephrasely is your intelligent Slack assistant that helps you send clearer,
      more thoughtful messages. Before your message goes out, Rephrasely uses AI
      to refine your text—whether that means rephrasing for tone, improving clarity,
      or aligning with your communication goals.
    </p>

    <div class="usage">/re Your original message here</div>

    <div class="slack-btn">
      <a href="{{ url_for('install') }}">
        <img alt="Add to Slack" height="40" width="139"
             src="https://platform.slack-edge.com/img/add_to_slack.png"
             srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x,
                     https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" />
      </a>
    </div>

    <iframe src="https://www.youtube.com/embed/RkcwLKBhhLA"
            title="Rephrasely how to use"
            allowfullscreen></iframe>
  </body>
                                  
<div style="margin-top:16px; font-size:.95rem; color:#555;">
  <a href="{{ url_for('support') }}">Support</a> ·
  <a href="{{ url_for('privacy') }}">Privacy</a> ·
  <a href="{{ url_for('terms') }}">Terms</a> ·
  <a href="https://github.com/bueltan/rephrasely" target="_blank">GitHub</a> ·
  <a href="https://bueltan.github.io/" target="_blank">About</a>
</div>


                                
</html>
    """)



@app.route("/slack/oauth/callback")
def oauth_callback():
    """Handle Slack OAuth and persist bot & user tokens using new schema."""
    if (err := request.args.get("error")):
        return abort(400, description=f"Slack returned error: {err}")

    code = request.args.get("code")
    state = request.args.get("state")
    if not code:
        return abort(400, description="Missing ?code")

    # CSRF check
    expected_state = session.get("oauth_state")
    if expected_state and state != expected_state:
        return abort(400, description="Invalid state")

    # Prevent duplicate code use on refresh
    if session.get("used_oauth_code") == code:
        return redirect(url_for("home"))

    try:
        data = exchange_oauth_code(code)
    except Exception as e:
        app.logger.exception("OAuth exchange failed")
        return abort(502, description=f"OAuth exchange failed: {e}")

    app.logger.debug("OAuth response: %s", data)

    if not data.get("ok"):
        # Example: {"ok": false, "error": "invalid_code"}
        return abort(400, description=f"Slack error: {data.get('error','unknown')}")

    # Extract tokens and ids
    bot_token   = data.get("access_token")  # xoxb-...
    authed_user = data.get("authed_user") or {}
    user_token  = authed_user.get("access_token")  # xoxp-...
    user_id     = authed_user.get("id")

    team        = data.get("team") or {}
    team_id     = team.get("id")
    team_name   = team.get("name")

    enterprise  = data.get("enterprise") or {}
    enterprise_id = enterprise.get("id")

    # Persist using new schema
    if bot_token or user_token:
        save_tokens(
            bot_token=bot_token,
            user_token=user_token,
            team_id=team_id,
            user_id=user_id,
            team_name=team_name,
            enterprise_id=enterprise_id,
        )

    # Mark code used and clear state
    session["used_oauth_code"] = code
    session.pop("oauth_state", None)

    # Success page content
    masked_bot  = escape(mask(bot_token))
    masked_user = escape(mask(user_token)) if user_token else "—"

    user_hint = ""
    if not user_token:
        # Helpful guidance if the app didn’t get a user token
        user_hint = """
          <div class="help">
            <strong>Heads up:</strong> We didn’t receive a user token (xoxp).<br/>
            If you want Rephrasely to send messages <em>as you</em>, re-install and ensure the app requests
            <code>user_scope</code> (e.g. <code>chat:write</code>) and you approve it.
          </div>
        """

    body = f"""
      <p class="ok">Install completed successfully.</p>

      <div class="kv">
        <div>Team</div><div><strong>{escape(team_name or "—")}</strong> ({escape(team_id or "—")})</div>
        <div>User</div><div><strong>{escape(user_id or "—")}</strong></div>
        <div>Bot token</div><div><code>{masked_bot}</code></div>
        <div>User token</div><div><code>{masked_user}</code></div>
      </div>

      {user_hint}

      <div class="hr"></div>

      <div class="cta">
        <a class="btn primary" href="https://slack.com/app_redirect?app={escape(CLIENT_ID)}">Open in Slack</a>
        <a class="btn" href="{{{{ url_for('home') }}}}">Back to Home</a>
        <span class="slack-btn">
          <a class="btn" href="{{{{ url_for('install') }}}}">Install to another workspace</a>
        </span>
      </div>
    """
    return render_page("Install successful", body, status=200)



# =========================
# Debug routes (updated)
# =========================
def _slack_auth_test(token: str) -> dict:
    """Hit auth.test with any token to inspect who it is."""
    r = requests.post(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {token}"},
        timeout=8,
    )
    return r.json()

@app.route("/debug/auth-test/bot/<team_id>")
def debug_auth_test_bot(team_id):
    """Test the bot token for a workspace."""
    token = get_bot_token(team_id)
    return jsonify(_slack_auth_test(token))

@app.route("/debug/auth-test/user/<team_id>/<user_id>")
def debug_auth_test_user(team_id, user_id):
    """Test the user token for (team_id, user_id)."""
    token = get_user_token(team_id, user_id)
    return jsonify(_slack_auth_test(token))

# ----------------------------------------------------------

def _bot_headers(team_id: str) -> dict:
    return {
        "Authorization": f"Bearer {get_bot_token(team_id)}",
        "Content-Type": "application/json",
    }

def _user_headers(team_id: str, user_id: str) -> dict:
    return {
        "Authorization": f"Bearer {get_user_token(team_id, user_id)}",
        "Content-Type": "application/json",
    }

#-----------------------------------------------------------
def open_working_modal(trigger_id: str, channel_id: str, team_id: str) -> str:
    """
    Open a minimal modal that shows a spinner/message quickly.
    Return the view_id so we can later call views.update.
    """
    payload = {
        "trigger_id": trigger_id,
        "view": {
            "type": "modal",
            "callback_id": "edit_and_send_message",
            "close": {"type": "plain_text", "text": "Cancel"},
            "private_metadata": channel_id,
            "title": {"type": "plain_text", "text": "Rephrasely"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":hourglass_flowing_sand: Working on your suggestion…",
                    },
                },
            ],
        },
    }

    try:
        r = requests.post(SLACK_VIEWS_OPEN, headers=_bot_headers(team_id), json=payload, timeout=10)
        data = r.json()
    except Exception as e:
        app.logger.error("views.open transport error: %s", e)
        return ""

    if not data.get("ok"):
        app.logger.error("views.open failed: %s", data)
        return ""

    return data["view"]["id"]



@app.route("/slack/rephrasely", methods=["POST"])
def handle_command():
    """
    Slash command entrypoint:
      1) Open a quick 'Working…' modal immediately (within 3s).
      2) Kick off background work; when done, update the modal to the editable version.
    """
    data = request.form
    trigger_id   = data.get("trigger_id")
    channel_id   = data.get("channel_id")
    team_id      = data.get("team_id")  # <-- IMPORTANT
    original_text = data.get("text", "")

    if not team_id:
        # Slack always sends team_id for slash commands, but guard anyway
        app.logger.error("Missing team_id in slash command payload")
        return "", 200

    view_id = open_working_modal(trigger_id, channel_id, team_id)

    # 2) Process in background and update the modal when done
    Thread(
        target=process_and_update_modal,
        args=(view_id, channel_id, team_id, original_text),
        daemon=True,
    ).start()

    return "", 200

def process_and_update_modal(view_id: str, channel_id: str, team_id: str, original_text: str):
    """
    Runs LLM processing and updates the modal with the final editable content.
    """
    prompt = "Translate: " + (original_text or "")

    try:
        modified_text = rephrasely_method(prompt)
    except Exception as e:  # pylint: disable=broad-except
        modified_text = f"(Error generating suggestion: {e})\n\n{prompt}"

    update_modal_with_result(view_id, channel_id, team_id, modified_text)


def update_modal_with_result(view_id: str, channel_id: str, team_id: str, suggested_text: str):
    """
    Replace the 'Working…' modal with the real editable modal using views.update.
    """
    if not view_id:
        app.logger.error("No view_id available to update modal.")
        return

    new_view = {
        "type": "modal",
        "callback_id": "edit_and_send_message",
        "title": {"type": "plain_text", "text": "Edit Message"},
        "submit": {"type": "plain_text", "text": "Send"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": channel_id,
        "blocks": [
            {
                "type": "input",
                "block_id": "message_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "message_text",
                    "multiline": True,
                    "initial_value": suggested_text or "",
                },
                "label": {"type": "plain_text", "text": "Edit your message"},
            }
        ],
    }

    payload = {"view_id": view_id, "view": new_view}

    try:
        r = requests.post(SLACK_VIEWS_UPDATE, headers=_bot_headers(team_id), json=payload, timeout=20)
        if not r.ok:
            app.logger.error("views.update failed: %s", r.text)
    except Exception as e: # pylint: disable=broad-except
        app.logger.error("views.update transport error: %s", e)

        
# =========================
# Interactions handler (updated)
# =========================
@app.route("/slack/interactions", methods=["POST"])
def handle_view_submission():
    """
    Handle the modal submission (view_submission).
    Expects channel_id in view.private_metadata, team.id and user.id in payload.
    """
    payload = request.form.to_dict()
    payload_data = json.loads(payload.get("payload", "{}"))

    if payload_data.get("type") == "view_submission":
        values      = payload_data["view"]["state"]["values"]
        edited_text = values["message_input"]["message_text"]["value"]
        channel_id  = payload_data["view"]["private_metadata"]

        team_id = (payload_data.get("team") or {}).get("id")
        user_id = (payload_data.get("user") or {}).get("id")

        if not team_id or not user_id:
            app.logger.error("Missing team_id or user_id in interaction payload")
            return "", 200

        send_message_as_user(channel_id, team_id, user_id, edited_text)
        return "", 200

    # Other interaction types can be handled here if needed
    return "", 200

def send_message_as_user(channel_id: str, team_id: str, user_id: str, text: str) -> dict:
    """
    Post the message as the *real user* who authorized (uses xoxp user token).
    Falls back to empty dict on error; logs details.
    """
    try:
        headers = _user_headers(team_id, user_id)
    except RuntimeError as e:
        app.logger.error("Cannot send as user: %s", e)
        return {}

    payload = {"channel": channel_id, "text": text}

    try:
        r = requests.post(SLACK_CHAT_POST, headers=headers, json=payload, timeout=10)
        if not r.ok:
            app.logger.error("chat.postMessage failed: %s", r.text)
            return {}
        return r.json() if r.content else {}
    except Exception as e:
        app.logger.error("chat.postMessage transport error: %s", e)
        return {}


def get_latest_messages(channel_id: str, team_id: str, user_id: str, limit: int = 5) -> dict:
    """
    Fetch latest messages from a channel using the *user token* (so it's 'as that user').
    Requires both team_id and user_id to resolve the right xoxp token.
    """
    url = f"{SLACK_API_BASE}/conversations.history"

    try:
        headers = _user_headers(team_id, user_id)
    except RuntimeError as e:
        app.logger.error("Cannot load messages (missing user token): %s", e)
        return {}

    params = {"channel": channel_id, "limit": limit}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if not response.ok:
            app.logger.error("conversations.history failed: %s", response.text)
            return {}
        return response.json()
    except Exception as e:
        app.logger.error("conversations.history transport error: %s", e)
        return {}


@app.get("/install")
def install():
    """
    Redirects to Slack OAuth with a fresh state.
    Use this as the href for your 'Add to Slack' button.
    """
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    return redirect(build_authorize_url(state))

@app.route("/privacy")
def privacy():
    return render_template_string("""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Rephrasely • Privacy Policy</title>
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <style>
      body {
        margin:0; font-family: system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
        background:#f9fafb; color:#1f2937;
        display:flex; justify-content:center; padding:40px 20px;
      }
      main {
        max-width:720px; background:#fff; border:1px solid #e5e7eb;
        border-radius:16px; padding:32px;
        box-shadow:0 8px 20px rgba(0,0,0,.06);
      }
      h1 { font-size:1.8rem; margin-top:0; }
      p { line-height:1.6; margin:1em 0; }
      a { color:#2563eb; text-decoration:none; }
      a:hover { text-decoration:underline; }
      footer { margin-top:24px; font-size:0.9rem; color:#6b7280; }
    </style>
  </head>
  <body>
    <main>
      <h1>Privacy Policy</h1>
      <p>
        Rephrasely is an open-source Slack app designed to help you refine and improve
        your messages using AI. We respect your privacy and are committed to protecting it.
      </p>
      <p>
        <strong>No message content is stored on our servers.</strong> All processing is performed
        in memory and only for the purpose of generating improved message suggestions.
      </p>
      <p>
        We may store minimal installation information (such as Slack team IDs, user IDs, and OAuth
        tokens) solely for the purpose of enabling the app to function within your workspace.
        This data is never shared with third parties and can be revoked at any time by removing
        the app from Slack.
      </p>
      <p>
        By using Rephrasely, you agree that your input messages are processed temporarily to
        generate suggestions, but are not logged, retained, or sold.
      </p>
      <footer>
        <p>
          Open Source: <a href="https://github.com/bueltan/rephrasely" target="_blank">GitHub Repo</a> ·
          <a href="https://bueltan.github.io/" target="_blank">About me</a>
        </p>
      </footer>
    </main>
  </body>
</html>
    """)


@app.route("/support")
def support():
    return render_template_string("""
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
    """)


@app.route("/terms")
def terms():
    return render_template_string("""
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
    """)


if __name__ == "__main__":
    app.run(port=5000)
