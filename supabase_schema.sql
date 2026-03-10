-- ============================================================
-- NEXUS AI — Supabase SQL Schema
-- Выполни этот скрипт в Supabase SQL Editor
-- ============================================================

-- ─── Таблица мероприятий ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    title TEXT NOT NULL,
    date DATE NOT NULL,
    location TEXT NOT NULL,
    max_candidates INTEGER NOT NULL DEFAULT 10,
    status TEXT NOT NULL DEFAULT 'Draft',
    poll_id TEXT,
    sheet_url TEXT,
    required_men INTEGER NOT NULL DEFAULT 0,
    required_women INTEGER NOT NULL DEFAULT 0,
    created_by BIGINT, -- Telegram user_id рекрутера
    created_at TIMESTAMPTZ DEFAULT now ()
);

-- ─── Таблица кандидатов ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    user_id BIGINT PRIMARY KEY, -- Telegram user_id
    first_name TEXT NOT NULL,
    last_name TEXT DEFAULT '',
    phone_number TEXT DEFAULT '',
    telegram_username TEXT DEFAULT '',
    gender TEXT CHECK (gender IN ('Male', 'Female')),
    has_messaged_bot BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now ()
);

-- ─── Связующая таблица Event <-> Candidate ───────────────────────────────────
CREATE TABLE IF NOT EXISTS event_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    event_id UUID REFERENCES events (event_id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES candidates (user_id) ON DELETE CASCADE,
    vote_status TEXT CHECK (
        vote_status IN ('yes', 'no', 'maybe')
    ),
    selected BOOLEAN DEFAULT FALSE,
    arrival_time TEXT, -- HH:MM (24h)
    departure_time TEXT, -- HH:MM (24h)
    confirmed BOOLEAN DEFAULT FALSE,
    UNIQUE (event_id, user_id)
);

-- ─── Аудит-лог ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS event_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    event_id UUID REFERENCES events (event_id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    performed_by BIGINT, -- Telegram user_id
    timestamp TIMESTAMPTZ DEFAULT now (),
    details JSONB DEFAULT '{}'
);

-- ─── Индексы для производительности ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_events_status ON events (status);

CREATE INDEX IF NOT EXISTS idx_events_poll_id ON events (poll_id);

CREATE INDEX IF NOT EXISTS idx_ec_event_id ON event_candidates (event_id);

CREATE INDEX IF NOT EXISTS idx_ec_user_id ON event_candidates (user_id);

CREATE INDEX IF NOT EXISTS idx_ec_selected ON event_candidates (event_id, selected);

CREATE INDEX IF NOT EXISTS idx_logs_event_id ON event_logs (event_id);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON event_logs (timestamp DESC);

-- ─── Row Level Security (RLS) ─────────────────────────────────────────────────
-- Включаем RLS (используй service_role ключ в боте для обхода)
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;

ALTER TABLE event_candidates ENABLE ROW LEVEL SECURITY;

ALTER TABLE event_logs ENABLE ROW LEVEL SECURITY;

-- Разрешить полный доступ для service_role (используется ботом)
CREATE POLICY "service_role_all_events" ON events FOR ALL USING (true);

CREATE POLICY "service_role_all_cands" ON candidates FOR ALL USING (true);

CREATE POLICY "service_role_all_ec" ON event_candidates FOR ALL USING (true);

CREATE POLICY "service_role_all_logs" ON event_logs FOR ALL USING (true);