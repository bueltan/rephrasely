"""Send a manual Slack message with a user token."""

import requests

USER_TOKEN = ""


def main() -> None:
    """Post a test message to Slack using the configured user token."""
    headers = {
        "Authorization": f"Bearer {USER_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "channel": "#general",
        "text": "Hello, this test message was sent with a user token.",
    }
    response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload, timeout=10)
    print(response.json())


if __name__ == "__main__":
    main()
