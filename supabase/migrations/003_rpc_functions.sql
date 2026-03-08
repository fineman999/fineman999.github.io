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
