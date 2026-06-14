"""
End-of-day scoring for Unknown Unknowns.

Pattern mirrors briefing_generator.py:
  • One LLM call per topic. Inputs are the curriculum bullets, the cold
    transcript, and the final transcript. Output is two metric blocks
    (cold + final, each 1-10 across coverage/accuracy/structure/depth/
    clarity) plus a synthesis paragraph naming what changed.
  • Per-prompt task waits up to 90s each for cold + final transcripts to
    land. All topics scored in parallel via asyncio.gather.
  • Idempotent: if a prompt's cold and final scores already exist, skip.

Persistence layout:
  • uu_scores has one row per Recording (5 metrics, one per kind).
  • The per-topic notes_md paragraph lives on uu_prompts.scoring_notes_md
    since it synthesizes both recordings, not one.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Literal

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select

from app.common.llm import ask_claude_structured
from app.db.session import async_session
from app.unknownUnknowns.models import Prompt, Recording, Score

# ---------- LLM contract ----------

SCORING_SYSTEM_PROMPT = """\
You're scoring a user's recorded explanations for a daily learning app \
built around the Illusion of Explanatory Depth.

For each topic, you'll receive:
- The cold prompt (the question asked on the first attempt)
- The final prompt (a NEW-ANGLE question, NOT a rephrasing of the cold prompt)
- The curriculum bullets (the anchor concepts that teach the whole topic; \
they were written to fully answer the COLD prompt)
- The cold transcript (the user's first attempt, no preparation)
- The final transcript (their second attempt after reading a briefing)

Your output is three things:
1. `cold_score`: five 1-10 metrics rating the cold recording
2. `final_score`: five 1-10 metrics rating the final recording
3. `notes_md`: one paragraph (~80-150 words) explaining what changed \
between cold and final

CRITICAL — the two recordings answer DIFFERENT questions, so score them \
against DIFFERENT targets:
- Score the COLD recording against the COLD prompt, using the curriculum \
bullets as the checklist of what a complete answer covers.
- Score the FINAL recording against the FINAL prompt ONLY. The final is a \
new-angle question that needs just the SUBSET of concepts relevant to it \
(plus correct transfer to the new situation). Do NOT penalize the user for \
omitting curriculum bullets that aren't needed to answer the final question. \
Treat the curriculum as available knowledge, not a checklist the final must \
re-cover. Example: cold "Why is the sky blue?" → final "Why is the sky red \
at sunset?". The final answer needs wavelength-dependent scattering and the \
longer atmospheric path at sunset; it does NOT need to re-derive everything \
about daytime blue, and must not be docked for leaving it out.

Metrics (each 1-10):
- coverage: for the cold recording, how many curriculum bullets the user \
touched; for the final recording, whether they brought in the concepts the \
FINAL question actually requires (not the full curriculum)
- accuracy: how correct what they said was
- structure: how well-organized their explanation flowed
- depth: how thoroughly they explored each concept they raised
- clarity: how clearly they communicated to a listener

Be cold-honest. The product depends on accurate feedback:
- If a metric went DOWN from cold to final, MARK IT DOWN. Don't smooth.
- If the user said very little or went off-topic, low scores are appropriate.
- A 6 means "competent but with real gaps". A 9 means "near-mastery". \
A 10 means "couldn't be meaningfully improved". Reserve 9s and 10s.
- Inflation is not kindness; the user already knows what they said.

Notes (`notes_md`):
- One paragraph, ~80-150 words. No bullet lists, no headers.
- Reference specific things they actually said (or specifically didn't say).
- Stay descriptive, never evaluative: \
"in the final you got the wavelength scaling but conflated violet \
sensitivity with violet absorption" — NOT "good improvement" or \
"weak coverage". The user sees the numbers; notes explain what's behind \
them.
- Use *italic markers* for emphasis on key terms or phrases.\
"""


class GeneratedRecordingScore(BaseModel):
    coverage: int
    accuracy: int
    structure: int
    depth: int
    clarity: int


class GeneratedTopicScores(BaseModel):
    cold_score: GeneratedRecordingScore
    final_score: GeneratedRecordingScore
    notes_md: str


async def score_topic(
    cold_prompt: str,
    final_prompt: str,
    curriculum_bullets: list[str],
    cold_transcript: str,
    final_transcript: str,
) -> GeneratedTopicScores:
    """One LLM call returning both recordings' metric blocks + a notes paragraph."""
    bullets = "\n".join(f"- {b}" for b in curriculum_bullets)
    user_prompt = (
        f"Topic — cold prompt asked:\n{cold_prompt}\n\n"
        f"Final challenge asked:\n{final_prompt}\n\n"
        f"Curriculum bullets (the anchor concepts):\n{bullets}\n\n"
        f'Cold transcript (user\'s first attempt):\n"""\n{cold_transcript}\n"""\n\n'
        f'Final transcript (user\'s second attempt, after the briefing):\n'
        f'"""\n{final_transcript}\n"""\n\n'
        "Score both recordings and explain what changed."
    )
    return await ask_claude_structured(
        prompt=user_prompt,
        schema=GeneratedTopicScores,
        system=SCORING_SYSTEM_PROMPT,
        cache_system=True,
        effort="high",
        max_tokens=12_000,
    )


# ---------- Orchestrator ----------

_TRANSCRIPT_POLL_INTERVAL_SECONDS = 2
_TRANSCRIPT_MAX_WAIT_SECONDS = 90


async def _get_recording(
    prompt_id: uuid.UUID, kind: Literal["cold", "final"]
) -> Recording | None:
    async with async_session() as session:
        result = await session.execute(
            select(Recording).where(
                Recording.prompt_id == prompt_id, Recording.kind == kind
            )
        )
        return result.scalar_one_or_none()


async def _wait_for_transcript(
    prompt_id: uuid.UUID, kind: Literal["cold", "final"]
) -> tuple[Recording, str] | None:
    """Returns (recording, transcript) once the recording row has a non-null
    transcript, or None on timeout."""
    elapsed = 0
    while elapsed < _TRANSCRIPT_MAX_WAIT_SECONDS:
        rec = await _get_recording(prompt_id, kind)
        if rec is not None and rec.transcript:
            return rec, rec.transcript
        await asyncio.sleep(_TRANSCRIPT_POLL_INTERVAL_SECONDS)
        elapsed += _TRANSCRIPT_POLL_INTERVAL_SECONDS
    return None


async def _score_for_prompt(prompt_id: uuid.UUID) -> None:
    """Per-prompt: wait for both transcripts, run the LLM call, persist
    two Score rows + the prompt's notes_md. Idempotent: skip if both
    scores already exist."""
    try:
        async with async_session() as session:
            result = await session.execute(select(Prompt).where(Prompt.id == prompt_id))
            prompt = result.scalar_one_or_none()
            if prompt is None:
                logger.warning(f"[uu scoring] Prompt {prompt_id} not found — skipping.")
                return
            cold_prompt_text = prompt.cold_prompt_text
            final_prompt_text = prompt.final_prompt_text
            bullets = list(prompt.curriculum_bullets or [])

        if not bullets:
            logger.error(
                f"[uu scoring] Prompt {prompt_id} has no curriculum bullets — can't score."
            )
            return

        cold = await _wait_for_transcript(prompt_id, "cold")
        if cold is None:
            logger.warning(
                f"[uu scoring] Cold transcript for prompt {prompt_id} not ready — skipping."
            )
            return
        cold_recording, cold_transcript = cold

        final = await _wait_for_transcript(prompt_id, "final")
        if final is None:
            logger.warning(
                f"[uu scoring] Final transcript for prompt {prompt_id} not ready — skipping."
            )
            return
        final_recording, final_transcript = final

        # Idempotency: if both scores already exist, skip.
        async with async_session() as session:
            existing = await session.execute(
                select(Score).where(
                    Score.recording_id.in_(
                        [cold_recording.id, final_recording.id]
                    )
                )
            )
            if len(list(existing.scalars().all())) >= 2:
                logger.info(
                    f"[uu scoring] Both scores already exist for prompt {prompt_id} — skipping."
                )
                return

        logger.info(f"[uu scoring] Scoring topic {prompt_id}…")
        scored = await score_topic(
            cold_prompt=cold_prompt_text,
            final_prompt=final_prompt_text,
            curriculum_bullets=bullets,
            cold_transcript=cold_transcript,
            final_transcript=final_transcript,
        )

        # Persist: 2 score rows + notes_md on the prompt.
        async with async_session() as session:
            for recording_id, ms in (
                (cold_recording.id, scored.cold_score),
                (final_recording.id, scored.final_score),
            ):
                # Delete any partial existing score for this recording, then insert.
                existing_row = await session.execute(
                    select(Score).where(Score.recording_id == recording_id)
                )
                row = existing_row.scalar_one_or_none()
                if row is not None:
                    await session.delete(row)
                    await session.flush()
                session.add(
                    Score(
                        recording_id=recording_id,
                        coverage=ms.coverage,
                        accuracy=ms.accuracy,
                        structure=ms.structure,
                        depth=ms.depth,
                        clarity=ms.clarity,
                    )
                )

            result = await session.execute(select(Prompt).where(Prompt.id == prompt_id))
            prompt = result.scalar_one()
            prompt.scoring_notes_md = scored.notes_md
            await session.commit()
            logger.info(
                f"[uu scoring] Stored scores + notes for prompt {prompt_id}."
            )
    except Exception:
        logger.exception(
            f"[uu scoring] Per-prompt scoring failed for {prompt_id}."
        )


async def score_session(session_id: uuid.UUID) -> None:
    """Kick off concurrent per-prompt scorers for a session. Idempotent."""
    async with async_session() as session:
        result = await session.execute(
            select(Prompt)
            .where(Prompt.session_id == session_id)
            .order_by(Prompt.order_index)
        )
        prompts = list(result.scalars().all())

    if not prompts:
        logger.warning(f"[uu scoring] Session {session_id} has no prompts.")
        return

    logger.info(
        f"[uu scoring] Scoring session {session_id} ({len(prompts)} topic(s))."
    )
    await asyncio.gather(
        *(_score_for_prompt(p.id) for p in prompts),
        return_exceptions=True,
    )
    logger.info(f"[uu scoring] Scoring pass complete for session {session_id}.")
