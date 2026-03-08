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

-- items: anon read all
CREATE POLICY "items_anon_read" ON items FOR SELECT TO anon USING (true);

-- fcm_tokens: anon insert (token registration)
-- Note: no update policy needed — token refresh handled by upsert in scraper
CREATE POLICY "fcm_tokens_anon_insert" ON fcm_tokens FOR INSERT TO anon WITH CHECK (true);
-- anon can read their own token row (needed to get token_id after insert)
CREATE POLICY "fcm_tokens_anon_select" ON fcm_tokens FOR SELECT TO anon USING (true);

-- subscriptions: anon full access
-- Ownership enforced at app level (frontend passes token_id from localStorage)
-- Data sensitivity: low (subscription preferences only)
CREATE POLICY "subscriptions_anon_all" ON subscriptions FOR ALL TO anon USING (true) WITH CHECK (true);

-- user_interactions: anon full access
-- Ownership enforced at app level. Data: read/bookmark/hide state only.
CREATE POLICY "user_interactions_anon_all" ON user_interactions FOR ALL TO anon USING (true) WITH CHECK (true);

-- scrape_runs: anon read (monitoring dashboard)
CREATE POLICY "scrape_runs_anon_read" ON scrape_runs FOR SELECT TO anon USING (true);

-- notification_log: no anon access (internal only, service_role writes)
CREATE POLICY "notification_log_deny_anon" ON notification_log AS RESTRICTIVE TO anon USING (false);
