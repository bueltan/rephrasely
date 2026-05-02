"""Thin Slack Web API wrapper."""

from __future__ import annotations

from urllib.parse import urlencode

import requests

from rephrasely.token_store import TokenStore

SLACK_API_BASE = "https://slack.com/api"


class SlackClient:
    """Minimal client for the Slack endpoints used by Rephrasely."""

    def __init__(
        self,
        token_store: TokenStore,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        """Store Slack app credentials and token persistence."""
        self.token_store = token_store
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def build_authorize_url(self, state: str) -> str:
        """Build the Slack OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "scope": "commands",
            "user_scope": "chat:write",
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return "https://slack.com/oauth/v2/authorize?" + urlencode(params)

    def exchange_oauth_code(self, code: str) -> dict:
        """Exchange a temporary OAuth code for Slack tokens."""
        response = requests.post(
            f"{SLACK_API_BASE}/oauth.v2.access",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def bot_headers(self, team_id: str) -> dict:
        """Build authorization headers for a workspace bot token."""
        return {
            "Authorization": f"Bearer {self.token_store.get_bot_token(team_id)}",
            "Content-Type": "application/json",
        }

    def user_headers(self, team_id: str, user_id: str) -> dict:
        """Build authorization headers for a user token."""
        return {
            "Authorization": f"Bearer {self.token_store.get_user_token(team_id, user_id)}",
            "Content-Type": "application/json",
        }

    def open_view(self, team_id: str, payload: dict, timeout: int = 10) -> dict:
        """Open a Slack modal view."""
        response = requests.post(
            f"{SLACK_API_BASE}/views.open",
            headers=self.bot_headers(team_id),
            json=payload,
            timeout=timeout,
        )
        return response.json()

    def update_view(self, team_id: str, payload: dict, timeout: int = 20) -> requests.Response:
        """Update an existing Slack modal view."""
        return requests.post(
            f"{SLACK_API_BASE}/views.update",
            headers=self.bot_headers(team_id),
            json=payload,
            timeout=timeout,
        )

    def post_message_as_user(self, channel_id: str, team_id: str, user_id: str, text: str) -> dict:
        """Post a message using the installing user's Slack token."""
        response = requests.post(
            f"{SLACK_API_BASE}/chat.postMessage",
            headers=self.user_headers(team_id, user_id),
            json={"channel": channel_id, "text": text},
            timeout=10,
        )
        if not response.ok:
            return {}
        return response.json() if response.content else {}

    def auth_test(self, token: str) -> dict:
        """Call Slack auth.test with the provided token."""
        response = requests.post(
            f"{SLACK_API_BASE}/auth.test",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        return response.json()
