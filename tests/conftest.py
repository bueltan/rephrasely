"""Shared test environment defaults."""

import os


os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ.setdefault("SLACK_CLIENT_ID", "client-id")
os.environ.setdefault("SLACK_CLIENT_SECRET", "client-secret")
os.environ.setdefault("SLACK_REDIRECT_URI", "http://localhost/slack/oauth/callback")
os.environ.setdefault("SLACK_SIGNING_SECRET", "signing-secret")
os.environ.setdefault("REPHRASELY_SITE_URL", "https://rephrasely.example")
