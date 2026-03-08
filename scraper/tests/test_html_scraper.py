import responses as resp_mock
from scrapers.html import HtmlScraper

SITE = {
    "id": "site-html",
    "name": "Test HTML",
    "url": "https://example.com/list",
    "selector": {
        "type": "html",
        "container": ".item",
        "title": ".title",
        "link": "a@href",
        "base_url": "https://example.com"
    }
}

HTML_CONTENT = """
<html><body>
  <div class="item">
    <span class="title"><a href="/article/1">Article One</a></span>
  </div>
  <div class="item">
    <span class="title"><a href="/article/2">Article Two</a></span>
  </div>
</body></html>
"""


@resp_mock.activate
def test_html_scraper_parses_items():
    resp_mock.add(resp_mock.GET, "https://example.com/list", body=HTML_CONTENT)
    scraper = HtmlScraper()
    items = scraper.run(SITE)
    assert len(items) == 2
    assert items[0]["title"] == "Article One"
    assert items[0]["link"] == "https://example.com/article/1"


@resp_mock.activate
def test_html_scraper_handles_http_error():
    resp_mock.add(resp_mock.GET, "https://example.com/list", status=404)
    scraper = HtmlScraper()
    items = scraper.run(SITE)
    assert items == []


@resp_mock.activate
def test_html_scraper_resolves_relative_links():
    resp_mock.add(resp_mock.GET, "https://example.com/list", body=HTML_CONTENT)
    scraper = HtmlScraper()
    items = scraper.run(SITE)
    assert items[1]["link"] == "https://example.com/article/2"
