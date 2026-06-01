"""
Post-cold-record briefing generation for Unknown Unknowns.

Hybrid contract (see DESIGN.md):
  • Overnight: curriculum_bullets are pre-generated and stored on uu_prompts.
  • Post-cold-record: this module takes
      { curriculum_bullets, cold_transcript }
    and asks Claude to write a structured briefing that opens with a 1-2
    sentence acknowledgment of where the user landed, then teaches the
    curriculum bullets. The output is assembled into markdown and stored
    on uu_prompts.briefing_md.

Concurrency:
  • generate_briefings_for_session runs all per-prompt generators in
    parallel. Each per-prompt task waits for its cold transcript to land
    (polls the recordings row), then makes one structured LLM call.
  • Idempotent: any prompt that already has briefing_md is skipped.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.common.llm import ask_claude_structured
from app.db.session import async_session
from app.unknownUnknowns.models import Prompt, Recording

# ---------- LLM contract ----------

BRIEFING_SYSTEM_PROMPT = """\
You are a brilliant friend writing a brief, clear teaching note for a daily \
learning app. The user just gave their best cold attempt at a topic. Your \
briefing teaches the topic *while gently acknowledging where they landed*.

You will return three structured fields:

- `topic_title`: a short topical heading (e.g., "Rayleigh scattering & the \
blue sky"). NOT the question form ("Why is the sky blue?") — name the \
concept.
- `acknowledgment`: 1-2 sentences naming what the user actually covered or \
missed. Be specific to their words. STAY DESCRIPTIVE, never evaluative: \
don't say "good", "wrong", "correct", "incomplete", and never preview a \
score. The shape you want is "You [thing they said/missed], [what the \
briefing will fill in]." Example: "You named the wavelength dependence but \
skipped why violet doesn't dominate the sky's color."
- `body_paragraphs`: 3-4 short paragraphs that teach the curriculum bullets. \
Each paragraph covers one or two related bullets in clear prose. Use \
*italic markers* for emphasized terms. No bullet lists, no sub-headings in \
the body — just paragraphs.

Total length across acknowledgment + body: roughly 300-400 words. Tight, no \
filler. Confident, never lecturing. If the user said little or went \
off-topic, name that calmly in the acknowledgment ("You didn't speak much \
to the topic — here's the curriculum we'd cover.") and proceed to teach \
without judgment.\
"""


class GeneratedBriefing(BaseModel):
    """LLM output schema. Assembled into markdown by briefing_to_markdown()."""

    topic_title: str = Field(
        description=(
            "Short topical heading naming the concept, not the question form."
        )
    )
    acknowledgment: str = Field(
        description=(
            "1-2 sentences referencing what the user actually said. "
            "Descriptive, never evaluative."
        )
    )
    body_paragraphs: list[str] = Field(
        description="3-4 prose paragraphs teaching the curriculum bullets."
    )


def briefing_to_markdown(b: GeneratedBriefing) -> str:
    body = "\n\n".join(p.strip() for p in b.body_paragraphs)
    return f"# {b.topic_title}\n\n{b.acknowledgment.strip()}\n\n{body}"


async def generate_briefing(
    cold_prompt: str,
    curriculum_bullets: list[str],
    cold_transcript: str,
) -> GeneratedBriefing:
    """One LLM call: bullets + transcript → structured briefing."""
    bullets_text = "\n".join(f"- {b}" for b in curriculum_bullets)
    user_prompt = (
        f"Cold prompt the user was asked:\n{cold_prompt}\n\n"
        f"Curriculum bullets (you must cover all of these):\n{bullets_text}\n\n"
        f"What the user said (their cold transcript):\n"
        f'"""\n{cold_transcript}\n"""\n\n'
        "Write the briefing."
    )
    return await ask_claude_structured(
        prompt=user_prompt,
        schema=GeneratedBriefing,
        system=BRIEFING_SYSTEM_PROMPT,
        # Future-proof: cache the system prompt for the day's batch. Won't
        # actually cache today (prefix is under the 4096-token minimum on
        # Opus 4.7) but engages automatically if we expand the prompt.
        cache_system=True,
        # Briefing is intelligence-sensitive; high is the right baseline per
        # the Opus 4.7 effort guidance.
        effort="high",
        max_tokens=8_000,
    )


# ---------- Orchestrator ----------

_TRANSCRIPT_POLL_INTERVAL_SECONDS = 2
_TRANSCRIPT_MAX_WAIT_SECONDS = 90


async def _wait_for_cold_transcript(prompt_id: uuid.UUID) -> str | None:
    """Poll for the cold transcript. Returns the transcript text or None on
    timeout. Doesn't raise — the caller logs and skips."""
    elapsed = 0
    while elapsed < _TRANSCRIPT_MAX_WAIT_SECONDS:
        async with async_session() as session:
            result = await session.execute(
                select(Recording).where(
                    Recording.prompt_id == prompt_id,
                    Recording.kind == "cold",
                )
            )
            recording = result.scalar_one_or_none()
            if recording and recording.transcript:
                return recording.transcript

        await asyncio.sleep(_TRANSCRIPT_POLL_INTERVAL_SECONDS)
        elapsed += _TRANSCRIPT_POLL_INTERVAL_SECONDS

    return None


async def _generate_for_prompt(prompt_id: uuid.UUID) -> None:
    """Per-prompt generator: skip if briefing exists, otherwise wait for
    transcript and generate. Catches its own errors so concurrent siblings
    aren't affected."""
    try:
        # Read current prompt state (skip-if-done check + LLM inputs).
        async with async_session() as session:
            result = await session.execute(
                select(Prompt).where(Prompt.id == prompt_id)
            )
            prompt = result.scalar_one_or_none()
            if prompt is None:
                logger.warning(
                    f"[uu briefings] Prompt {prompt_id} not found — skipping."
                )
                return
            if prompt.briefing_md is not None:
                logger.info(
                    f"[uu briefings] Prompt {prompt_id} already has a briefing — skipping."
                )
                return
            cold_prompt = prompt.cold_prompt_text
            bullets = list(prompt.curriculum_bullets or [])

        if not bullets:
            logger.error(
                f"[uu briefings] Prompt {prompt_id} has no curriculum bullets — can't generate."
            )
            return

        cold_transcript = await _wait_for_cold_transcript(prompt_id)
        if not cold_transcript:
            logger.warning(
                f"[uu briefings] Cold transcript for prompt {prompt_id} not ready "
                f"after {_TRANSCRIPT_MAX_WAIT_SECONDS}s — skipping. "
                "Caller can retry later."
            )
            return

        logger.info(
            f"[uu briefings] Generating briefing for prompt {prompt_id}…"
        )
        generated = await generate_briefing(cold_prompt, bullets, cold_transcript)
        md = briefing_to_markdown(generated)

        # Re-read + persist.
        async with async_session() as session:
            result = await session.execute(
                select(Prompt).where(Prompt.id == prompt_id)
            )
            prompt = result.scalar_one()
            prompt.briefing_md = md
            prompt.briefing_generated_at = datetime.now(timezone.utc).replace(
                tzinfo=None
            )
            await session.commit()
            logger.info(
                f"[uu briefings] Stored briefing for prompt {prompt_id} ({len(md)} chars)."
            )
    except Exception:
        logger.exception(
            f"[uu briefings] Per-prompt generation failed for {prompt_id}."
        )


async def generate_briefings_for_session(session_id: uuid.UUID) -> None:
    """Kick off concurrent per-prompt generators for every prompt in a session.

    Idempotent (skips prompts whose briefing already exists). Safe to invoke
    multiple times — overlapping calls do redundant DB checks but don't
    produce duplicates.
    """
    async with async_session() as session:
        result = await session.execute(
            select(Prompt)
            .where(Prompt.session_id == session_id)
            .order_by(Prompt.order_index)
        )
        prompts = list(result.scalars().all())

    if not prompts:
        logger.warning(
            f"[uu briefings] Session {session_id} has no prompts — nothing to do."
        )
        return

    logger.info(
        f"[uu briefings] Kicking off briefing generation for session {session_id} "
        f"({len(prompts)} prompt(s))."
    )
    await asyncio.gather(
        *(_generate_for_prompt(p.id) for p in prompts),
        return_exceptions=True,
    )
    logger.info(
        f"[uu briefings] Briefing generation pass complete for session {session_id}."
    )
