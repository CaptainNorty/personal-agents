"""
End-of-session content generation for Unknown Unknowns.

When the user finishes today's score reveal (POST /sessions/today/complete),
this module generates 3 topics for the user's next session and stashes them
in user.prefs.pending_topics. The next time POST /sessions/today/start runs,
those pending topics are consumed and become the day's Prompt rows.

Why end-of-session instead of a nightly cron (see DESIGN.md):
  • No timezone handling needed.
  • No "did the user show up today?" check — if they don't complete a session,
    no new content is generated; they pick up where they left off.
  • Simpler infra: no scheduler, no cron, no missed-run debugging.
"""

from __future__ import annotations

import uuid
from typing import Literal

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select

from app.common.llm import ask_claude_structured
from app.db.session import async_session
from app.unknownUnknowns.models import DailySession, Prompt, User

PENDING_TOPICS_PREFS_KEY = "pending_topics"


# ---------- LLM contract ----------

TOPIC_SYSTEM_PROMPT = """\
You're designing topics for a daily learning app built around the Illusion \
of Explanatory Depth. Each day, the user cold-records their best attempt at \
explaining a topic, then reads a briefing built from your curriculum \
bullets, then re-records on a new angle. You generate N topics with the \
structure needed to make this work.

For each topic produce:

- `category`: one of 'cultural' (history, literature, philosophy, geography, \
the humanities) or 'technical' (science, engineering, math, systems, \
quantitative thinking).
- `cold_prompt_text`: a concrete one-question prompt asked cold. \
Good: "Why is the sky blue?" or "What was the Treaty of Westphalia?" \
Bad: "Tell me about light." Should invite an explanation, not a yes/no.
- `curriculum_bullets`: 4-5 short statements naming the anchor concepts. \
Together they form a complete teaching of the topic for a curious \
generalist. Each bullet is a specific fact or principle, not a vague \
header.
- `final_prompt_text`: a *new-angle* question answerable from the curriculum \
bullets but NOT a rephrasing of the cold prompt. It should test transfer of \
understanding. Good: cold="Why is the sky blue?" final="Why does the sun \
look red at sunset?" Bad: cold="What is entropy?" final="Can you re-explain \
entropy?"

Guidelines:
- Mix categories across topics. If asked for 3, do roughly 1-2 technical + \
1-2 cultural.
- Pick interesting, non-trivial topics. Avoid tired pop-science clichés \
("how black holes work"), surface trivia ("when was X invented"), and \
anything that depends on current events.
- Each topic should be teachable in ~300-400 words.
- AVOID any topic the user has already covered (listed in the user message).

Tone: the kind of topics a brilliant friend with eclectic interests would \
push on you.\
"""


class GeneratedTopic(BaseModel):
    """LLM output schema per topic. Direct match for the persisted Prompt
    shape (minus session_id, order_index, briefing_md)."""

    category: Literal["cultural", "technical"]
    cold_prompt_text: str
    curriculum_bullets: list[str]
    final_prompt_text: str


class GeneratedDailyContent(BaseModel):
    topics: list[GeneratedTopic]


async def generate_topics(
    n: int, past_cold_prompts: list[str]
) -> list[GeneratedTopic]:
    """One LLM call: return N fresh topics avoiding the user's history."""
    past_block = "\n".join(f"- {p}" for p in past_cold_prompts) or "(none — first day)"
    user_prompt = (
        f"Generate {n} topic(s) for the user's next session.\n\n"
        f"Topics they've already covered (avoid these and anything that's a "
        f"near-relative):\n{past_block}\n\n"
        f"Return exactly {n} topics."
    )
    result = await ask_claude_structured(
        prompt=user_prompt,
        schema=GeneratedDailyContent,
        system=TOPIC_SYSTEM_PROMPT,
        cache_system=True,
        effort="high",
        max_tokens=12_000,
    )
    return result.topics[:n]


# ---------- DB-side helpers (prefs.pending_topics is the queue) ----------


def _topics_from_prefs(prefs: dict | None) -> list[dict]:
    if not prefs:
        return []
    raw = prefs.get(PENDING_TOPICS_PREFS_KEY) or []
    return list(raw)


def _set_topics_in_prefs(prefs: dict | None, topics: list[dict]) -> dict:
    new_prefs = dict(prefs or {})
    new_prefs[PENDING_TOPICS_PREFS_KEY] = topics
    return new_prefs


async def populate_pending_topics_for_user(user_id: uuid.UUID, n: int = 3) -> None:
    """Background task — generate N topics for the user and store them in
    prefs.pending_topics. Idempotent: if pending_topics already has ≥ N
    entries, no-op."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            logger.warning(f"[uu content gen] User {user_id} not found — skipping.")
            return

        existing = _topics_from_prefs(user.prefs)
        if len(existing) >= n:
            logger.info(
                f"[uu content gen] User {user_id} already has {len(existing)} "
                f"pending topic(s) — skipping generation."
            )
            return

        # Gather past cold prompts from this user's history.
        past_result = await session.execute(
            select(Prompt.cold_prompt_text)
            .join(DailySession, DailySession.id == Prompt.session_id)
            .where(DailySession.user_id == user_id)
        )
        past_cold_prompts = [row[0] for row in past_result.all()]

    logger.info(
        f"[uu content gen] Generating {n} topic(s) for user {user_id} "
        f"({len(past_cold_prompts)} past topic(s) to avoid)."
    )
    try:
        topics = await generate_topics(n, past_cold_prompts)
    except Exception:
        logger.exception(f"[uu content gen] Generation failed for user {user_id}.")
        return

    # Persist as plain JSON in user.prefs.
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        merged = _topics_from_prefs(user.prefs) + [t.model_dump() for t in topics]
        user.prefs = _set_topics_in_prefs(user.prefs, merged)
        await session.commit()
        logger.info(
            f"[uu content gen] Stored {len(topics)} topic(s) for user {user_id} "
            f"(pool size now {len(merged)})."
        )
