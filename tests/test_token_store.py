"""Tests for YAML-backed Slack token persistence."""

from rephrasely.token_store import TokenStore


def test_save_and_read_tokens(tmp_path):
    """Saved bot and user tokens can be read back by team and user."""
    store = TokenStore(tmp_path / "tokens.yml")

    store.save(
        bot_token="xoxb-token",
        user_token="xoxp-token",
        team_id="T123",
        user_id="U123",
        team_name="Example",
    )

    assert store.get_bot_token("T123") == "xoxb-token"
    assert store.get_user_token("T123", "U123") == "xoxp-token"
    assert store.load_team("T123")["team_name"] == "Example"
