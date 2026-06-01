"""
Pydantic DTOs (request and response shapes) for the Unknown Unknowns API.

Naming convention: `XxxRequest` for POST bodies, `XxxResponse` for endpoint
return shapes. Nested response shapes (e.g. `TodaySessionState`) keep names
short — the wrapper conveys context.

Spoiler hygiene: response shapes deliberately exclude content the user
shouldn't see at that stage. `TodaySessionResponse` returns only cold prompt
text — no briefings, no final-challenge prompts.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TodaySessionState(BaseModel):
    """Status of today's session for the current user. exists=False means
    the user hasn't started today's session yet (Home shows the Begin CTA)."""

    exists: bool
    prompt_count: int | None = None
    include_repeat: bool | None = None
    completed_at: datetime | None = None


class MeResponse(BaseModel):
    user_id: UUID
    email: str | None
    streak_count: int
    last_completed_date: date | None
    prefs: dict
    today: TodaySessionState


class SessionStartRequest(BaseModel):
    prompt_count: int = Field(ge=1, le=3)
    include_repeat: bool = False


class SessionStartResponse(BaseModel):
    session_id: UUID
    session_date: date
    prompt_count: int
    include_repeat: bool


class PromptItem(BaseModel):
    """Single prompt as exposed pre-recording. Only cold-prompt text is sent —
    briefings, finals, and curriculum bullets are intentionally absent."""

    id: UUID
    order_index: int
    category: str
    cold_prompt_text: str


class TodaySessionResponse(BaseModel):
    session_id: UUID
    prompts: list[PromptItem]


class FinalPromptItem(BaseModel):
    """Final-challenge prompt shape. `id` is the same UUID as the cold prompt
    (one Prompt row carries both texts) — upload uses the same prompt_id with
    kind='final'."""

    id: UUID
    order_index: int
    category: str
    final_prompt_text: str


class TodayFinalsResponse(BaseModel):
    session_id: UUID
    prompts: list[FinalPromptItem]


# ----- Recording upload pipeline -----


class PresignedUploadRequest(BaseModel):
    prompt_id: UUID
    kind: Literal["cold", "final"]


class PresignedUploadResponse(BaseModel):
    upload_url: str
    s3_key: str
    expires_in_seconds: int


class RecordingRegisterRequest(BaseModel):
    prompt_id: UUID
    kind: Literal["cold", "final"]
    s3_key: str


class RecordingRegisterResponse(BaseModel):
    recording_id: UUID
    transcription_status: Literal["pending", "completed"]


# ----- Briefings -----


class BriefingItem(BaseModel):
    """One topic's briefing. `briefing_md` is null while generation is
    pending; once non-null, it's the full assembled markdown."""

    prompt_id: UUID
    order_index: int
    briefing_md: str | None
    generated_at: datetime | None


class BriefingsResponse(BaseModel):
    session_id: UUID
    briefings: list[BriefingItem]
    pending_count: int
    status: Literal["pending", "partial", "complete"]


class BriefingGenerateResponse(BaseModel):
    """Returned by POST /briefings/generate — generation runs in the
    background; the client polls GET /briefings until status='complete'."""

    status: Literal["started", "complete"]
    pending_count: int


# ----- Session completion -----


class CompleteSessionResponse(BaseModel):
    """Result of POST /sessions/today/complete. completed_at is the moment
    today's session was marked done (idempotent re-calls return the original)."""

    completed_at: datetime
    streak_count: int
    next_content_status: Literal["scheduled", "already_present", "skipped"]


# ----- Scoring -----


class MetricScoreItem(BaseModel):
    label: Literal["Coverage", "Accuracy", "Structure", "Depth", "Clarity"]
    cold: int
    final: int
    delta: int


class TopicScoreItem(BaseModel):
    """Per-topic score row. `metrics` is empty until both cold + final
    scores exist; `net_delta` and `notes_md` are likewise null until ready."""

    prompt_id: UUID
    order_index: int
    topic_title: str
    metrics: list[MetricScoreItem]
    net_delta: float | None
    notes_md: str | None
    is_ready: bool


class ScoresResponse(BaseModel):
    session_id: UUID
    scores: list[TopicScoreItem]
    pending_count: int
    status: Literal["pending", "partial", "complete"]


class ScoringGenerateResponse(BaseModel):
    """POST /scores/generate — generation runs in the background, client
    polls GET /scores until status='complete'."""

    status: Literal["started", "complete"]
    pending_count: int
