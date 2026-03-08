import pytest
from unittest.mock import patch
from scrapers.rss import RssScraper

SAMPLE_FEED = {
    "entries": [
        {
            "title": "Rust Is Amazing",
            "link": "https://example.com/rust",
            "summary": "Rust beats C++",
            "published_parsed": (2026, 3, 8, 10, 0, 0, 0, 0, 0)
        },
        {
            "title": "Python Tips",
            "link": "https://example.com/python",
            "summary": "",
            "published_parsed": None
        }
    ]
}

SITE = {
    "id": "site-rss",
    "name": "Test RSS",
    "url": "https://example.com",
    "selector": {"type": "rss", "url": "https://example.com/rss"}
}


def test_rss_scraper_parses_entries():
    scraper = RssScraper()
    with patch("scrapers.rss.feedparser.parse", return_value=SAMPLE_FEED):
        items = scraper.run(SITE)
    assert len(items) == 2
    assert items[0]["title"] == "Rust Is Amazing"
    assert items[0]["link"] == "https://example.com/rust"
    assert items[0]["summary"] == "Rust beats C++"


def test_rss_scraper_handles_missing_published():
    scraper = RssScraper()
    with patch("scrapers.rss.feedparser.parse", return_value=SAMPLE_FEED):
        items = scraper.run(SITE)
    assert items[1]["published_at"] is None


def test_rss_scraper_uses_selector_url():
    """Should fetch from selector.url, not site.url"""
    captured = {}
    def fake_parse(url, agent=None):
        captured["url"] = url
        return {"entries": []}
    scraper = RssScraper()
    with patch("scrapers.rss.feedparser.parse", side_effect=fake_parse):
        scraper.run(SITE)
    assert captured["url"] == "https://example.com/rss"
