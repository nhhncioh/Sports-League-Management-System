-- Schedule Management Enhancement Tables

-- Blackout Dates: dates when matches cannot be scheduled
CREATE TABLE IF NOT EXISTS blackout_dates (
    blackout_id SERIAL PRIMARY KEY,
    league_id INTEGER REFERENCES leagues(league_id) ON DELETE CASCADE,
    season_id INTEGER REFERENCES seasons(season_id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason VARCHAR(255),
    applies_to VARCHAR(50) DEFAULT 'all', -- 'all', 'specific_teams', 'specific_venue'
    metadata JSONB, -- store team_ids, venue_ids, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    CHECK (end_date >= start_date)
);

-- Schedule Drafts: allow creating and reviewing schedules before publishing
CREATE TABLE IF NOT EXISTS schedule_drafts (
    draft_id SERIAL PRIMARY KEY,
    league_id INTEGER REFERENCES leagues(league_id) ON DELETE CASCADE,
    season_id INTEGER REFERENCES seasons(season_id) ON DELETE CASCADE,
    draft_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'pending_approval', 'approved', 'rejected', 'published'
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by INTEGER,
    rejection_reason TEXT,
    approval_notes TEXT,
    generation_params JSONB, -- store parameters used to generate this draft
    conflict_count INTEGER DEFAULT 0,
    UNIQUE(league_id, season_id, draft_name)
);

-- Draft Matches: matches associated with a draft
CREATE TABLE IF NOT EXISTS draft_matches (
    draft_match_id SERIAL PRIMARY KEY,
    draft_id INTEGER REFERENCES schedule_drafts(draft_id) ON DELETE CASCADE,
    home_team_id INTEGER REFERENCES teams(team_id) ON DELETE CASCADE,
    away_team_id INTEGER REFERENCES teams(team_id) ON DELETE CASCADE,
    proposed_date TIMESTAMP NOT NULL,
    venue_id INTEGER,
    matchday INTEGER, -- round/week number
    display_order INTEGER DEFAULT 0, -- for custom ordering within matchday
    notes TEXT,
    has_conflict BOOLEAN DEFAULT FALSE,
    conflict_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Schedule Conflicts: detected issues with proposed schedules
CREATE TABLE IF NOT EXISTS schedule_conflicts (
    conflict_id SERIAL PRIMARY KEY,
    draft_match_id INTEGER REFERENCES draft_matches(draft_match_id) ON DELETE CASCADE,
    conflict_type VARCHAR(50) NOT NULL, -- 'blackout_date', 'team_unavailable', 'venue_conflict', 'rest_period', 'double_booking'
    severity VARCHAR(20) DEFAULT 'warning', -- 'info', 'warning', 'error'
    description TEXT NOT NULL,
    auto_resolvable BOOLEAN DEFAULT FALSE,
    resolution_suggestion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Approval Workflow Log
CREATE TABLE IF NOT EXISTS schedule_approval_log (
    log_id SERIAL PRIMARY KEY,
    draft_id INTEGER REFERENCES schedule_drafts(draft_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL, -- 'created', 'submitted', 'approved', 'rejected', 'published', 'modified'
    actor_id INTEGER,
    actor_name VARCHAR(255),
    notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add display_order to existing matches table for manual reordering
ALTER TABLE matches ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS matchday INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS venue_id INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE; -- prevent changes to published matches

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_blackout_dates_league_season ON blackout_dates(league_id, season_id);
CREATE INDEX IF NOT EXISTS idx_blackout_dates_date_range ON blackout_dates(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_schedule_drafts_status ON schedule_drafts(status);
CREATE INDEX IF NOT EXISTS idx_draft_matches_draft_id ON draft_matches(draft_id);
CREATE INDEX IF NOT EXISTS idx_draft_matches_date ON draft_matches(proposed_date);
CREATE INDEX IF NOT EXISTS idx_schedule_conflicts_draft_match ON schedule_conflicts(draft_match_id);
CREATE INDEX IF NOT EXISTS idx_matches_display_order ON matches(league_id, season_id, display_order);
CREATE INDEX IF NOT EXISTS idx_matches_matchday ON matches(league_id, season_id, matchday);
