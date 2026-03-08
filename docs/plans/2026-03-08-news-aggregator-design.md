# News Aggregator — Design Document

**Date:** 2026-03-08
**Status:** Approved

---

## 프로젝트 개요

GitHub Pages 기반 뉴스/정보 애그리게이터. 다양한 사이트(GeekNews, 네이버 금융뉴스 등)를 스크래핑하여 한 곳에서 모아보고, 사이트별 FCM 푸시 알림을 받을 수 있는 서비스.

---

## 아키텍처

```
[GitHub Actions (cron)] → Python 스크래퍼 → Supabase DB 저장
                                            ↓
                              FCM 푸시 알림 발송 (새 글 감지 시)
                                            ↓
[GitHub Pages] ← React(Vite) + Tailwind ← Supabase에서 데이터 조회
```

- **스크래핑**: Python + BeautifulSoup, GitHub Actions cron (사이트별 주기 설정 가능)
- **프론트엔드**: React (Vite) + Tailwind CSS + shadcn/ui, GitHub Pages 배포
- **백엔드/DB**: Supabase (PostgreSQL + Realtime)
- **알림**: FCM (Firebase Cloud Messaging), 로그인 없이 기기(브라우저) 토큰 기반

---

## 핵심 설계 원칙

- **로그인 없음**: FCM 토큰(기기 단위)으로 구독/알림 관리. 나중에 Auth 확장 가능하도록 user_id 컬럼 nullable로 예비
- **동적 사이트 추가**: sites 테이블이 Single Source of Truth. DB 수정만으로 사이트 추가/비활성화 가능 (sites.yaml은 초기 시드 데이터 용도로만 사용)
- **기기별 독립 구독**: 각 기기(브라우저)마다 별도 FCM 토큰 발급, 기기별로 구독 설정. 읽음/북마크 등 유저 상태는 기기 간 동기화 안 됨 (Auth 추가 시 전환 가능)
- **구독 기반 알림**: fcm_tokens 전체가 아닌, subscriptions 테이블 기준으로 구독자만 필터하여 알림 발송

---

## 모노레포 구조

```
my_github_pages/
├── scraper/
│   ├── main.py              # 진입점 (DB에서 sites 읽고 각 사이트 스크래핑)
│   ├── sites.yaml           # 초기 시드 데이터 (DB 최초 투입용)
│   ├── scrapers/
│   │   ├── base.py          # BaseScraper 추상 클래스
│   │   ├── html.py          # requests + BeautifulSoup (일반 사이트)
│   │   └── rss.py           # RSS/Atom 피드 파서
│   ├── notifier.py          # FCM HTTP v1 API 발송
│   ├── db.py                # Supabase 클라이언트 (upsert, diff 감지)
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   │   ├── manifest.json    # PWA 매니페스트
│   │   └── sw.js            # Service Worker (FCM push 수신)
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── FeedCard.jsx     # 아이템 카드
│   │   │   ├── FilterBar.jsx    # 사이트별 필터
│   │   │   └── NotifBanner.jsx  # 알림 권한 요청 배너
│   │   ├── hooks/
│   │   │   ├── useFeed.js       # Supabase 데이터 페치
│   │   │   └── useFCM.js        # FCM 토큰 등록
│   │   └── lib/
│   │       ├── supabase.js
│   │       └── firebase.js
│   ├── vite.config.js
│   └── package.json
│
└── .github/
    └── workflows/
        ├── scrape.yml       # cron 1시간마다 스크래퍼 실행
        └── deploy.yml       # main push시 GitHub Pages 배포
```

---

## Database Schema (Supabase PostgreSQL)

### 1. sites — 스크래핑 대상 사이트 관리

```sql
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
```

selector 예시: `{"container": ".topic_row", "title": ".topictitle a", "link": ".topictitle a@href"}`

### 2. items — 스크래핑된 뉴스/게시글

```sql
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
```

### 3. fcm_tokens — 기기별 FCM 토큰

```sql
CREATE TABLE fcm_tokens (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token        text UNIQUE NOT NULL,
  user_id      uuid,                 -- nullable, Auth 연동 예비
  device_name  text,
  is_active    boolean DEFAULT true,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);
```

### 4. subscriptions — 사이트별 구독 설정

```sql
CREATE TABLE subscriptions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token_id    uuid NOT NULL REFERENCES fcm_tokens(id) ON DELETE CASCADE,
  site_id     uuid NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  category    text,                  -- NULL이면 사이트 전체 구독
  is_muted    boolean DEFAULT false,
  created_at  timestamptz DEFAULT now(),
  UNIQUE(token_id, site_id, category)
);
```

### 5. notification_log — 알림 발송 이력

```sql
CREATE TABLE notification_log (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id     uuid NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  token_id    uuid NOT NULL REFERENCES fcm_tokens(id) ON DELETE CASCADE,
  status      text NOT NULL DEFAULT 'pending',
  error_msg   text,
  sent_at     timestamptz DEFAULT now()
);
```

### 6. scrape_runs — 스크래핑 실행 이력

```sql
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
```

### 7. user_interactions — 읽음/북마크/숨기기

```sql
CREATE TABLE user_interactions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token_id    uuid NOT NULL REFERENCES fcm_tokens(id) ON DELETE CASCADE,
  item_id     uuid NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  action      text NOT NULL,         -- 'read', 'bookmark', 'hide'
  created_at  timestamptz DEFAULT now(),
  UNIQUE(token_id, item_id, action)
);
```

### 테이블 관계도

```
sites ──1:N──→ items
sites ──1:N──→ scrape_runs
sites ──1:N──→ subscriptions ←──N:1── fcm_tokens
items ──1:N──→ notification_log ←──N:1── fcm_tokens
items ──1:N──→ user_interactions ←──N:1── fcm_tokens
```

---

## RLS 정책 (Row Level Security)

프론트엔드는 Supabase anon key로 접근. 스크래퍼는 service_role key로 접근하여 RLS 우회.

| 테이블 | anon 권한 |
|---|---|
| items | SELECT only |
| fcm_tokens | INSERT + UPDATE(본인) |
| subscriptions | SELECT/INSERT/UPDATE/DELETE (token_id 본인) |
| user_interactions | SELECT/INSERT/DELETE (token_id 본인) |
| sites | SELECT (is_active=true만) |
| scrape_runs | SELECT (모니터링용) |
| notification_log | 접근 불가 |

---

## 스크래퍼 실행 플로우

```
GitHub Actions (매시간 cron)
  1. sites 테이블에서 is_active=true인 사이트 조회
  2. 사이트별 scrape_runs 레코드 생성 (status='running')
  3. 각 사이트 스크래핑 (HTML or RSS, sites.selector 기반)
  4. link 기준으로 Supabase upsert (중복 무시)
  5. 새로 삽입된 항목 감지 → scrape_runs 업데이트
  6. 새 항목 있으면 → subscriptions + fcm_tokens JOIN으로 구독자 조회
     (is_muted=false, is_active=true 필터)
  7. FCM HTTP v1 API로 푸시 발송
     → notification_log에 발송 결과 기록 (sent/failed)
  8. items.is_new = false 업데이트
  9. scrape_runs 완료 처리 (success/failed + finished_at)
```

---

## 환경변수 & Secrets

### GitHub Actions Secrets (비공개)
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
FCM_PROJECT_ID
FCM_SERVICE_ACCOUNT_JSON
SENTRY_DSN                    # (선택) 에러 모니터링
```

### 프론트엔드 환경변수 (공개 가능)
```
VITE_SUPABASE_URL
VITE_SUPABASE_ANON_KEY
VITE_FIREBASE_CONFIG
VITE_FIREBASE_VAPID_KEY
```

---

## 확장 예비 사항

- `fcm_tokens.user_id`: Supabase Auth (GitHub/Google OAuth) 연동 시 기기 간 구독/북마크 동기화
- `items.metadata` (jsonb): 사이트별 커스텀 데이터 (댓글수, 점수, 조회수 등) 유연하게 저장
- `sites.selector` (jsonb): 어드민 UI에서 셀렉터 수정 가능
- `sites.cron_expr`: 사이트별 스크래핑 주기 차별화
