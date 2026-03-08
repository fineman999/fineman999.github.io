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

-- Prevent duplicate notifications (race condition guard)
ALTER TABLE notification_log ADD CONSTRAINT uq_notification_log_item_token UNIQUE (item_id, token_id);

-- Enforce valid status values
ALTER TABLE notification_log ADD CONSTRAINT chk_notification_status
  CHECK (status IN ('pending', 'sent', 'failed'));

ALTER TABLE scrape_runs ADD CONSTRAINT chk_scrape_status
  CHECK (status IN ('running', 'success', 'failed'));
