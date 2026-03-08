import pytest
from unittest.mock import MagicMock, patch


RSS_SITE = {
    "id": "s1", "name": "GeekNews", "url": "u",
    "selector": {"type": "rss", "url": "u/rss"}, "category": "tech"
}
HTML_SITE = {
    "id": "s2", "name": "Test HTML", "url": "u2",
    "selector": {"type": "html", "container": ".item", "title": "a", "link": "a@href"},
    "category": "general"
}


def test_run_all_scrapes_all_active_sites():
    mock_db = MagicMock()
    mock_db.get_active_sites.return_value = [RSS_SITE, HTML_SITE]
    mock_db.create_scrape_run.return_value = "run-1"
    mock_db.upsert_items.return_value = 2
    mock_db.get_new_items_with_subscribers.return_value = []

    with patch("main.RssScraper") as MockRss, patch("main.HtmlScraper") as MockHtml:
        MockRss.return_value.run.return_value = [{"site_id": "s1", "title": "A", "link": "l1"}]
        MockHtml.return_value.run.return_value = [{"site_id": "s2", "title": "B", "link": "l2"}]
        from main import run_all
        run_all(db=mock_db, notifier=None)

    assert mock_db.create_scrape_run.call_count == 2
    assert mock_db.finish_scrape_run.call_count == 2


def test_run_all_sends_notifications_for_new_items():
    mock_db = MagicMock()
    mock_db.get_active_sites.return_value = [RSS_SITE]
    mock_db.create_scrape_run.return_value = "run-1"
    mock_db.upsert_items.return_value = 1
    mock_db.get_new_items_with_subscribers.return_value = [
        {
            "item_id": "item-1",
            "item_title": "New Article",
            "item_link": "https://example.com/1",
            "site_name": "GeekNews",
            "token_id": "tok-1",
            "fcm_token": "device-token-abc"
        }
    ]

    mock_notifier = MagicMock()
    mock_notifier.send_one.return_value = {"status": "sent"}

    with patch("main.RssScraper") as MockRss:
        MockRss.return_value.run.return_value = [{"site_id": "s1", "title": "New Article", "link": "https://example.com/1"}]
        from main import run_all
        run_all(db=mock_db, notifier=mock_notifier)

    mock_notifier.send_one.assert_called_once()
    mock_db.log_notifications.assert_called_once()
    mock_db.mark_items_not_new.assert_called_once_with(["item-1"])


def test_run_all_handles_scraper_exception():
    mock_db = MagicMock()
    mock_db.get_active_sites.return_value = [RSS_SITE]
    mock_db.create_scrape_run.return_value = "run-1"
    mock_db.get_new_items_with_subscribers.return_value = []

    with patch("main.RssScraper") as MockRss:
        MockRss.return_value.run.side_effect = Exception("Network error")
        from main import run_all
        run_all(db=mock_db, notifier=None)

    call_kwargs = mock_db.finish_scrape_run.call_args[1]
    assert call_kwargs["status"] == "failed"
    assert "Network error" in call_kwargs["error_msg"]
