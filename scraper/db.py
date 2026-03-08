import os
from datetime import datetime, timezone
from supabase import create_client


class SupabaseClient:
    def __init__(self, supabase_client=None):
        if supabase_client:
            self.sb = supabase_client
        else:
            url = os.environ["SUPABASE_URL"]
            key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
            self.sb = create_client(url, key)

    def get_active_sites(self) -> list[dict]:
        res = self.sb.table("sites").select("*").eq("is_active", True).execute()
        return res.data

    def upsert_items(self, items: list[dict]) -> int:
        """Insert items, ignore duplicates on link. Returns count of inserted rows."""
        if not items:
            return 0
        res = self.sb.table("items").upsert(items, on_conflict="link", ignore_duplicates=True).execute()
        return len(res.data)

    def get_new_items_with_subscribers(self) -> list[dict]:
        res = self.sb.rpc("get_new_items_with_subscribers").execute()
        return res.data or []

    def create_scrape_run(self, site_id: str) -> str:
        res = self.sb.table("scrape_runs").insert({
            "site_id": site_id,
            "status": "running"
        }).execute()
        return res.data[0]["id"]

    def finish_scrape_run(
        self,
        run_id: str,
        status: str,
        items_found: int = 0,
        items_new: int = 0,
        error_msg: str = None
    ):
        update = {
            "status": status,
            "items_found": items_found,
            "items_new": items_new,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        if error_msg:
            update["error_msg"] = error_msg
        self.sb.table("scrape_runs").update(update).eq("id", run_id).execute()

    def mark_items_not_new(self, item_ids: list[str]):
        if not item_ids:
            return
        self.sb.table("items").update({"is_new": False}).in_("id", item_ids).execute()

    def log_notifications(self, logs: list[dict]):
        """logs: [{"item_id": ..., "token_id": ..., "status": "sent"/"failed", "error_msg": ...}]"""
        if not logs:
            return
        self.sb.table("notification_log").insert(logs).execute()
