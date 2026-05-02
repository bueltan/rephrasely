"""Run a manual Grok rewrite prompt from the command line."""

import requests

from rephrasely.llm.grok import rephrase_text


def main() -> None:
    """Send an example English rewrite prompt to Grok and print the result."""
    prompt = (
        "Please rewrite this message in clear, natural English: "
        "Hi Santiago, I hope you are doing well. I am working on a Poetry migration "
        "and could use your help understanding how to start the project locally. "
        "Could we talk tomorrow when you have a moment?"
    )
    try:
        result = rephrase_text(prompt, model="grok-3-latest", stream=False)
        print("\n\n--- RESULT ---\n", result)
    except requests.HTTPError as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()
