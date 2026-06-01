-- uu_prompts
--   N rows per session — one per cold/final pair, ordered by order_index.
--
--   curriculum_bullets is generated overnight (the 4–5 anchor points the
--   day-of briefing generator must hit). briefing_md is null until after the
--   cold recording is captured, then populated by the post-record LLM call
--   that takes { curriculum_bullets, cold_transcript } and writes the prose
--   briefing (opens with 1–2 sentences acknowledging where the user landed).
--
--   source_prompt_id is set when category='repeat' to point at the earlier
--   prompt being re-asked.

CREATE TABLE IF NOT EXISTS uu_prompts (
    id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id             UUID         NOT NULL,
    category               TEXT         NOT NULL,
    order_index            INTEGER      NOT NULL,
    cold_prompt_text       TEXT         NOT NULL,
    curriculum_bullets     JSONB        NOT NULL,
    briefing_md            TEXT,
    briefing_generated_at  TIMESTAMPTZ,
    final_prompt_text      TEXT         NOT NULL,
    source_prompt_id       UUID,
    scoring_notes_md       TEXT,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_uu_prompts_session_order UNIQUE (session_id, order_index)
);

CREATE INDEX IF NOT EXISTS idx_uu_prompts_session ON uu_prompts (session_id);
