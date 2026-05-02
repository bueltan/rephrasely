# Rephrasely

[![Watch the video](image_about.png)](https://youtu.be/DN5VTZUfhE4)

Rephrasely is an open-source Slack app that helps people send clearer messages. It receives text through the `/rephrasely` slash command, asks an LLM to translate or improve the message, opens an editable Slack modal, and posts the final text as the installing user.


## What it does

- Installs into Slack through OAuth 2.0.
- Handles `/rephrasely your message here`.
- Verifies Slack request signatures.
- Uses xAI Grok by default for rewriting and translation.
- Stores Slack bot/user OAuth tokens in a local YAML file.
- Serves public pages for home, privacy, support, and terms.

## Project structure

```text
rephrasely/
  app.py              Flask app factory, routes, and request flow
  config.py           Runtime settings and env lookup
  security.py         Slack signature validation
  slack_client.py     Slack Web API wrapper
  slack_views.py      Slack modal payload builders
  token_store.py      YAML-backed Slack token persistence
  llm/
    grok.py           xAI Grok provider
    ollama.py         Optional local Ollama provider
  templates/          Flask HTML, XML, and text templates
scripts/manual/       Manual local experiments
tests/                Unit tests
```

## Requirements

- Python 3.11+
- Poetry
- A Slack app with slash commands, interactivity, and OAuth enabled
- An xAI API key for Grok

## Environment variables

Create local environment variables before running the app:

```bash
export FLASK_SECRET_KEY="change-me"
export FLASK_ENV="development"
export SLACK_CLIENT_ID="..."
export SLACK_CLIENT_SECRET="..."
export SLACK_SIGNING_SECRET="..."
export SLACK_REDIRECT_URI="https://your-domain/slack/oauth/callback"
export XAI_API_KEY="..."
export REPHRASELY_TOKENS_FILE="./tokens.yml"
export REPHRASELY_SITE_URL="https://rephrasely.com.ar"
```

`tokens.yml` is ignored by git because it contains OAuth secrets. In production, point `REPHRASELY_TOKENS_FILE` to a persistent private path.

## Install and run locally

```bash
poetry install
poetry run flask --app rephrasely.app:app run --debug --port 5000
```

For Slack to reach your local machine, expose port `5000` with a tunneling tool and configure these Slack URLs:

- Slash command: `https://your-tunnel/slack/rephrasely`
- Interactivity: `https://your-tunnel/slack/interactions`
- OAuth redirect: `https://your-tunnel/slack/oauth/callback`

The included `slack_rephrasely_manifest.yml` is a starting point for the Slack app manifest.

## Slack scopes

Current minimal scopes:

- Bot scope: `commands`
- User scope: `chat:write`

`chat:write` as a user scope lets Rephrasely post the edited result as the user who approved the installation.

## Run tests

```bash
poetry run pytest
```

The current tests cover Slack signature verification, token persistence, public page metadata, `robots.txt`, and `sitemap.xml`. Add route-level tests when changing OAuth, modal handling, or Slack API behavior.

## SEO and AEO

Public pages are rendered from Flask templates in `rephrasely/templates/`.

- `base.html` owns shared metadata, canonical URLs, Open Graph tags, Twitter card tags, and JSON-LD.
- `home.html` includes FAQ content and FAQ structured data for answer-engine visibility.
- `/sitemap.xml` is rendered from known public routes.
- `/robots.txt` points crawlers to the sitemap.
- `REPHRASELY_SITE_URL` controls canonical URLs and sitemap locations.

## Deployment notes

The WSGI target is:

```text
rephrasely.app:app
```

Recommended production settings:

- Set `FLASK_ENV=production`.
- Use HTTPS for Slack callbacks.
- Store `REPHRASELY_TOKENS_FILE` outside the repo.
- Rotate Slack and xAI secrets if they were ever committed or shared.
- Keep logs outside the app package by setting `LOG_DIR`.

## Development notes

- Keep Slack API calls inside `rephrasely/slack_client.py`.
- Keep modal JSON builders inside `rephrasely/slack_views.py`.
- Keep LLM provider-specific behavior inside `rephrasely/llm/`.

## License

Rephrasely is released under the MIT License. See [LICENSE](LICENSE) for details.
