"""
Service layer — DAO-equivalent query helpers for Unknown Unknowns.

Plain async functions that take an `AsyncSession` and return ORM models. Route
handlers stay thin; multi-step DB logic (find-or-create today's session, seed
prompts) lives here so it's reusable from tests and future cron jobs.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.unknownUnknowns.content_generator import PENDING_TOPICS_PREFS_KEY
from app.unknownUnknowns.fixtures import FAKE_TOPICS
from app.unknownUnknowns.models import DailySession, Prompt, Recording, User


def today_in_tz(tz_name: str | None) -> date:
    """User's local date for an IANA timezone string (e.g. 'America/Denver').

    Falls back to UTC if the header is missing or unparseable. We compute
    "today" in the user's tz so the daily-ritual boundary matches local
    midnight rather than server (UTC) midnight.
    """
    if not tz_name:
        return datetime.now(timezone.utc).date()
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.now(timezone.utc).date()
    return datetime.now(tz).date()


async def find_today_session(
    session: AsyncSession, user_id: uuid.UUID, today: date | None = None
) -> DailySession | None:
    """Return today's session for the user, or None."""
    today = today or date.today()
    result = await session.execute(
        select(DailySession).where(
            DailySession.user_id == user_id,
            DailySession.session_date == today,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_today_session(
    session: AsyncSession,
    user: User,
    prompt_count: int,
    include_repeat: bool,
    today: date | None = None,
) -> DailySession:
    """Idempotent: returns the existing today's session if any, otherwise
    creates one and seeds `prompt_count` prompts.

    Topic source priority:
      1. user.prefs.pending_topics (pre-generated end-of-previous-session)
      2. FAKE_TOPICS fixtures (first-day fallback before generation has run)

    Pending topics are drained from the front of the pool as they're consumed.
    """
    today = today or date.today()
    existing = await find_today_session(session, user.id, today=today)
    if existing is not None:
        return existing

    daily = DailySession(
        user_id=user.id,
        session_date=today,
        prompt_count=prompt_count,
        include_repeat=include_repeat,
    )
    session.add(daily)
    await session.flush()  # populate daily.id without committing yet

    # Pull from the pending pool first; fall back to fixtures if it's short.
    pool = list((user.prefs or {}).get(PENDING_TOPICS_PREFS_KEY) or [])
    consumed: list[dict] = []
    for i in range(prompt_count):
        if pool:
            t = pool.pop(0)
            consumed.append(t)
            session.add(
                Prompt(
                    session_id=daily.id,
                    category=t["category"],
                    order_index=i,
                    cold_prompt_text=t["cold_prompt_text"],
                    curriculum_bullets=list(t["curriculum_bullets"]),
                    final_prompt_text=t["final_prompt_text"],
                )
            )
        else:
            fallback = FAKE_TOPICS[i % len(FAKE_TOPICS)]
            session.add(
                Prompt(
                    session_id=daily.id,
                    category=fallback.category,
                    order_index=i,
                    cold_prompt_text=fallback.cold_prompt,
                    curriculum_bullets=list(fallback.curriculum_bullets),
                    final_prompt_text=fallback.final_prompt,
                )
            )

    if consumed:
        # Update prefs with the drained pool so we don't re-use topics.
        new_prefs = dict(user.prefs or {})
        new_prefs[PENDING_TOPICS_PREFS_KEY] = pool
        user.prefs = new_prefs

    await session.commit()
    await session.refresh(daily)
    return daily


async def mark_session_complete(
    session: AsyncSession,
    user: User,
    daily: DailySession,
    today: date | None = None,
) -> bool:
    """Mark today's session completed and update the user's streak.

    Returns True if this call actually changed state (caller can decide to
    kick off generation), False if it was already complete.

    Streak logic (date-only, computed in the user's local timezone):
      - last_completed_date is None      → streak = 1
      - last_completed_date == today     → no change (idempotent)
      - last_completed_date == yesterday → streak += 1
      - otherwise (gap)                  → streak = 1
    """
    if daily.completed_at is not None:
        return False

    daily.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    today = today or date.today()
    yesterday = today - timedelta(days=1)
    last = user.last_completed_date

    if last == today:
        # Defensive: another path already marked completion.
        pass
    elif last is None or last < yesterday:
        user.streak_count = 1
    elif last == yesterday:
        user.streak_count = (user.streak_count or 0) + 1
    user.last_completed_date = today

    await session.commit()
    return True


async def get_session_prompts(
    session: AsyncSession, session_id: uuid.UUID
) -> list[Prompt]:
    """Prompts for a session, ordered by order_index."""
    result = await session.execute(
        select(Prompt)
        .where(Prompt.session_id == session_id)
        .order_by(Prompt.order_index)
    )
    return list(result.scalars().all())


async def find_prompt_for_user(
    session: AsyncSession, prompt_id: uuid.UUID, user_id: uuid.UUID
) -> Prompt | None:
    """Return the prompt if it belongs to one of the user's sessions, else None.

    Gate for the upload endpoints — a user can't generate presigned URLs or
    register recordings for prompts they don't own.
    """
    result = await session.execute(
        select(Prompt)
        .join(DailySession, DailySession.id == Prompt.session_id)
        .where(Prompt.id == prompt_id, DailySession.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_session_topic_scores(
    session: AsyncSession, session_id: uuid.UUID
) -> tuple[list[dict], int]:
    """Return per-topic score blocks for a session + count of topics not yet
    fully scored. The dict shape matches the TopicScoreItem Pydantic schema
    (the router does the conversion).
    """
    # Imports done lazily to avoid a circular import (scoring → service is fine,
    # but service shouldn't reach into the scoring module's namespace at
    # import time).
    from app.unknownUnknowns.models import Score  # noqa: E402  (within fn)

    result = await session.execute(
        select(Prompt)
        .where(Prompt.session_id == session_id)
        .order_by(Prompt.order_index)
    )
    prompts = list(result.scalars().all())

    rows: list[dict] = []
    pending = 0
    for p in prompts:
        # Recordings for this prompt, indexed by kind.
        rec_result = await session.execute(
            select(Recording).where(Recording.prompt_id == p.id)
        )
        recordings = {r.kind: r for r in rec_result.scalars().all()}
        cold_r = recordings.get("cold")
        final_r = recordings.get("final")

        # Scores for the recordings, indexed by recording_id.
        score_lookup: dict[uuid.UUID, Score] = {}
        if cold_r or final_r:
            ids = [r.id for r in (cold_r, final_r) if r is not None]
            s_result = await session.execute(
                select(Score).where(Score.recording_id.in_(ids))
            )
            for s in s_result.scalars().all():
                score_lookup[s.recording_id] = s

        cold_s = score_lookup.get(cold_r.id) if cold_r else None
        final_s = score_lookup.get(final_r.id) if final_r else None

        topic_title = p.cold_prompt_text.rstrip("?").rstrip()

        if cold_s is not None and final_s is not None:
            metrics = []
            deltas: list[int] = []
            for label, cold_v, final_v in (
                ("Coverage", cold_s.coverage, final_s.coverage),
                ("Accuracy", cold_s.accuracy, final_s.accuracy),
                ("Structure", cold_s.structure, final_s.structure),
                ("Depth", cold_s.depth, final_s.depth),
                ("Clarity", cold_s.clarity, final_s.clarity),
            ):
                delta = final_v - cold_v
                deltas.append(delta)
                metrics.append(
                    {"label": label, "cold": cold_v, "final": final_v, "delta": delta}
                )
            net_delta = round(sum(deltas) / len(deltas), 1)
            rows.append(
                {
                    "prompt_id": p.id,
                    "order_index": p.order_index,
                    "topic_title": topic_title,
                    "metrics": metrics,
                    "net_delta": net_delta,
                    "notes_md": p.scoring_notes_md,
                    "is_ready": True,
                }
            )
        else:
            pending += 1
            rows.append(
                {
                    "prompt_id": p.id,
                    "order_index": p.order_index,
                    "topic_title": topic_title,
                    "metrics": [],
                    "net_delta": None,
                    "notes_md": None,
                    "is_ready": False,
                }
            )

    return rows, pending


async def upsert_recording(
    session: AsyncSession,
    *,
    prompt_id: uuid.UUID,
    kind: str,
    s3_key: str,
) -> Recording:
    """Idempotent: if a recording exists for (prompt_id, kind), update its
    s3_key and clear the transcript (so the next transcription pass re-runs
    on the new audio). Otherwise create.

    Idempotency matters because the frontend may retry on flaky networks —
    we don't want duplicates blocked by the UNIQUE(prompt_id, kind)
    constraint, and the "second upload" should win.
    """
    result = await session.execute(
        select(Recording).where(
            Recording.prompt_id == prompt_id,
            Recording.kind == kind,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.s3_key = s3_key
        existing.transcript = None
        existing.transcribed_at = None
        await session.commit()
        await session.refresh(existing)
        return existing

    recording = Recording(prompt_id=prompt_id, kind=kind, s3_key=s3_key)
    session.add(recording)
    await session.commit()
    await session.refresh(recording)
    return recording
