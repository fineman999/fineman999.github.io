import pytest
from unittest.mock import MagicMock


def test_get_active_sites_returns_list(mock_supabase):
    from db import SupabaseClient
    client = SupabaseClient(supabase_client=mock_supabase)
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "abc", "name": "GeekNews", "url": "https://news.hada.io",
         "selector": {"type": "rss", "url": "https://news.hada.io/rss"},
         "category": "tech"}
    ]
    sites = client.get_active_sites()
    assert len(sites) == 1
    assert sites[0]["name"] == "GeekNews"


def test_upsert_items_returns_new_count(mock_supabase):
    from db import SupabaseClient
    client = SupabaseClient(supabase_client=mock_supabase)
    mock_supabase.table.return_value.upsert.return_value.execute.return_value.data = [
        {"id": "new-id", "title": "Test", "link": "https://example.com/1"}
    ]
    items = [{"site_id": "abc", "title": "Test", "link": "https://example.com/1"}]
    result = client.upsert_items(items)
    assert result == 1


def test_upsert_items_empty_returns_zero(mock_supabase):
    from db import SupabaseClient
    client = SupabaseClient(supabase_client=mock_supabase)
    result = client.upsert_items([])
    assert result == 0
    mock_supabase.table.assert_not_called()


def test_create_scrape_run(mock_supabase):
    from db import SupabaseClient
    client = SupabaseClient(supabase_client=mock_supabase)
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "run-id", "site_id": "abc", "status": "running"}
    ]
    run_id = client.create_scrape_run("abc")
    assert run_id == "run-id"


def test_finish_scrape_run_success(mock_supabase):
    from db import SupabaseClient
    client = SupabaseClient(supabase_client=mock_supabase)
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    # Should not raise
    client.finish_scrape_run("run-id", status="success", items_found=10, items_new=3)
    call_args = mock_supabase.table.return_value.update.call_args[0][0]
    assert call_args["status"] == "success"
    assert call_args["items_found"] == 10
    assert call_args["items_new"] == 3


def test_mark_items_not_new_skips_empty(mock_supabase):
    from db import SupabaseClient
    client = SupabaseClient(supabase_client=mock_supabase)
    client.mark_items_not_new([])
    mock_supabase.table.assert_not_called()


@pytest.fixture
def mock_supabase():
    return MagicMock()
