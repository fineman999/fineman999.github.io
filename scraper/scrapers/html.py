import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from scrapers.base import BaseScraper


class HtmlScraper(BaseScraper):
    def scrape(self, site: dict) -> list[dict]:
        sel = site["selector"]
        base_url = sel.get("base_url", site["url"])
        try:
            res = requests.get(site["url"], timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            res.raise_for_status()
        except requests.RequestException:
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        containers = soup.select(sel["container"])
        items = []
        for container in containers:
            title_el = container.select_one(sel["title"])
            title = title_el.get_text(strip=True) if title_el else ""

            link_sel = sel["link"]
            if "@href" in link_sel:
                tag = link_sel.replace("@href", "").strip() or "a"
                link_el = container.select_one(tag)
                raw_link = link_el["href"] if link_el and link_el.get("href") else ""
            else:
                link_el = container.select_one(link_sel)
                raw_link = link_el["href"] if link_el and link_el.get("href") else ""

            link = urljoin(base_url, raw_link) if raw_link else ""
            if title and link:
                items.append({"title": title, "link": link})
        return items
