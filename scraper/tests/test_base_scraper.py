import pytest
from scrapers.base import BaseScraper


class ConcreteScraper(BaseScraper):
    def scrape(self, site: dict) -> list[dict]:
        return [{"title": "Test", "link": "https://example.com"}]


class EmptyTitleScraper(BaseScraper):
    def scrape(self, site):
        return [
            {"title": "Valid", "link": "https://a.com"},
            {"title": "", "link": "https://b.com"},
            {"title": None, "link": "https://c.com"},
        ]


SITE = {"id": "site-123", "name": "Test Site", "url": "https://example.com", "selector": {}}


def test_run_injects_site_id():
    scraper = ConcreteScraper()
    items = scraper.run(SITE)
    assert all("site_id" in item for item in items)
    assert items[0]["site_id"] == "site-123"


def test_run_filters_empty_titles():
    scraper = EmptyTitleScraper()
    items = scraper.run(SITE)
    assert len(items) == 1
    assert items[0]["title"] == "Valid"


def test_scraper_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseScraper()
