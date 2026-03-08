import logging
import feedparser
from datetime import datetime, timezone
from scrapers.base import BaseScraper

log = logging.getLogger(__name__)


class RssScraper(BaseScraper):
    def scrape(self, site: dict) -> list[dict]:
        feed_url = site["selector"].get("url", site["url"])
        feed = feedparser.parse(
            feed_url,
            agent="Mozilla/5.0 (compatible; NewsAggregator/1.0)"
        )
        status = feed.get("status", "N/A")
        bozo = feed.get("bozo", False)
        entries_count = len(feed.get("entries", []))
        log.info(f"RSS [{site['name']}] url={feed_url} status={status} bozo={bozo} entries={entries_count}")
        if bozo:
            log.warning(f"RSS [{site['name']}] bozo_exception={feed.get('bozo_exception')}")
        items = []
        for entry in feed.get("entries", []):
            published_at = None
            published_parsed = entry.get("published_parsed")
            if published_parsed:
                published_at = datetime(*published_parsed[:6], tzinfo=timezone.utc).isoformat()
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary") or None,
                "published_at": published_at,
            })
        return items
