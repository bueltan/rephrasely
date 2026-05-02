"""Flask application factory for Rephrasely."""

from __future__ import annotations

import logging
import secrets
from logging.handlers import RotatingFileHandler
from threading import Thread

from flask import Flask, Response, abort, json, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from rephrasely.config import Settings
from rephrasely.llm import rephrase_text
from rephrasely.security import is_valid_slack_signature
from rephrasely.slack_client import SlackClient
from rephrasely.slack_views import help_modal, result_modal, working_modal
from rephrasely.token_store import TokenStore

LOGO_URL = "https://avatars.slack-edge.com/2025-07-27/9256789801219_5f9092f24cb6e34a01a0_192.png"
LASTMOD = "2026-05-02"

PAGE_META = {
    "home": {
        "path": "/",
        "title": "Rephrasely | Open-source AI Slack assistant",
        "description": (
            "Rephrasely is an open-source AI Slack assistant that rewrites, translates, "
            "and polishes messages before you send them."
        ),
        "priority": "1.0",
    },
    "privacy": {
        "path": "/privacy",
        "title": "Privacy Policy | Rephrasely",
        "description": "Learn how Rephrasely handles Slack installation data and AI message processing.",
        "priority": "0.6",
    },
    "support": {
        "path": "/support",
        "title": "Support | Rephrasely",
        "description": "Get help installing, configuring, and using the Rephrasely Slack app.",
        "priority": "0.7",
    },
    "terms": {
        "path": "/terms",
        "title": "Terms of Service | Rephrasely",
        "description": "Read the terms for installing and using the Rephrasely Slack app.",
        "priority": "0.5",
    },
}


def create_app(settings: Settings | None = None) -> Flask:
    """Create and configure the Flask app."""
    settings = settings or Settings.from_env()
    settings.validate()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.flask_secret_key,
        SESSION_PERMANENT=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="None" if settings.is_prod else "Lax",
        SESSION_COOKIE_SECURE=settings.is_prod,
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    configure_logging(app, settings)

    token_store = TokenStore(settings.tokens_file)
    slack = SlackClient(
        token_store=token_store,
        client_id=settings.slack_client_id,
        client_secret=settings.slack_client_secret,
        redirect_uri=settings.slack_redirect_uri,
    )

    @app.errorhandler(400)
    def handle_400(error):
        """Render installation errors as an HTML page."""
        return render_error_page(
            settings,
            heading="Installation error",
            message="Slack could not complete the installation request.",
            detail=getattr(error, "description", "Bad request"),
            status=400,
        )

    @app.errorhandler(502)
    def handle_502(error):
        """Render upstream gateway errors as an HTML page."""
        return render_error_page(
            settings,
            heading="Temporary gateway error",
            message="Rephrasely could not reach an upstream service.",
            detail=getattr(error, "description", "Upstream error"),
            status=502,
        )

    @app.get("/_test/session")
    def _test_session():
        """Expose a development endpoint that confirms session storage works."""
        session["ping"] = "pong"
        return {"stored": True, "state_present": bool(session.get("oauth_state"))}

    @app.route("/")
    def home():
        """Render the public home page."""
        return render_template(
            "home.html",
            **page_context(settings, "home", structured_data=home_structured_data(settings)),
        )

    @app.get("/install")
    def install():
        """Start Slack OAuth installation with a fresh state token."""
        state = secrets.token_urlsafe(24)
        session["oauth_state"] = state
        return redirect(slack.build_authorize_url(state))

    @app.route("/slack/oauth/callback")
    def oauth_callback():
        """Handle Slack OAuth completion and persist workspace tokens."""
        if error := request.args.get("error"):
            return abort(400, description=f"Slack returned error: {error}")

        code = request.args.get("code")
        state = request.args.get("state")
        if not code:
            return abort(400, description="Missing ?code")

        expected_state = session.get("oauth_state")
        if expected_state and state != expected_state:
            return abort(400, description="Invalid state")

        if session.get("used_oauth_code") == code:
            return redirect(url_for("home"))

        try:
            data = slack.exchange_oauth_code(code)
        except Exception as exc:
            app.logger.exception("OAuth exchange failed")
            return abort(502, description=f"OAuth exchange failed: {exc}")

        app.logger.debug("OAuth response: %s", data)
        if not data.get("ok"):
            return abort(400, description=f"Slack error: {data.get('error', 'unknown')}")

        authed_user = data.get("authed_user") or {}
        team = data.get("team") or {}
        enterprise = data.get("enterprise") or {}

        token_store.save(
            bot_token=data.get("access_token"),
            user_token=authed_user.get("access_token"),
            team_id=team.get("id"),
            user_id=authed_user.get("id"),
            team_name=team.get("name"),
            enterprise_id=enterprise.get("id"),
        )

        session["used_oauth_code"] = code
        session.pop("oauth_state", None)

        return render_install_success(
            settings=settings,
            team_id=team.get("id"),
            team_name=team.get("name"),
            user_id=authed_user.get("id"),
            bot_token=data.get("access_token"),
            user_token=authed_user.get("access_token"),
            client_id=settings.slack_client_id,
        )

    @app.route("/slack/rephrasely", methods=["POST"])
    def handle_command():
        """Handle the Rephrasely Slack slash command."""
        if not verify_slack_request(settings.slack_signing_secret):
            abort(403)

        data = request.form
        trigger_id = data.get("trigger_id", "")
        channel_id = data.get("channel_id", "")
        team_id = data.get("team_id", "")
        text = data.get("text", "").strip()

        if not team_id:
            app.logger.error("Missing team_id")
            return "", 200

        if not text or text.lower() == "help":
            if open_help_modal(app, slack, trigger_id, team_id):
                return "", 200
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": (
                        "Sorry, couldn't open the help modal right now.\n\n"
                        "Quick usage: `/rephrasely your text here`.\n"
                        "Visit https://rephrasely.com.ar/support for more help."
                    ),
                }
            ), 200

        view_id = open_working_modal(app, slack, trigger_id, channel_id, team_id)
        Thread(
            target=process_and_update_modal,
            args=(app, slack, view_id, channel_id, team_id, text),
            daemon=True,
        ).start()

        return "", 200

    @app.route("/slack/interactions", methods=["POST"])
    def handle_view_submission():
        """Handle Slack modal submissions and post the edited message."""
        payload = request.form.to_dict()
        payload_data = json.loads(payload.get("payload", "{}"))

        if payload_data.get("type") != "view_submission":
            return "", 200

        values = payload_data["view"]["state"]["values"]
        edited_text = values["message_input"]["message_text"]["value"]
        channel_id = payload_data["view"]["private_metadata"]
        team_id = (payload_data.get("team") or {}).get("id")
        user_id = (payload_data.get("user") or {}).get("id")

        if not team_id or not user_id:
            app.logger.error("Missing team_id or user_id in interaction payload")
            return "", 200

        try:
            slack.post_message_as_user(channel_id, team_id, user_id, edited_text)
        except RuntimeError as exc:
            app.logger.error("Cannot send as user: %s", exc)

        return "", 200

    @app.route("/debug/auth-test/bot/<team_id>")
    def debug_auth_test_bot(team_id):
        """Run Slack auth.test for a stored bot token."""
        return jsonify(slack.auth_test(token_store.get_bot_token(team_id)))

    @app.route("/debug/auth-test/user/<team_id>/<user_id>")
    def debug_auth_test_user(team_id, user_id):
        """Run Slack auth.test for a stored user token."""
        return jsonify(slack.auth_test(token_store.get_user_token(team_id, user_id)))

    @app.route("/privacy")
    def privacy():
        """Render the privacy policy page."""
        return render_template("privacy.html", **page_context(settings, "privacy"))

    @app.route("/support")
    def support():
        """Render the support page."""
        return render_template("support.html", **page_context(settings, "support"))

    @app.route("/terms")
    def terms():
        """Render the terms of service page."""
        return render_template("terms.html", **page_context(settings, "terms"))

    @app.route("/robots.txt")
    def robots_txt():
        """Render crawler instructions for public search engines."""
        body = render_template(
            "robots.txt",
            sitemap_url=f"{settings.site_url}/sitemap.xml",
        )
        return Response(body, mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap_xml():
        """Render the XML sitemap for public pages."""
        pages = [
            {
                "loc": f"{settings.site_url}{meta['path']}",
                "lastmod": LASTMOD,
                "changefreq": "weekly",
                "priority": meta["priority"],
            }
            for meta in PAGE_META.values()
        ]
        body = render_template("sitemap.xml", pages=pages)
        return Response(body, mimetype="application/xml")

    return app


def configure_logging(app: Flask, settings: Settings) -> None:
    """Configure rotating file and console logging for production."""
    if app.debug:
        return

    settings.log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        settings.log_dir / "flaskapp.log",
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


def verify_slack_request(signing_secret: str) -> bool:
    """Verify the active Flask request using Slack's signing secret."""
    return is_valid_slack_signature(
        signing_secret=signing_secret,
        timestamp=request.headers.get("X-Slack-Request-Timestamp"),
        signature=request.headers.get("X-Slack-Signature"),
        body=request.get_data(as_text=True),
    )


def mask(token: str | None) -> str:
    """Return a short masked representation of a token."""
    return token[:10] + "..." + token[-6:] if token else "-"


def page_context(
    settings: Settings,
    page_key: str,
    structured_data: dict | None = None,
    robots: str = "index,follow",
) -> dict:
    """Build shared template context for public pages."""
    meta = PAGE_META[page_key]
    return {
        "title": meta["title"],
        "description": meta["description"],
        "canonical_url": f"{settings.site_url}{meta['path']}",
        "logo_url": LOGO_URL,
        "robots": robots,
        "structured_data": structured_data or organization_structured_data(settings),
    }


def organization_structured_data(settings: Settings) -> dict:
    """Build SoftwareApplication structured data for Rephrasely."""
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "Rephrasely",
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Slack",
        "url": settings.site_url,
        "image": LOGO_URL,
        "description": PAGE_META["home"]["description"],
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "creator": {
            "@type": "Person",
            "name": "Denis Gimenez",
            "url": "https://bueltan.github.io/",
        },
        "codeRepository": "https://github.com/bueltan/rephrasely",
    }


def home_structured_data(settings: Settings) -> dict:
    """Build home page structured data, including FAQ answers."""
    return {
        "@context": "https://schema.org",
        "@graph": [
            organization_structured_data(settings),
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "What is Rephrasely?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Rephrasely is an open-source Slack app that uses AI to suggest clearer wording for messages.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "Does Rephrasely store message content?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "No. Message content is processed in memory to generate a suggestion and is not stored.",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "How do I use Rephrasely?",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "Type /rephrasely followed by your message in Slack, review the suggestion, and send it.",
                        },
                    },
                ],
            },
        ],
    }


def render_error_page(
    settings: Settings,
    heading: str,
    message: str,
    detail: str,
    status: int,
) -> tuple[str, int]:
    """Render a noindex error page with the provided status code."""
    return (
        render_template(
            "error.html",
            **page_context(settings, "home", robots="noindex,nofollow"),
            heading=heading,
            message=message,
            detail=detail,
        ),
        status,
    )


def render_install_success(
    settings: Settings,
    team_id: str | None,
    team_name: str | None,
    user_id: str | None,
    bot_token: str | None,
    user_token: str | None,
    client_id: str,
) -> tuple[str, int]:
    """Render the Slack installation success page."""
    return render_template(
        "install_success.html",
        **page_context(settings, "home", robots="noindex,nofollow"),
        team_id=team_id or "-",
        team_name=team_name or "-",
        user_id=user_id or "-",
        bot_token=mask(bot_token),
        user_token=mask(user_token),
        missing_user_token=not user_token,
        client_id=client_id,
    ), 200


def open_working_modal(app: Flask, slack: SlackClient, trigger_id: str, channel_id: str, team_id: str) -> str:
    """Open a temporary Slack modal while the LLM suggestion is generated."""
    try:
        data = slack.open_view(team_id, working_modal(trigger_id, channel_id))
    except Exception as exc:
        app.logger.error("views.open transport error: %s", exc)
        return ""

    if not data.get("ok"):
        app.logger.error("views.open failed: %s", data)
        return ""

    return data["view"]["id"]


def process_and_update_modal(
    app: Flask,
    slack: SlackClient,
    view_id: str,
    channel_id: str,
    team_id: str,
    original_text: str,
) -> None:
    """Generate the suggestion and update the Slack modal asynchronously."""
    prompt = "Translate: " + (original_text or "")
    try:
        modified_text = rephrase_text(prompt)
    except Exception as exc:
        modified_text = f"(Error generating suggestion: {exc})\n\n{prompt}"

    update_modal_with_result(app, slack, view_id, channel_id, team_id, modified_text)


def update_modal_with_result(
    app: Flask,
    slack: SlackClient,
    view_id: str,
    channel_id: str,
    team_id: str,
    suggested_text: str,
) -> None:
    """Replace the working modal with the editable suggestion modal."""
    if not view_id:
        app.logger.error("No view_id available to update modal.")
        return

    try:
        response = slack.update_view(
            team_id,
            {"view_id": view_id, "view": result_modal(channel_id, suggested_text)},
        )
        if not response.ok:
            app.logger.error("views.update failed: %s", response.text)
    except Exception as exc:
        app.logger.error("views.update transport error: %s", exc)


def open_help_modal(app: Flask, slack: SlackClient, trigger_id: str, team_id: str) -> bool:
    """Open the Slack help modal for empty or help slash commands."""
    try:
        response = slack.open_view(team_id, help_modal(trigger_id))
        if not response.get("ok"):
            app.logger.error("views.open for help failed: %s", response.get("error"))
            return False
        return True
    except Exception as exc:
        app.logger.error("views.open transport error for help: %s", exc)
        return False


app = create_app()


if __name__ == "__main__":
    app.run(port=5000)
