-- uu_users
--   Auth-attached identity. firebase_uid is the unique handle (currently the
--   hardcoded "dev-user-001" while the auth dependency is stubbed; becomes the
--   real Firebase UID when Firebase Admin SDK is wired).
--
-- NOTE: this file is human-readable schema documentation. SQLAlchemy
-- create_all() on FastAPI startup creates the actual table — see
-- app/unknownUnknowns/models.py and app/db/session.py.

CREATE TABLE IF NOT EXISTS uu_users (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid        TEXT         NOT NULL UNIQUE,
    email               TEXT,
    streak_count        INTEGER      NOT NULL DEFAULT 0,
    last_completed_date DATE,
    prefs               JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uu_users_firebase_uid ON uu_users (firebase_uid);
