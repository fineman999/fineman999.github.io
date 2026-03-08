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

-- notification_log: no anon access (service_role bypasses RLS automatically)
