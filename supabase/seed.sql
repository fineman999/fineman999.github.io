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
