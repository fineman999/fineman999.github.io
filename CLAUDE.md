# News Aggregator — CLAUDE.md

## 프로젝트 개요

GitHub Pages 기반 뉴스 애그리게이터. Python 스크래퍼가 매시간 여러 사이트를 수집하여 Supabase에 저장하고, FCM으로 푸시 알림을 발송한다. React PWA로 피드를 보여준다.

```
GitHub Actions (cron 1h)
  → scraper/main.py
  → Supabase (PostgreSQL)
  → FCM 푸시 알림

GitHub Pages (React PWA)
  → Supabase에서 피드 조회
```

- **레포**: https://github.com/fineman999/fineman999.github.io
- **배포 URL**: https://fineman999.github.io
- **Supabase**: sites 테이블이 Single Source of Truth (sites.yaml은 초기 시드용)

---

## 새 사이트 추가하는 법

### 1단계: 실제 HTML 구조 확인

```bash
python3 -c "
import requests
from bs4 import BeautifulSoup
res = requests.get('https://대상사이트.com', headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
soup = BeautifulSoup(res.text, 'html.parser')
# 클래스명 탐색
classes = set()
for tag in soup.find_all(True):
    for c in (tag.get('class') or []):
        classes.add((tag.name, c))
print(classes)
"
```

### 2단계: 셀렉터 검증

```bash
python3 -c "
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
BASE = 'https://대상사이트.com'
res = requests.get(BASE, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
soup = BeautifulSoup(res.text, 'html.parser')
for row in soup.select('컨테이너셀렉터')[:5]:
    title_el = row.select_one('제목셀렉터')
    link_el = row.select_one('링크셀렉터')
    print(title_el.get_text(strip=True)[:60] if title_el else None)
    print(urljoin(BASE, link_el.get('href','')) if link_el else None)
    print()
"
```

### 3단계: Supabase SQL Editor에서 INSERT

**RSS 사이트:**
```sql
INSERT INTO sites (name, url, selector, category, cron_expr) VALUES (
  '사이트명',
  'https://example.com',
  '{"type": "rss", "url": "https://example.com/rss"}',
  'tech',   -- tech | finance | general
  '0 * * * *'
);
```

**HTML 사이트:**
```sql
INSERT INTO sites (name, url, selector, category, cron_expr) VALUES (
  '사이트명',
  'https://example.com',
  '{
    "type": "html",
    "container": "div.item",
    "title": "a.title",
    "link": "a.title@href",
    "base_url": "https://example.com"
  }',
  'general',
  '0 * * * *'
);
```

**셀렉터 수정:**
```sql
UPDATE sites
SET selector = '{ ... }'::jsonb
WHERE name = '사이트명';
```

### 4단계: 즉시 테스트

GitHub → Actions → **Scrape** → **"Run workflow"**

---

## selector JSON 형식

| 필드 | 설명 | 예시 |
|---|---|---|
| `type` | `"rss"` 또는 `"html"` | `"html"` |
| `url` | RSS일 때 피드 URL | `"https://example.com/feed"` |
| `container` | 각 아이템 감싸는 요소 | `"div.topic_row"` |
| `title` | 제목 텍스트 요소 | `"div.topictitle a"` |
| `link` | 링크 요소 (`@href` 접미사) | `"a.title@href"` |
| `base_url` | 상대경로 링크 절대경로 변환용 | `"https://news.hada.io"` |

**link 셀렉터 특수 케이스:**
- `"a@href"` → 컨테이너 안의 첫 번째 `<a>` 태그의 href
- `"a.cls@href"` → `.cls` 클래스의 `<a>` 태그의 href
- `"div.info a[href^=topic]@href"` → 특정 패턴의 href를 가진 링크

---

## 등록된 사이트 목록

| 사이트 | 타입 | 카테고리 |
|---|---|---|
| GeekNews | html | tech |
| Hacker News | rss | tech |
| 네이버 금융뉴스 | html | finance |

> 최신 목록: Supabase → sites 테이블 확인

---

## 주요 커맨드

```bash
# 스크래퍼 전체 테스트
cd scraper && python3 -m pytest -v

# 셀렉터 디버그 (위 2단계 참고)
cd scraper && python3 -c "..."

# 로컬 스크래퍼 실행 (env 필요)
cd scraper && SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python3 main.py
```

---

## 파일 구조

```
scraper/
├── main.py           # 진입점 — DB에서 sites 읽고 스크래핑 오케스트레이션
├── db.py             # SupabaseClient — upsert, scrape_runs, 알림 로그
├── notifier.py       # FCMNotifier — HTTP v1 API 푸시 발송
├── scrapers/
│   ├── base.py       # BaseScraper ABC — run()이 site_id 주입 + 빈 title 필터
│   ├── rss.py        # feedparser 기반, selector.url에서 피드 파싱
│   └── html.py       # requests + BeautifulSoup, selector JSON 기반 파싱
└── requirements.txt  # 런타임 의존성 (supabase, httpx<0.28.0 포함)

supabase/
├── migrations/
│   ├── 001_initial_schema.sql   # 7개 테이블
│   ├── 002_rls_policies.sql     # RLS 정책
│   └── 003_rpc_functions.sql    # get_new_items_with_subscribers() RPC
└── seed.sql          # 초기 사이트 3개

frontend/
├── src/
│   ├── lib/supabase.js    # Supabase 클라이언트
│   ├── lib/firebase.js    # Firebase/FCM 초기화
│   ├── hooks/useFeed.js   # 피드 데이터 페치
│   ├── hooks/useFCM.js    # FCM 토큰 등록
│   └── components/
│       ├── FeedCard.jsx   # 아이템 카드
│       ├── FilterBar.jsx  # 사이트 필터
│       └── NotifBanner.jsx # 알림 권한 요청
└── public/
    ├── manifest.json  # PWA 매니페스트
    └── sw.js          # FCM 서비스 워커

.github/workflows/
├── scrape.yml   # cron 1h + workflow_dispatch
└── deploy.yml   # frontend/** 변경 시 GitHub Pages 배포
```

---

## GitHub Secrets

| Secret | 용도 |
|---|---|
| `SUPABASE_URL` | 스크래퍼용 Supabase URL |
| `SUPABASE_SERVICE_ROLE_KEY` | RLS 우회 관리자 키 |
| `FCM_PROJECT_ID` | Firebase 프로젝트 ID |
| `FCM_SERVICE_ACCOUNT_JSON` | FCM HTTP v1 서비스 계정 JSON (한 줄) |
| `VITE_SUPABASE_URL` | 프론트엔드용 Supabase URL |
| `VITE_SUPABASE_ANON_KEY` | 프론트엔드용 공개 키 (RLS로 보호) |
| `VITE_FIREBASE_CONFIG` | Firebase 앱 설정 JSON (한 줄) |
| `VITE_FIREBASE_VAPID_KEY` | Web Push VAPID 공개 키 |

---

## 알려진 이슈 / 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `Invalid API key` | SUPABASE_SERVICE_ROLE_KEY 오등록 | GitHub Secrets 재등록 |
| `proxy kwarg` 오류 | httpx 버전 충돌 | `httpx<0.28.0` 핀 (이미 적용됨) |
| `found=0, new=0` | 셀렉터 불일치 또는 봇 차단 | RSS 로그의 `status=` 확인 후 셀렉터 수정 |
| RPC 404 | Supabase에 함수 미생성 | `003_rpc_functions.sql` SQL Editor 실행 |
| 배포 안 됨 | GitHub Pages 소스 설정 미변경 | Settings → Pages → Source: GitHub Actions |
