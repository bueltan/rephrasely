"""Slack modal payload builders."""

from __future__ import annotations


def working_modal(trigger_id: str, channel_id: str) -> dict:
    """Build the temporary modal shown while a suggestion is generated."""
    return {
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
                        "text": ":hourglass_flowing_sand: Working on your suggestion...",
                    },
                },
            ],
        },
    }


def result_modal(channel_id: str, suggested_text: str) -> dict:
    """Build the editable modal containing the generated suggestion."""
    return {
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


def help_modal(trigger_id: str) -> dict:
    """Build the help modal shown for empty or help slash commands."""
    return {
        "trigger_id": trigger_id,
        "view": {
            "type": "modal",
            "callback_id": "help_modal",
            "title": {"type": "plain_text", "text": "Rephrasely Help"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*Welcome to Rephrasely!*\n\n"
                            "Quickly improve, rephrase, or polish your messages.\n\n"
                            "*How to use:*\n"
                            "- Type `/rephrasely` followed by your text\n"
                            "- A modal opens with an AI suggestion\n"
                            "- Edit if needed, then click *Send* to post as yourself\n\n"
                            "*Support / Feedback*\n"
                            "<https://rephrasely.com.ar/support|Contact support> | "
                            "<https://rephrasely.com.ar/privacy|Privacy> | "
                            "<https://rephrasely.com.ar/terms|Terms>"
                        ),
                    },
                },
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": "Tip: Try `/rephrasely help` anytime"}],
                },
            ],
        },
    }
