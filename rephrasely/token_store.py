"""Token persistence for installed Slack workspaces."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml


def _now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class TokenStore:
    """Small YAML-backed token store keyed by Slack team id."""

    def __init__(self, path: Path):
        """Store the YAML path used for token persistence."""
        self.path = path

    def read_all(self) -> dict:
        """Read all stored workspace token records."""
        if not self.path.exists():
            return {}
        return yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}

    def load_team(self, team_id: str) -> dict:
        """Return the token record for a Slack team."""
        return self.read_all().get(team_id, {})

    def get_bot_token(self, team_id: str) -> str:
        """Return the bot token for a Slack team."""
        token = (self.load_team(team_id).get("bot") or {}).get("access_token")
        if not token:
            raise RuntimeError(f"No bot_token for team_id={team_id}")
        return token

    def get_user_token(self, team_id: str, user_id: str) -> str:
        """Return a user token for a Slack team and user."""
        users = self.load_team(team_id).get("users") or {}
        token = (users.get(user_id) or {}).get("access_token")
        if not token:
            raise RuntimeError(f"No user_token for team_id={team_id}, user_id={user_id}")
        return token

    def save(
        self,
        bot_token: str | None,
        user_token: str | None,
        team_id: str | None,
        user_id: str | None,
        team_name: str | None = None,
        enterprise_id: str | None = None,
    ) -> None:
        """Save bot and user tokens for a Slack installation."""
        if not team_id:
            raise ValueError("Missing team_id to save tokens")

        data = self.read_all()
        team = data.setdefault(team_id, {})
        if team_name:
            team["team_name"] = team_name
        if enterprise_id:
            team["enterprise_id"] = enterprise_id

        if bot_token:
            bot = team.setdefault("bot", {})
            bot["access_token"] = bot_token
            bot["installed_at"] = _now_iso()

        if user_token and user_id:
            users = team.setdefault("users", {})
            user_entry = users.setdefault(user_id, {})
            user_entry["access_token"] = user_token
            user_entry["authed_at"] = _now_iso()

        self._atomic_write(data)

    def _atomic_write(self, data: dict) -> None:
        """Write YAML data atomically with user-only permissions."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", delete=False, dir=str(self.path.parent), encoding="utf-8"
        ) as temp_file:
            yaml.safe_dump(data, temp_file, sort_keys=True, allow_unicode=True)
            temp_name = temp_file.name
        os.replace(temp_name, self.path)
        os.chmod(self.path, 0o600)
