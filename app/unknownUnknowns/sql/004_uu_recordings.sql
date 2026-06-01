-- uu_recordings
--   One row per audio capture. kind distinguishes 'cold' vs 'final' for the
--   same prompt; UNIQUE(prompt_id, kind) prevents duplicates.
--   s3_key is set when the frontend completes its presigned-URL PUT.
--   transcript + transcribed_at are populated by the backend transcription
--   step after upload.
--
--   FORWARD-LOOKING: schema in place, no endpoints write to this table in the
--   bootstrap slice.

CREATE TABLE IF NOT EXISTS uu_recordings (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id       UUID         NOT NULL,
    kind            TEXT         NOT NULL,
    s3_key          TEXT         NOT NULL,
    transcript      TEXT,
    transcribed_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_uu_recordings_prompt_kind UNIQUE (prompt_id, kind)
);

CREATE INDEX IF NOT EXISTS idx_uu_recordings_prompt ON uu_recordings (prompt_id);
