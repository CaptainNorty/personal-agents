-- uu_daily_sessions
--   One row per user per day. session_date is the user-local calendar date the
--   ritual was started; UNIQUE(user_id, session_date) enforces "one session
--   per day."
--   completed_at flips from NULL → NOW() when the end-of-day scoring flow
--   finishes (deferred to a later slice).

CREATE TABLE IF NOT EXISTS uu_daily_sessions (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID         NOT NULL,
    session_date    DATE         NOT NULL,
    prompt_count    INTEGER      NOT NULL,
    include_repeat  BOOLEAN      NOT NULL DEFAULT FALSE,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_uu_daily_sessions_user_date UNIQUE (user_id, session_date),
    CONSTRAINT ck_uu_daily_sessions_prompt_count CHECK (prompt_count BETWEEN 1 AND 3)
);

CREATE INDEX IF NOT EXISTS idx_uu_daily_sessions_user_date
    ON uu_daily_sessions (user_id, session_date);
