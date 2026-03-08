import logging
from db import SupabaseClient
from notifier import FCMNotifier
from scrapers.rss import RssScraper
from scrapers.html import HtmlScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def get_scraper(selector: dict):
    if selector.get("type") == "rss":
        return RssScraper()
    return HtmlScraper()


def run_all(db: SupabaseClient = None, notifier: FCMNotifier = None):
    if db is None:
        db = SupabaseClient()

    sites = db.get_active_sites()
    log.info(f"Scraping {len(sites)} active sites")

    for site in sites:
        run_id = db.create_scrape_run(site["id"])
        try:
            scraper = get_scraper(site["selector"])
            items = scraper.run(site)
            items_new = db.upsert_items(items)
            log.info(f"[{site['name']}] found={len(items)}, new={items_new}")
            db.finish_scrape_run(run_id, status="success", items_found=len(items), items_new=items_new)
        except Exception as e:
            log.error(f"[{site['name']}] FAILED: {e}")
            db.finish_scrape_run(run_id, status="failed", error_msg=str(e))

    # 알림 발송
    new_items_with_subs = db.get_new_items_with_subscribers()
    if not new_items_with_subs:
        log.info("No new items to notify")
        return

    log.info(f"Sending {len(new_items_with_subs)} notifications")
    if notifier is None:
        notifier = FCMNotifier()
    notif_logs = []
    item_ids_to_mark = []

    for row in new_items_with_subs:
        result = notifier.send_one(
            token=row["fcm_token"],
            title=f"[{row['site_name']}] {row['item_title']}",
            body="새 글이 올라왔습니다",
            link=row["item_link"]
        )
        notif_logs.append({
            "item_id": row["item_id"],
            "token_id": row["token_id"],
            "status": result["status"],
            "error_msg": result.get("error_msg")
        })
        item_ids_to_mark.append(row["item_id"])

    db.log_notifications(notif_logs)
    db.mark_items_not_new(list(set(item_ids_to_mark)))


if __name__ == "__main__":
    run_all()
