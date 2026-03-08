# News Aggregator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Python 스크래퍼 + React(Vite) + Supabase + FCM + GitHub Actions로 구성된 뉴스 애그리게이터 모노레포를 구축한다.

**Architecture:** GitHub Actions가 매시간 Python 스크래퍼를 실행하여 Supabase에 새 글을 저장하고 FCM으로 알림을 발송한다. React PWA는 GitHub Pages에 배포되어 Supabase에서 피드를 조회한다.

**Tech Stack:** Python 3.11, requests, BeautifulSoup4, feedparser, supabase-py, google-auth / React 18, Vite, Tailwind CSS, shadcn/ui, Firebase JS SDK, supabase-js / GitHub Actions, GitHub Pages, Supabase PostgreSQL, FCM HTTP v1 API

---

## Prerequisites (사전 준비 — 코드 작성 전 수동 설정)

```
1. Supabase 프로젝트 생성 → URL, anon key, service_role key 메모
2. Firebase 프로젝트 생성 → FCM 활성화, VAPID key 생성, 서비스 계정 JSON 다운로드
3. GitHub 레포 생성 후 아래 Secrets 등록:
   SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY
   FCM_PROJECT_ID / FCM_SERVICE_ACCOUNT_JSON
4. GitHub Pages 설정: Settings → Pages → Source: GitHub Actions
```

---

## Task 1: 모노레포 디렉토리 scaffold

**Files:**
- Create: `scraper/requirements.txt`
- Create: `scraper/scrapers/__init__.py`
- Create: `scraper/tests/__init__.py`
- Create: `.gitignore`

**Step 1: 디렉토리 생성**

```bash
mkdir -p scraper/scrapers scraper/tests frontend .github/workflows
touch scraper/__init__.py scraper/scrapers/__init__.py scraper/tests/__init__.py
```

**Step 2: `scraper/requirements.txt` 작성**

```
requests==2.31.0
beautifulsoup4==4.12.3
feedparser==6.0.11
supabase==2.4.0
google-auth==2.28.0
google-auth-httplib2==0.2.0
python-dotenv==1.0.1
pytest==8.1.1
pytest-mock==3.14.0
responses==0.25.0
```

**Step 3: `.gitignore` 작성**

```
# Python
__pycache__/
*.py[cod]
.env
.venv/
venv/

# Node
node_modules/
dist/
.env.local
.env.*.local

# IDE
.idea/
*.iml
.DS_Store
```

**Step 4: 커밋**

```bash
git add scraper/ .github/ frontend/ .gitignore
git commit -m "chore: scaffold monorepo directory structure"
```

---

## Task 2: Supabase 스키마 마이그레이션

**Files:**
- Create: `supabase/migrations/001_initial_schema.sql`
- Create: `supabase/migrations/002_rls_policies.sql`
- Create: `supabase/seed.sql`

**Step 1: `supabase/migrations/001_initial_schema.sql` 작성**

```sql
-- sites
CREATE TABLE sites (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name            text UNIQUE NOT NULL,
  url             text NOT NULL,
  selector        jsonb NOT NULL,
  category        text NOT NULL DEFAULT 'general',
  cron_expr       text DEFAULT '0 */6 * * *',
  is_active       boolean DEFAULT true,
  last_scraped_at timestamptz,
  created_at      timestamptz DEFAULT now()
);

-- items
CREATE TABLE items (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id       uuid NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  title         text NOT NULL,
  link          text UNIQUE NOT NULL,
  summary       text,
  image_url     text,
  metadata      jsonb,
  published_at  timestamptz,
  scraped_at    timestamptz DEFAULT now(),
  is_new        boolean DEFAULT true
);
CREATE INDEX idx_items_site_id ON items(site_id);
CREATE INDEX idx_items_scraped_at ON items(scraped_at DESC);
CREATE INDEX idx_items_is_new ON items(is_new) WHERE is_new = true;

-- fcm_tokens
CREATE TABLE fcm_tokens (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token        text UNIQUE NOT NULL,
  user_id      uuid,
  device_name  text,
  is_active    boolean DEFAULT true,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

-- subscriptions
CREATE TABLE subscriptions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token_id    uuid NOT NULL REFERENCES fcm_tokens(id) ON DELETE CASCADE,
  site_id     uuid NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  category    text,
  is_muted    boolean DEFAULT false,
  created_at  timestamptz DEFAULT now(),
  UNIQUE(token_id, site_id, category)
);
CREATE INDEX idx_subscriptions_token_id ON subscriptions(token_id);
CREATE INDEX idx_subscriptions_site_id ON subscriptions(site_id);

-- notification_log
CREATE TABLE notification_log (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id     uuid NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  token_id    uuid NOT NULL REFERENCES fcm_tokens(id) ON DELETE CASCADE,
  status      text NOT NULL DEFAULT 'pending',
  error_msg   text,
  sent_at     timestamptz DEFAULT now()
);
CREATE INDEX idx_notification_log_item_id ON notification_log(item_id);
CREATE INDEX idx_notification_log_status ON notification_log(status) WHERE status = 'pending';

-- scrape_runs
CREATE TABLE scrape_runs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id      uuid NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  status       text NOT NULL DEFAULT 'running',
  items_found  int DEFAULT 0,
  items_new    int DEFAULT 0,
  error_msg    text,
  started_at   timestamptz DEFAULT now(),
  finished_at  timestamptz
);
CREATE INDEX idx_scrape_runs_site_id ON scrape_runs(site_id);
CREATE INDEX idx_scrape_runs_started_at ON scrape_runs(started_at DESC);

-- user_interactions
CREATE TABLE user_interactions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token_id    uuid NOT NULL REFERENCES fcm_tokens(id) ON DELETE CASCADE,
  item_id     uuid NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  action      text NOT NULL,
  created_at  timestamptz DEFAULT now(),
  UNIQUE(token_id, item_id, action)
);
CREATE INDEX idx_user_interactions_token_item ON user_interactions(token_id, item_id);
CREATE INDEX idx_user_interactions_bookmark ON user_interactions(token_id, action) WHERE action = 'bookmark';
```

**Step 2: `supabase/migrations/002_rls_policies.sql` 작성**

```sql
ALTER TABLE sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE fcm_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE scrape_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_interactions ENABLE ROW LEVEL SECURITY;

-- sites: anon read (active only)
CREATE POLICY "sites_anon_read" ON sites FOR SELECT TO anon
  USING (is_active = true);

-- items: anon read
CREATE POLICY "items_anon_read" ON items FOR SELECT TO anon USING (true);

-- fcm_tokens: anon insert + update own
CREATE POLICY "fcm_tokens_anon_insert" ON fcm_tokens FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "fcm_tokens_anon_update" ON fcm_tokens FOR UPDATE TO anon
  USING (token = current_setting('request.jwt.claims', true)::jsonb->>'fcm_token');

-- subscriptions: anon full access own rows
CREATE POLICY "subscriptions_anon" ON subscriptions FOR ALL TO anon
  USING (token_id IN (SELECT id FROM fcm_tokens WHERE token = current_setting('request.jwt.claims', true)::jsonb->>'fcm_token'));

-- user_interactions: anon access own rows
CREATE POLICY "user_interactions_anon" ON user_interactions FOR ALL TO anon
  USING (token_id IN (SELECT id FROM fcm_tokens WHERE token = current_setting('request.jwt.claims', true)::jsonb->>'fcm_token'));

-- scrape_runs: anon read (모니터링)
CREATE POLICY "scrape_runs_anon_read" ON scrape_runs FOR SELECT TO anon USING (true);

-- notification_log: no anon access
-- (service_role bypasses RLS automatically)
```

> **참고:** RLS에서 token_id 본인 판별은 API 헤더 기반으로 단순화. 실제로는 Supabase Edge Function 또는 미들웨어로 token_id를 주입하는 패턴을 쓰거나, 프론트에서 token을 직접 WHERE 조건에 넣어 필터링하는 방식이 현실적. 우선 service_role로 쓰기, anon으로 읽기 분리를 기본으로 가져가고 세부 RLS는 배포 후 조정.

**Step 3: `supabase/seed.sql` — 초기 사이트 데이터**

```sql
INSERT INTO sites (name, url, selector, category, cron_expr) VALUES
(
  'GeekNews',
  'https://news.hada.io',
  '{"type": "rss", "url": "https://news.hada.io/rss"}',
  'tech',
  '0 * * * *'
),
(
  'Hacker News',
  'https://news.ycombinator.com',
  '{"type": "rss", "url": "https://news.ycombinator.com/rss"}',
  'tech',
  '0 * * * *'
),
(
  '네이버 금융뉴스',
  'https://finance.naver.com',
  '{"type": "html", "container": ".articleSubject", "title": "a", "link": "a@href", "base_url": "https://finance.naver.com"}',
  'finance',
  '0 * * * *'
);
```

**Step 4: Supabase 대시보드에서 SQL 실행**

Supabase 대시보드 → SQL Editor에서 001, 002, seed.sql 순서대로 실행.

**Step 5: 커밋**

```bash
git add supabase/
git commit -m "feat: add supabase schema migrations and seed data"
```

---

## Task 3: Python DB 클라이언트 (`scraper/db.py`)

**Files:**
- Create: `scraper/db.py`
- Create: `scraper/tests/test_db.py`

**Step 1: `scraper/tests/test_db.py` — 실패하는 테스트 작성**

```python
import pytest
from unittest.mock import MagicMock, patch


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


def test_create_scrape_run(mock_supabase):
    from db import SupabaseClient
    client = SupabaseClient(supabase_client=mock_supabase)
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "run-id", "site_id": "abc", "status": "running"}
    ]
    run_id = client.create_scrape_run("abc")
    assert run_id == "run-id"


def test_finish_scrape_run(mock_supabase):
    from db import SupabaseClient
    client = SupabaseClient(supabase_client=mock_supabase)
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    # Should not raise
    client.finish_scrape_run("run-id", status="success", items_found=10, items_new=3)


@pytest.fixture
def mock_supabase():
    return MagicMock()
```

**Step 2: 테스트 실패 확인**

```bash
cd scraper && python -m pytest tests/test_db.py -v
```
Expected: `ModuleNotFoundError: No module named 'db'`

**Step 3: `scraper/db.py` 구현**

```python
import os
from supabase import create_client, Client
from datetime import datetime, timezone


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
        """Insert items, ignore duplicates (link is UNIQUE). Returns count of inserted rows."""
        if not items:
            return 0
        res = self.sb.table("items").upsert(items, on_conflict="link", ignore_duplicates=True).execute()
        return len(res.data)

    def get_new_items_with_subscribers(self) -> list[dict]:
        """새 아이템과 구독자 토큰을 JOIN하여 반환"""
        res = self.sb.rpc("get_new_items_with_subscribers").execute()
        return res.data

    def create_scrape_run(self, site_id: str) -> str:
        res = self.sb.table("scrape_runs").insert({
            "site_id": site_id,
            "status": "running"
        }).execute()
        return res.data[0]["id"]

    def finish_scrape_run(self, run_id: str, status: str, items_found: int = 0, items_new: int = 0, error_msg: str = None):
        update = {
            "status": status,
            "items_found": items_found,
            "items_new": items_new,
            "finished_at": datetime.now(timezone.utc).isoformat()
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
```

**Step 4: Supabase RPC 함수 추가 (대시보드 SQL Editor)**

```sql
CREATE OR REPLACE FUNCTION get_new_items_with_subscribers()
RETURNS TABLE (
  item_id uuid,
  item_title text,
  item_link text,
  site_name text,
  token_id uuid,
  fcm_token text
)
LANGUAGE sql SECURITY DEFINER AS $$
  SELECT
    i.id AS item_id,
    i.title AS item_title,
    i.link AS item_link,
    s.name AS site_name,
    ft.id AS token_id,
    ft.token AS fcm_token
  FROM items i
  JOIN sites s ON s.id = i.site_id
  JOIN subscriptions sub ON sub.site_id = i.site_id
    AND sub.is_muted = false
  JOIN fcm_tokens ft ON ft.id = sub.token_id
    AND ft.is_active = true
  WHERE i.is_new = true
    AND NOT EXISTS (
      SELECT 1 FROM notification_log nl
      WHERE nl.item_id = i.id AND nl.token_id = ft.id
    );
$$;
```

**Step 5: 테스트 통과 확인**

```bash
cd scraper && python -m pytest tests/test_db.py -v
```
Expected: 4 passed

**Step 6: 커밋**

```bash
git add scraper/db.py scraper/tests/test_db.py
git commit -m "feat: add Supabase DB client with scrape run tracking"
```

---

## Task 4: BaseScraper 추상 클래스

**Files:**
- Create: `scraper/scrapers/base.py`
- Create: `scraper/tests/test_base_scraper.py`

**Step 1: `scraper/tests/test_base_scraper.py` 작성**

```python
import pytest
from scrapers.base import BaseScraper


class ConcreteScraper(BaseScraper):
    def scrape(self, site: dict) -> list[dict]:
        return [{"title": "Test", "link": "https://example.com"}]


def test_scraper_returns_items_with_site_id():
    site = {"id": "site-123", "name": "Test Site", "url": "https://example.com",
            "selector": {}}
    scraper = ConcreteScraper()
    items = scraper.run(site)
    assert all("site_id" in item for item in items)
    assert items[0]["site_id"] == "site-123"


def test_scraper_filters_empty_titles():
    class EmptyTitleScraper(BaseScraper):
        def scrape(self, site):
            return [
                {"title": "Valid", "link": "https://a.com"},
                {"title": "", "link": "https://b.com"},
                {"title": None, "link": "https://c.com"},
            ]
    scraper = EmptyTitleScraper()
    items = scraper.run({"id": "s1", "name": "x", "url": "u", "selector": {}})
    assert len(items) == 1
    assert items[0]["title"] == "Valid"
```

**Step 2: 테스트 실패 확인**

```bash
cd scraper && python -m pytest tests/test_base_scraper.py -v
```
Expected: `ImportError`

**Step 3: `scraper/scrapers/base.py` 구현**

```python
from abc import ABC, abstractmethod


class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, site: dict) -> list[dict]:
        """사이트 설정을 받아 아이템 list 반환. site_id는 없어도 됨 (run()에서 주입)."""
        pass

    def run(self, site: dict) -> list[dict]:
        """scrape() 호출 후 site_id 주입 + 빈 title 필터링."""
        raw = self.scrape(site)
        items = []
        for item in raw:
            if not item.get("title"):
                continue
            item["site_id"] = site["id"]
            items.append(item)
        return items
```

**Step 4: 테스트 통과 확인**

```bash
cd scraper && python -m pytest tests/test_base_scraper.py -v
```
Expected: 2 passed

**Step 5: 커밋**

```bash
git add scraper/scrapers/base.py scraper/tests/test_base_scraper.py
git commit -m "feat: add BaseScraper abstract class"
```

---

## Task 5: RSS 스크래퍼

**Files:**
- Create: `scraper/scrapers/rss.py`
- Create: `scraper/tests/test_rss_scraper.py`

**Step 1: `scraper/tests/test_rss_scraper.py` 작성**

```python
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
```

**Step 2: 테스트 실패 확인**

```bash
cd scraper && python -m pytest tests/test_rss_scraper.py -v
```

**Step 3: `scraper/scrapers/rss.py` 구현**

```python
import feedparser
from datetime import datetime, timezone
from scrapers.base import BaseScraper


class RssScraper(BaseScraper):
    def scrape(self, site: dict) -> list[dict]:
        feed_url = site["selector"].get("url", site["url"])
        feed = feedparser.parse(feed_url)
        items = []
        for entry in feed.entries:
            published_at = None
            if entry.get("published_parsed"):
                published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
            items.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", "") or None,
                "published_at": published_at,
            })
        return items
```

**Step 4: 테스트 통과 확인**

```bash
cd scraper && python -m pytest tests/test_rss_scraper.py -v
```
Expected: 2 passed

**Step 5: 커밋**

```bash
git add scraper/scrapers/rss.py scraper/tests/test_rss_scraper.py
git commit -m "feat: add RSS scraper using feedparser"
```

---

## Task 6: HTML 스크래퍼

**Files:**
- Create: `scraper/scrapers/html.py`
- Create: `scraper/tests/test_html_scraper.py`

**Step 1: `scraper/tests/test_html_scraper.py` 작성**

```python
import pytest
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
```

**Step 2: 테스트 실패 확인**

```bash
cd scraper && python -m pytest tests/test_html_scraper.py -v
```

**Step 3: `scraper/scrapers/html.py` 구현**

```python
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
```

**Step 4: 테스트 통과 확인**

```bash
cd scraper && python -m pytest tests/test_html_scraper.py -v
```
Expected: 2 passed

**Step 5: 커밋**

```bash
git add scraper/scrapers/html.py scraper/tests/test_html_scraper.py
git commit -m "feat: add HTML scraper using BeautifulSoup"
```

---

## Task 7: FCM 알림 발송 (`scraper/notifier.py`)

**Files:**
- Create: `scraper/notifier.py`
- Create: `scraper/tests/test_notifier.py`

**Step 1: `scraper/tests/test_notifier.py` 작성**

```python
import pytest
from unittest.mock import patch, MagicMock
from notifier import FCMNotifier


def test_send_notification_returns_success():
    notifier = FCMNotifier(project_id="test-project", credentials=MagicMock())
    with patch("notifier.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"name": "projects/test/messages/123"}
        result = notifier.send_one(
            token="device-token-abc",
            title="New Post",
            body="Check it out",
            link="https://example.com/post"
        )
    assert result["status"] == "sent"


def test_send_notification_handles_failure():
    notifier = FCMNotifier(project_id="test-project", credentials=MagicMock())
    with patch("notifier.requests.post") as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"error": {"message": "INVALID_ARGUMENT"}}
        result = notifier.send_one(
            token="bad-token",
            title="New Post",
            body="Check it out",
            link="https://example.com/post"
        )
    assert result["status"] == "failed"
    assert "INVALID_ARGUMENT" in result["error_msg"]
```

**Step 2: 테스트 실패 확인**

```bash
cd scraper && python -m pytest tests/test_notifier.py -v
```

**Step 3: `scraper/notifier.py` 구현**

```python
import json
import os
import requests
import google.auth.transport.requests
from google.oauth2 import service_account


class FCMNotifier:
    FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

    def __init__(self, project_id: str = None, credentials=None):
        self.project_id = project_id or os.environ["FCM_PROJECT_ID"]
        if credentials:
            self.credentials = credentials
        else:
            service_account_info = json.loads(os.environ["FCM_SERVICE_ACCOUNT_JSON"])
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=[self.FCM_SCOPE]
            )

    def _get_access_token(self) -> str:
        req = google.auth.transport.requests.Request()
        self.credentials.refresh(req)
        return self.credentials.token

    def send_one(self, token: str, title: str, body: str, link: str) -> dict:
        url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        payload = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
                "webpush": {
                    "fcm_options": {"link": link}
                }
            }
        }
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json"
        }
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            return {"status": "sent"}
        else:
            error = res.json().get("error", {}).get("message", str(res.text))
            return {"status": "failed", "error_msg": error}

    def send_batch(self, notifications: list[dict]) -> list[dict]:
        """notifications: [{"token": ..., "title": ..., "body": ..., "link": ...}]"""
        return [self.send_one(**n) for n in notifications]
```

**Step 4: 테스트 통과 확인**

```bash
cd scraper && python -m pytest tests/test_notifier.py -v
```
Expected: 2 passed

**Step 5: 커밋**

```bash
git add scraper/notifier.py scraper/tests/test_notifier.py
git commit -m "feat: add FCM HTTP v1 notifier"
```

---

## Task 8: 스크래퍼 진입점 (`scraper/main.py`)

**Files:**
- Create: `scraper/main.py`
- Create: `scraper/tests/test_main.py`

**Step 1: `scraper/tests/test_main.py` 작성**

```python
import pytest
from unittest.mock import MagicMock, patch


def test_main_runs_all_active_sites():
    mock_db = MagicMock()
    mock_db.get_active_sites.return_value = [
        {"id": "s1", "name": "GeekNews", "url": "u", "selector": {"type": "rss", "url": "u/rss"}, "category": "tech"},
        {"id": "s2", "name": "Test HTML", "url": "u2", "selector": {"type": "html", "container": ".item", "title": "a", "link": "a@href"}, "category": "general"},
    ]
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
```

**Step 2: 테스트 실패 확인**

```bash
cd scraper && python -m pytest tests/test_main.py -v
```

**Step 3: `scraper/main.py` 구현**

```python
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
    if notifier is None:
        notifier = FCMNotifier()

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
```

**Step 4: 테스트 통과 확인**

```bash
cd scraper && python -m pytest tests/test_main.py -v
```
Expected: 1 passed

**Step 5: 전체 테스트 통과 확인**

```bash
cd scraper && python -m pytest -v
```
Expected: All passed

**Step 6: 커밋**

```bash
git add scraper/main.py scraper/tests/test_main.py
git commit -m "feat: add scraper orchestration main.py"
```

---

## Task 9: GitHub Actions 워크플로우

**Files:**
- Create: `.github/workflows/scrape.yml`
- Create: `.github/workflows/deploy.yml`

**Step 1: `.github/workflows/scrape.yml` 작성**

```yaml
name: Scrape

on:
  schedule:
    - cron: '0 * * * *'   # 매시간 정각
  workflow_dispatch:        # 수동 실행 가능

jobs:
  scrape:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: scraper

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: scraper/requirements.txt

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run scraper
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
          FCM_PROJECT_ID: ${{ secrets.FCM_PROJECT_ID }}
          FCM_SERVICE_ACCOUNT_JSON: ${{ secrets.FCM_SERVICE_ACCOUNT_JSON }}
        run: python main.py

      - name: Run tests
        run: python -m pytest -v
```

**Step 2: `.github/workflows/deploy.yml` 작성**

```yaml
name: Deploy

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Build
        env:
          VITE_SUPABASE_URL: ${{ secrets.VITE_SUPABASE_URL }}
          VITE_SUPABASE_ANON_KEY: ${{ secrets.VITE_SUPABASE_ANON_KEY }}
          VITE_FIREBASE_CONFIG: ${{ secrets.VITE_FIREBASE_CONFIG }}
          VITE_FIREBASE_VAPID_KEY: ${{ secrets.VITE_FIREBASE_VAPID_KEY }}
        run: npm run build

      - uses: actions/upload-pages-artifact@v3
        with:
          path: frontend/dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/deploy-pages@v4
        id: deployment
```

**Step 3: 커밋**

```bash
git add .github/workflows/
git commit -m "ci: add scrape cron and GitHub Pages deploy workflows"
```

---

## Task 10: 프론트엔드 Vite + Tailwind 설정

**Files:**
- Create: `frontend/` (Vite scaffold)

**Step 1: Vite 프로젝트 생성**

```bash
cd frontend
npm create vite@latest . -- --template react
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install @supabase/supabase-js firebase
npm install @shadcn/ui lucide-react clsx tailwind-merge
```

**Step 2: `frontend/vite.config.js` 수정**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',  // GitHub Pages 상대경로
})
```

**Step 3: `frontend/src/index.css` — Tailwind import**

```css
@import "tailwindcss";
```

**Step 4: 빌드 확인**

```bash
npm run build
```
Expected: `dist/` 생성, 에러 없음

**Step 5: 커밋**

```bash
git add frontend/
git commit -m "feat: scaffold React Vite frontend with Tailwind CSS"
```

---

## Task 11: 프론트엔드 라이브러리 초기화

**Files:**
- Create: `frontend/src/lib/supabase.js`
- Create: `frontend/src/lib/firebase.js`
- Create: `frontend/.env.example`

**Step 1: `frontend/.env.example` 작성**

```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_FIREBASE_CONFIG={"apiKey":"...","authDomain":"...","projectId":"...","storageBucket":"...","messagingSenderId":"...","appId":"..."}
VITE_FIREBASE_VAPID_KEY=your-vapid-key
```

**Step 2: `frontend/src/lib/supabase.js` 작성**

```js
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
)
```

**Step 3: `frontend/src/lib/firebase.js` 작성**

```js
import { initializeApp } from 'firebase/app'
import { getMessaging, getToken, onMessage } from 'firebase/messaging'

const firebaseConfig = JSON.parse(import.meta.env.VITE_FIREBASE_CONFIG)
const app = initializeApp(firebaseConfig)
export const messaging = getMessaging(app)

export async function requestFCMToken() {
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return null

  return getToken(messaging, {
    vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
    serviceWorkerRegistration: await navigator.serviceWorker.getRegistration('/sw.js')
  })
}

export { onMessage }
```

**Step 4: 커밋**

```bash
git add frontend/src/lib/ frontend/.env.example
git commit -m "feat: add Supabase and Firebase client initialization"
```

---

## Task 12: PWA 설정 (manifest + Service Worker)

**Files:**
- Create: `frontend/public/manifest.json`
- Create: `frontend/public/sw.js`

**Step 1: `frontend/public/manifest.json` 작성**

```json
{
  "name": "News Aggregator",
  "short_name": "News",
  "description": "다양한 사이트의 최신 뉴스를 한 곳에서",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0f172a",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

> **참고:** icon-192.png, icon-512.png 파일을 `frontend/public/`에 추가해야 PWA 설치 가능.

**Step 2: `frontend/public/sw.js` — FCM Service Worker 작성**

```js
importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js')
importScripts('https://www.gstatic.com/firebasejs/10.8.0/firebase-messaging-compat.js')

// Firebase config는 빌드 시 환경변수를 sw.js에 주입하거나
// sw.js를 동적으로 생성하는 Vite 플러그인을 쓰거나,
// 아래처럼 하드코딩(빌드 스크립트로 치환) 방식 중 선택.
// 여기서는 빌드 후 dist/sw.js에 환경변수를 치환하는 방식 사용.

firebase.initializeApp(JSON.parse('__FIREBASE_CONFIG__'))

const messaging = firebase.messaging()

messaging.onBackgroundMessage((payload) => {
  const { title, body } = payload.notification
  self.registration.showNotification(title, {
    body,
    icon: '/icon-192.png',
    data: { link: payload.fcmOptions?.link }
  })
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const link = event.notification.data?.link
  if (link) {
    event.waitUntil(clients.openWindow(link))
  }
})
```

**Step 3: `package.json`에 sw 환경변수 치환 스크립트 추가**

`frontend/package.json`의 scripts에 추가:

```json
"build": "vite build && node scripts/inject-sw-config.js"
```

**Step 4: `frontend/scripts/inject-sw-config.js` 작성**

```js
import { readFileSync, writeFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const swPath = resolve(__dirname, '../dist/sw.js')
let content = readFileSync(swPath, 'utf-8')
content = content.replace('__FIREBASE_CONFIG__', process.env.VITE_FIREBASE_CONFIG || '{}')
writeFileSync(swPath, content)
console.log('sw.js: Firebase config injected')
```

**Step 5: `frontend/index.html` — manifest 링크 + SW 등록**

`index.html` `<head>`에 추가:
```html
<link rel="manifest" href="/manifest.json" />
```

**Step 6: `frontend/src/main.jsx` — SW 등록 코드 추가**

```jsx
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(console.error)
}
```

**Step 7: 커밋**

```bash
git add frontend/public/ frontend/scripts/ frontend/index.html frontend/src/main.jsx frontend/package.json
git commit -m "feat: add PWA manifest and FCM service worker"
```

---

## Task 13: useFeed 훅

**Files:**
- Create: `frontend/src/hooks/useFeed.js`

**Step 1: `frontend/src/hooks/useFeed.js` 작성**

```js
import { useState, useEffect, useCallback } from 'react'
import { supabase } from '../lib/supabase'

export function useFeed({ siteId = null, limit = 50 } = {}) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchFeed = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      let query = supabase
        .from('items')
        .select('*, sites(name, category)')
        .order('scraped_at', { ascending: false })
        .limit(limit)

      if (siteId) {
        query = query.eq('site_id', siteId)
      }

      const { data, error } = await query
      if (error) throw error
      setItems(data || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [siteId, limit])

  useEffect(() => { fetchFeed() }, [fetchFeed])

  return { items, loading, error, refetch: fetchFeed }
}
```

**Step 2: 커밋**

```bash
git add frontend/src/hooks/useFeed.js
git commit -m "feat: add useFeed hook for Supabase data fetching"
```

---

## Task 14: useFCM 훅

**Files:**
- Create: `frontend/src/hooks/useFCM.js`

**Step 1: `frontend/src/hooks/useFCM.js` 작성**

```js
import { useState, useEffect } from 'react'
import { requestFCMToken, onMessage } from '../lib/firebase'
import { supabase } from '../lib/supabase'

const TOKEN_KEY = 'fcm_token_id'

export function useFCM() {
  const [tokenId, setTokenId] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [permissionState, setPermissionState] = useState(Notification.permission)

  async function registerToken() {
    const fcmToken = await requestFCMToken()
    if (!fcmToken) return

    // Supabase에 토큰 등록 (중복이면 무시)
    const { data, error } = await supabase
      .from('fcm_tokens')
      .upsert({ token: fcmToken }, { onConflict: 'token' })
      .select('id')
      .single()

    if (!error && data) {
      localStorage.setItem(TOKEN_KEY, data.id)
      setTokenId(data.id)
    }
    setPermissionState(Notification.permission)
  }

  useEffect(() => {
    // 포그라운드 메시지 처리
    const unsub = onMessage(messaging => {
      // 포그라운드에서는 직접 알림 표시 안 함 (sw가 백그라운드 처리)
      console.log('Foreground FCM message received')
    })
    return unsub
  }, [])

  return { tokenId, permissionState, registerToken }
}
```

**Step 2: 커밋**

```bash
git add frontend/src/hooks/useFCM.js
git commit -m "feat: add useFCM hook for token registration"
```

---

## Task 15: UI 컴포넌트

**Files:**
- Create: `frontend/src/components/FeedCard.jsx`
- Create: `frontend/src/components/FilterBar.jsx`
- Create: `frontend/src/components/NotifBanner.jsx`

**Step 1: `frontend/src/components/FeedCard.jsx` 작성**

```jsx
import { formatDistanceToNow } from 'date-fns'
import { ko } from 'date-fns/locale'

export function FeedCard({ item }) {
  const timeAgo = formatDistanceToNow(
    new Date(item.scraped_at),
    { addSuffix: true, locale: ko }
  )

  return (
    <a
      href={item.link}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
          {item.sites?.name ?? ''}
        </span>
        <span className="text-xs text-slate-400">{timeAgo}</span>
      </div>
      <p className="text-sm font-semibold text-slate-800 line-clamp-2">{item.title}</p>
      {item.summary && (
        <p className="mt-1 text-xs text-slate-500 line-clamp-2">{item.summary}</p>
      )}
    </a>
  )
}
```

> `date-fns` 설치 필요: `npm install date-fns`

**Step 2: `frontend/src/components/FilterBar.jsx` 작성**

```jsx
export function FilterBar({ sites, selectedId, onSelect }) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
      <button
        onClick={() => onSelect(null)}
        className={`shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
          selectedId === null
            ? 'bg-slate-800 text-white'
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
        }`}
      >
        전체
      </button>
      {sites.map(site => (
        <button
          key={site.id}
          onClick={() => onSelect(site.id)}
          className={`shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            selectedId === site.id
              ? 'bg-slate-800 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          {site.name}
        </button>
      ))}
    </div>
  )
}
```

**Step 3: `frontend/src/components/NotifBanner.jsx` 작성**

```jsx
export function NotifBanner({ permissionState, onEnable }) {
  if (permissionState === 'granted' || permissionState === 'denied') return null

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl bg-blue-50 border border-blue-200 px-4 py-3">
      <p className="text-sm text-blue-800">새 글 알림을 받으시겠어요?</p>
      <button
        onClick={onEnable}
        className="shrink-0 text-sm font-medium text-blue-600 hover:text-blue-800"
      >
        알림 허용
      </button>
    </div>
  )
}
```

**Step 4: 커밋**

```bash
cd frontend && npm install date-fns
git add frontend/src/components/ frontend/package.json frontend/package-lock.json
git commit -m "feat: add FeedCard, FilterBar, NotifBanner components"
```

---

## Task 16: App.jsx 메인 화면 조립

**Files:**
- Modify: `frontend/src/App.jsx`

**Step 1: `frontend/src/App.jsx` 작성**

```jsx
import { useState, useEffect } from 'react'
import { supabase } from './lib/supabase'
import { useFeed } from './hooks/useFeed'
import { useFCM } from './hooks/useFCM'
import { FeedCard } from './components/FeedCard'
import { FilterBar } from './components/FilterBar'
import { NotifBanner } from './components/NotifBanner'

export default function App() {
  const [sites, setSites] = useState([])
  const [selectedSiteId, setSelectedSiteId] = useState(null)
  const { items, loading, error, refetch } = useFeed({ siteId: selectedSiteId })
  const { permissionState, registerToken } = useFCM()

  useEffect(() => {
    supabase.from('sites').select('id, name, category').eq('is_active', true)
      .then(({ data }) => setSites(data || []))
  }, [])

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-10 bg-white border-b border-slate-200 px-4 py-3">
        <h1 className="text-lg font-bold text-slate-900 mb-3">News Feed</h1>
        <FilterBar sites={sites} selectedId={selectedSiteId} onSelect={setSelectedSiteId} />
      </header>

      <main className="max-w-2xl mx-auto px-4 py-4 space-y-3">
        <NotifBanner permissionState={permissionState} onEnable={registerToken} />

        {loading && (
          <p className="text-center text-slate-400 py-8">불러오는 중...</p>
        )}
        {error && (
          <p className="text-center text-red-500 py-8">{error}</p>
        )}
        {!loading && items.map(item => (
          <FeedCard key={item.id} item={item} />
        ))}
        {!loading && items.length === 0 && (
          <p className="text-center text-slate-400 py-8">아직 아이템이 없습니다.</p>
        )}
      </main>
    </div>
  )
}
```

**Step 2: 로컬 빌드 확인**

```bash
cd frontend && npm run dev
```
브라우저에서 `http://localhost:5173` 확인 — 에러 없이 렌더링되어야 함

**Step 3: 커밋**

```bash
git add frontend/src/App.jsx
git commit -m "feat: assemble main feed UI with filter and notification banner"
```

---

## Task 17: 최종 검증 및 정리

**Step 1: 전체 스크래퍼 테스트**

```bash
cd scraper && python -m pytest -v
```
Expected: All passed

**Step 2: 프론트엔드 프로덕션 빌드**

```bash
cd frontend && npm run build
```
Expected: `dist/` 생성, 에러 없음

**Step 3: GitHub Secrets 등록 확인 체크리스트**

```
☐ SUPABASE_URL
☐ SUPABASE_SERVICE_ROLE_KEY
☐ FCM_PROJECT_ID
☐ FCM_SERVICE_ACCOUNT_JSON
☐ VITE_SUPABASE_URL
☐ VITE_SUPABASE_ANON_KEY
☐ VITE_FIREBASE_CONFIG
☐ VITE_FIREBASE_VAPID_KEY
```

**Step 4: main 브랜치 push → GitHub Actions 확인**

```bash
git push origin main
```

- `deploy.yml` → GitHub Pages 배포 확인
- `scrape.yml` → Actions 탭에서 수동 실행(`workflow_dispatch`)으로 첫 스크래핑 테스트

**Step 5: 최종 커밋**

```bash
git add .
git commit -m "chore: final cleanup and verification"
git push origin main
```
