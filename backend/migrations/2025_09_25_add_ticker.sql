-- migrations/2025_09_25_add_ticker.sql
CREATE TABLE IF NOT EXISTS ticker_settings (
  id SERIAL PRIMARY KEY,
  league_id UUID NOT NULL UNIQUE,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  theme JSONB NOT NULL DEFAULT '{
    "bg":"#0b0d12",
    "fg":"#ffffff",
    "accent":"#ffc107",
    "height":40,
    "speed":55,
    "showLogos":true,
    "showStatus":true
  }',
  source JSONB NOT NULL DEFAULT '{
    "mode":"manual",
    "externalUrl":null,
    "competitionIds":[]
  }',
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticker_items (
  id SERIAL PRIMARY KEY,
  league_id UUID NOT NULL,
  start_time TIMESTAMP,
  status VARCHAR(24) DEFAULT 'FINAL',
  home_name VARCHAR(80),
  away_name VARCHAR(80),
  home_logo TEXT,
  away_logo TEXT,
  home_score INT,
  away_score INT,
  venue VARCHAR(120),
  link_url TEXT,
  sort_key TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ticker_items_league ON ticker_items (league_id, sort_key DESC);
