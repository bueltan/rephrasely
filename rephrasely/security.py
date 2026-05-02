"""Slack request verification."""

from __future__ import annotations

import hashlib
import hmac
import time


def is_valid_slack_signature(
    signing_secret: str,
    timestamp: str | None,
    signature: str | None,
    body: str,
    now: float | None = None,
) -> bool:
    """Validate Slack's v0 request signature."""
    if not signing_secret or not timestamp or not signature:
        return False

    try:
        request_time = int(timestamp)
    except ValueError:
        return False

    if abs((now or time.time()) - request_time) > 60 * 5:
        return False

    base_string = f"v0:{request_time}:{body}"
    computed = hmac.new(
        signing_secret.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"v0={computed}", signature)
