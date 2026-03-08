from abc import ABC, abstractmethod


class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, site: dict) -> list[dict]:
        """Scrape the site and return raw items (without site_id)."""
        pass

    def run(self, site: dict) -> list[dict]:
        """Call scrape(), inject site_id, filter empty titles."""
        raw = self.scrape(site)
        items = []
        for item in raw:
            if not item.get("title"):
                continue
            item["site_id"] = site["id"]
            items.append(item)
        return items
