"""Application configuration and environment helpers."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def get_env(name: str, default: str | None = None) -> str | None:
    """Read an environment variable, including user-level Windows env vars."""
    value = os.environ.get(name)
    if value is not None:
        return value

    if sys.platform.startswith("win"):
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                value, _ = winreg.QueryValueEx(key, name)
                return value
        except (FileNotFoundError, OSError):
            return default

    return default


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the Flask and Slack app."""

    repo_root: Path
    flask_secret_key: str
    is_prod: bool
    slack_client_id: str
    slack_client_secret: str
    slack_redirect_uri: str
    slack_signing_secret: str
    tokens_file: Path
    log_dir: Path
    site_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from process and user-level environment variables."""
        repo_root = Path(__file__).resolve().parents[1]
        return cls(
            repo_root=repo_root,
            flask_secret_key=get_env("FLASK_SECRET_KEY", "") or "",
            is_prod=get_env("FLASK_ENV") == "production",
            slack_client_id=get_env("SLACK_CLIENT_ID", "") or "",
            slack_client_secret=get_env("SLACK_CLIENT_SECRET", "") or "",
            slack_redirect_uri=get_env(
                "SLACK_REDIRECT_URI",
                "https://rephrasely.com.ar/slack/oauth/callback",
            )
            or "",
            slack_signing_secret=get_env("SLACK_SIGNING_SECRET", "") or "",
            tokens_file=Path(
                get_env(
                    "REPHRASELY_TOKENS_FILE",
                    str(Path.home() / "apps" / "rephrasely" / "tokens.yml"),
                )
                or ""
            ),
            log_dir=Path(get_env("LOG_DIR", str(repo_root / "logs")) or ""),
            site_url=(get_env("REPHRASELY_SITE_URL", "https://rephrasely.com.ar") or "").rstrip("/"),
        )

    def validate(self) -> None:
        """Raise an error when required Slack settings are missing."""
        missing = [
            name
            for name, value in {
                "SLACK_CLIENT_ID": self.slack_client_id,
                "SLACK_CLIENT_SECRET": self.slack_client_secret,
                "SLACK_REDIRECT_URI": self.slack_redirect_uri,
                "SLACK_SIGNING_SECRET": self.slack_signing_secret,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
