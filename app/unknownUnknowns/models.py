import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, BaseModel


class User(Base, BaseModel):
    __tablename__ = "uu_users"
    __table_args__ = (Index("idx_uu_users_firebase_uid", "firebase_uid"),)

    firebase_uid: Mapped[str] = mapped_column(Text, unique=True)
    email: Mapped[str | None] = mapped_column(Text, default=None)
    streak_count: Mapped[int] = mapped_column(default=0)
    last_completed_date: Mapped[date | None] = mapped_column(default=None)
    prefs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class DailySession(Base, BaseModel):
    __tablename__ = "uu_daily_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "session_date", name="uq_uu_daily_sessions_user_date"),
        CheckConstraint("prompt_count BETWEEN 1 AND 3", name="ck_uu_daily_sessions_prompt_count"),
        Index("idx_uu_daily_sessions_user_date", "user_id", "session_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column()
    session_date: Mapped[date] = mapped_column()
    prompt_count: Mapped[int] = mapped_column()
    include_repeat: Mapped[bool] = mapped_column(default=False)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)


class Prompt(Base, BaseModel):
    __tablename__ = "uu_prompts"
    __table_args__ = (
        UniqueConstraint("session_id", "order_index", name="uq_uu_prompts_session_order"),
        Index("idx_uu_prompts_session", "session_id"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column()
    category: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column()
    cold_prompt_text: Mapped[str] = mapped_column(Text)
    curriculum_bullets: Mapped[list[str]] = mapped_column(JSONB)
    briefing_md: Mapped[str | None] = mapped_column(Text, default=None)
    briefing_generated_at: Mapped[datetime | None] = mapped_column(default=None)
    final_prompt_text: Mapped[str] = mapped_column(Text)
    source_prompt_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    # Per-topic synthesis paragraph generated alongside scores (one paragraph
    # explaining what changed between cold and final). Lives on the prompt
    # so it stays close to the topic, not split across two recordings.
    scoring_notes_md: Mapped[str | None] = mapped_column(Text, default=None)


class Recording(Base, BaseModel):
    """Forward-looking — schema in place, no endpoints use it in the bootstrap slice."""

    __tablename__ = "uu_recordings"
    __table_args__ = (
        UniqueConstraint("prompt_id", "kind", name="uq_uu_recordings_prompt_kind"),
        Index("idx_uu_recordings_prompt", "prompt_id"),
    )

    prompt_id: Mapped[uuid.UUID] = mapped_column()
    kind: Mapped[str] = mapped_column(Text)
    s3_key: Mapped[str] = mapped_column(Text)
    transcript: Mapped[str | None] = mapped_column(Text, default=None)
    transcribed_at: Mapped[datetime | None] = mapped_column(default=None)


class Score(Base, BaseModel):
    """Forward-looking — schema in place, no endpoints use it in the bootstrap slice."""

    __tablename__ = "uu_scores"
    __table_args__ = (
        CheckConstraint("coverage BETWEEN 1 AND 10", name="ck_uu_scores_coverage"),
        CheckConstraint("accuracy BETWEEN 1 AND 10", name="ck_uu_scores_accuracy"),
        CheckConstraint("structure BETWEEN 1 AND 10", name="ck_uu_scores_structure"),
        CheckConstraint("depth BETWEEN 1 AND 10", name="ck_uu_scores_depth"),
        CheckConstraint("clarity BETWEEN 1 AND 10", name="ck_uu_scores_clarity"),
    )

    recording_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    coverage: Mapped[int] = mapped_column()
    accuracy: Mapped[int] = mapped_column()
    structure: Mapped[int] = mapped_column()
    depth: Mapped[int] = mapped_column()
    clarity: Mapped[int] = mapped_column()
    notes_md: Mapped[str | None] = mapped_column(Text, default=None)
