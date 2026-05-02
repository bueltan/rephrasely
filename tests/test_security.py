"""Tests for Slack request signature validation."""

import hashlib
import hmac

from rephrasely.security import is_valid_slack_signature


def test_valid_slack_signature():
    """A correctly signed Slack request is accepted."""
    secret = "signing-secret"
    timestamp = "1714600000"
    body = "token=abc&team_id=T123&text=hello"
    digest = hmac.new(
        secret.encode("utf-8"),
        f"v0:{timestamp}:{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert is_valid_slack_signature(
        secret,
        timestamp,
        f"v0={digest}",
        body,
        now=1714600001,
    )


def test_rejects_expired_slack_signature():
    """A request outside Slack's replay window is rejected."""
    assert not is_valid_slack_signature(
        "signing-secret",
        "1714600000",
        "v0=anything",
        "body",
        now=1714600400,
    )
