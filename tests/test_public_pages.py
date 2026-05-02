"""Tests for public SEO and crawler-facing pages."""

from rephrasely.app import create_app, sitemap_pages
from rephrasely.config import Settings


def make_app(tmp_path):
    """Create a test Flask app with isolated settings."""
    settings = Settings(
        repo_root=tmp_path,
        flask_secret_key="test-secret",
        is_prod=False,
        slack_client_id="client-id",
        slack_client_secret="client-secret",
        slack_redirect_uri="http://localhost/slack/oauth/callback",
        slack_signing_secret="signing-secret",
        tokens_file=tmp_path / "tokens.yml",
        log_dir=tmp_path / "logs",
        site_url="https://rephrasely.example",
    )
    return create_app(settings)


def test_home_has_seo_metadata(tmp_path):
    """The home page includes canonical metadata and JSON-LD."""
    client = make_app(tmp_path).test_client()

    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert '<link rel="canonical" href="https://rephrasely.example/">' in body
    assert '<script type="application/ld+json">' in body
    assert 'meta name="keywords"' in body
    assert 'twitter:card" content="summary_large_image"' in body
    assert "FAQPage" in body


def test_paid_landing_has_campaign_metadata(tmp_path):
    """The campaign landing page has its own canonical URL and conversion copy."""
    client = make_app(tmp_path).test_client()

    response = client.get("/slack-ai-writing-assistant")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert '<link rel="canonical" href="https://rephrasely.example/slack-ai-writing-assistant">' in body
    assert "Polish Slack Messages Before They Go Out" in body
    assert "Install Rephrasely" in body


def test_sitemap_and_robots(tmp_path):
    """Sitemap and robots routes expose crawler metadata."""
    client = make_app(tmp_path).test_client()

    sitemap = client.get("/sitemap.xml")
    robots = client.get("/robots.txt")

    assert sitemap.status_code == 200
    assert sitemap.mimetype == "application/xml"
    assert sitemap.headers["X-Robots-Tag"] == "noindex"
    assert "https://rephrasely.example/privacy" in sitemap.get_data(as_text=True)
    assert "https://rephrasely.example/slack-ai-writing-assistant" in sitemap.get_data(as_text=True)
    assert "<changefreq>yearly</changefreq>" in sitemap.get_data(as_text=True)
    assert robots.status_code == 200
    assert "Sitemap: https://rephrasely.example/sitemap.xml" in robots.get_data(as_text=True)


def test_sitemap_pages_are_ordered_by_priority(tmp_path):
    """Sitemap entries are ordered by priority and include per-page hints."""
    app = make_app(tmp_path)

    pages = sitemap_pages(app.config["REPHRASELY_SETTINGS"])

    assert pages[0]["loc"] == "https://rephrasely.example/"
    assert pages[0]["priority"] == "1.0"
    assert pages[-1]["loc"] == "https://rephrasely.example/terms"
    assert pages[-1]["changefreq"] == "yearly"
