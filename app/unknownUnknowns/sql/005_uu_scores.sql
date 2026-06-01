-- uu_scores
--   One row per recording (cold or final). Five 1–10 metrics + free-form
--   personalized notes for the score reveal screen. Generated end-of-day in
--   a single batched LLM call across all 6 recordings.
--
--   FORWARD-LOOKING: schema in place, no endpoints write to this table in the
--   bootstrap slice.

CREATE TABLE IF NOT EXISTS uu_scores (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id  UUID         NOT NULL UNIQUE,
    coverage      INTEGER      NOT NULL,
    accuracy      INTEGER      NOT NULL,
    structure     INTEGER      NOT NULL,
    depth         INTEGER      NOT NULL,
    clarity       INTEGER      NOT NULL,
    notes_md      TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_uu_scores_coverage  CHECK (coverage  BETWEEN 1 AND 10),
    CONSTRAINT ck_uu_scores_accuracy  CHECK (accuracy  BETWEEN 1 AND 10),
    CONSTRAINT ck_uu_scores_structure CHECK (structure BETWEEN 1 AND 10),
    CONSTRAINT ck_uu_scores_depth     CHECK (depth     BETWEEN 1 AND 10),
    CONSTRAINT ck_uu_scores_clarity   CHECK (clarity   BETWEEN 1 AND 10)
);
