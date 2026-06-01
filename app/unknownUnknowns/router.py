"""
FastAPI router for Unknown Unknowns — bootstrap slice.

Three endpoints mounted under /api/v1/uu:

    GET  /me                       — current user + today's session state
    POST /sessions/today/start     — initialize today's session (idempotent)
    GET  /sessions/today           — today's prompts (cold text only)

All endpoints depend on `get_current_user` (currently the stub dev user) and
`get_db` (the existing async sessionmaker).
"""

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth import get_current_user
from app.db.session import get_db
from app.unknownUnknowns import service
from app.unknownUnknowns.models import User


async def get_user_today(x_user_timezone: str | None = Header(default=None)) -> date:
    """Resolve the caller's local date from the X-User-Timezone header.

    The frontend sends an IANA tz string (e.g. 'America/Denver') from
    Intl.DateTimeFormat().resolvedOptions().timeZone. We compute "today" in
    that zone so the daily-ritual boundary matches local midnight rather
    than the server's UTC midnight. Falls back to UTC if missing/invalid.
    """
    return service.today_in_tz(x_user_timezone)
from app.unknownUnknowns.briefing_generator import generate_briefings_for_session
from app.unknownUnknowns.content_generator import (
    PENDING_TOPICS_PREFS_KEY,
    populate_pending_topics_for_user,
)
from app.unknownUnknowns.schemas import (
    BriefingGenerateResponse,
    BriefingItem,
    BriefingsResponse,
    CompleteSessionResponse,
    FinalPromptItem,
    MeResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
    PromptItem,
    RecordingRegisterRequest,
    RecordingRegisterResponse,
    ScoresResponse,
    ScoringGenerateResponse,
    SessionStartRequest,
    SessionStartResponse,
    TodayFinalsResponse,
    TodaySessionResponse,
    TodaySessionState,
    TopicScoreItem,
)
from app.unknownUnknowns.scoring import score_session
from app.unknownUnknowns.storage import (
    PRESIGNED_PUT_TTL_SECONDS,
    build_s3_key,
    generate_presigned_put,
)
from app.unknownUnknowns.transcription import transcribe_recording

router = APIRouter(prefix="/api/v1/uu", tags=["unknown-unknowns"])


@router.get("/me", response_model=MeResponse)
async def me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    today: date = Depends(get_user_today),
) -> MeResponse:
    daily = await service.find_today_session(session, user.id, today=today)
    today_state = TodaySessionState(
        exists=daily is not None,
        prompt_count=daily.prompt_count if daily else None,
        include_repeat=daily.include_repeat if daily else None,
        completed_at=daily.completed_at if daily else None,
    )
    return MeResponse(
        user_id=user.id,
        email=user.email,
        streak_count=user.streak_count,
        last_completed_date=user.last_completed_date,
        prefs=user.prefs or {},
        today=today_state,
    )


@router.post("/sessions/today/start", response_model=SessionStartResponse)
async def start_today(
    body: SessionStartRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    today: date = Depends(get_user_today),
) -> SessionStartResponse:
    daily = await service.get_or_create_today_session(
        session=session,
        user=user,
        prompt_count=body.prompt_count,
        include_repeat=body.include_repeat,
        today=today,
    )
    return SessionStartResponse(
        session_id=daily.id,
        session_date=daily.session_date,
        prompt_count=daily.prompt_count,
        include_repeat=daily.include_repeat,
    )


@router.get("/sessions/today", response_model=TodaySessionResponse)
async def get_today(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    today: date = Depends(get_user_today),
) -> TodaySessionResponse:
    daily = await service.find_today_session(session, user.id, today=today)
    if daily is None:
        raise HTTPException(
            status_code=404,
            detail="No session today. POST /api/v1/uu/sessions/today/start first.",
        )
    prompts = await service.get_session_prompts(session, daily.id)
    return TodaySessionResponse(
        session_id=daily.id,
        prompts=[
            PromptItem(
                id=p.id,
                order_index=p.order_index,
                category=p.category,
                cold_prompt_text=p.cold_prompt_text,
            )
            for p in prompts
        ],
    )


@router.get("/sessions/today/final-prompts", response_model=TodayFinalsResponse)
async def get_today_finals(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    today: date = Depends(get_user_today),
) -> TodayFinalsResponse:
    """Final-challenge prompts for today's session — new angles on the same
    topics the user already covered cold.

    TODO: gate by "all briefings viewed" once we track that. For now the
    frontend only fetches at the right moment, which is good enough for v1.
    """
    daily = await service.find_today_session(session, user.id, today=today)
    if daily is None:
        raise HTTPException(
            status_code=404,
            detail="No session today. POST /api/v1/uu/sessions/today/start first.",
        )
    prompts = await service.get_session_prompts(session, daily.id)
    return TodayFinalsResponse(
        session_id=daily.id,
        prompts=[
            FinalPromptItem(
                id=p.id,
                order_index=p.order_index,
                category=p.category,
                final_prompt_text=p.final_prompt_text,
            )
            for p in prompts
        ],
    )


@router.post("/uploads/presigned", response_model=PresignedUploadResponse)
async def presigned_upload(
    body: PresignedUploadRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PresignedUploadResponse:
    """Return a presigned PUT URL so the browser can upload audio directly
    to S3 without the bytes touching FastAPI."""
    prompt = await service.find_prompt_for_user(session, body.prompt_id, user.id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found.")

    s3_key = build_s3_key(user.id, prompt.id, body.kind)
    url = generate_presigned_put(s3_key)
    return PresignedUploadResponse(
        upload_url=url,
        s3_key=s3_key,
        expires_in_seconds=PRESIGNED_PUT_TTL_SECONDS,
    )


@router.post(
    "/sessions/today/scores/generate", response_model=ScoringGenerateResponse
)
async def kick_off_scoring(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    today: date = Depends(get_user_today),
) -> ScoringGenerateResponse:
    """Kick off end-of-day scoring for today's session. Idempotent: if every
    topic already has both cold + final scores, returns 'complete' without
    re-running. Otherwise schedules background scoring (waits for any missing
    transcripts up to 90s each, then scores in parallel per topic)."""
    daily = await service.find_today_session(session, user.id, today=today)
    if daily is None:
        raise HTTPException(
            status_code=404,
            detail="No session today. POST /api/v1/uu/sessions/today/start first.",
        )

    rows, pending = await service.get_session_topic_scores(session, daily.id)
    if pending == 0:
        return ScoringGenerateResponse(status="complete", pending_count=0)

    background_tasks.add_task(score_session, daily.id)
    return ScoringGenerateResponse(status="started", pending_count=pending)


@router.get("/sessions/today/scores", response_model=ScoresResponse)
async def get_scores(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    today: date = Depends(get_user_today),
) -> ScoresResponse:
    """Poll endpoint for scoring progress. Returns per-topic blocks; topics
    not yet scored have empty metrics and null deltas/notes."""
    daily = await service.find_today_session(session, user.id, today=today)
    if daily is None:
        raise HTTPException(
            status_code=404,
            detail="No session today.",
        )

    rows, pending = await service.get_session_topic_scores(session, daily.id)
    scores = [TopicScoreItem(**r) for r in rows]
    if pending == len(scores):
        status = "pending"
    elif pending == 0:
        status = "complete"
    else:
        status = "partial"
    return ScoresResponse(
        session_id=daily.id,
        scores=scores,
        pending_count=pending,
        status=status,
    )


@router.post("/sessions/today/complete", response_model=CompleteSessionResponse)
async def complete_today(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    today: date = Depends(get_user_today),
) -> CompleteSessionResponse:
    """Mark today's session done, update streak, and kick off generation of
    tomorrow's topics in the background.

    Idempotent: re-calling returns the original completed_at without changing
    streak. If the pending-topics pool is already populated (3+), we skip
    re-running the generator.
    """
    daily = await service.find_today_session(session, user.id, today=today)
    if daily is None:
        raise HTTPException(
            status_code=404,
            detail="No session today to complete.",
        )

    state_changed = await service.mark_session_complete(
        session, user, daily, today=today
    )

    pool_size = len((user.prefs or {}).get(PENDING_TOPICS_PREFS_KEY) or [])
    if pool_size >= 3:
        next_content_status = "already_present"
    elif state_changed:
        background_tasks.add_task(populate_pending_topics_for_user, user.id, 3)
        next_content_status = "scheduled"
    else:
        # Already completed earlier, pool not yet full — no rekick to avoid
        # duplicate generators in flight. Caller can refetch /me later.
        next_content_status = "skipped"

    # daily.completed_at is naive UTC; reattach for the response.
    return CompleteSessionResponse(
        completed_at=daily.completed_at.replace(tzinfo=None),
        streak_count=user.streak_count or 0,
        next_content_status=next_content_status,
    )


@router.post(
    "/sessions/today/briefings/generate", response_model=BriefingGenerateResponse
)
async def kick_off_briefing_generation(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    today: date = Depends(get_user_today),
) -> BriefingGenerateResponse:
    """Kick off post-cold-record briefing generation for today's session.

    Idempotent: if every briefing is already present, returns 'complete'
    without re-running. Otherwise schedules a background task that:
      - waits for any missing cold transcripts (up to 90s each)
      - generates briefings for prompts that need them, in parallel
    The client polls GET /sessions/today/briefings until status='complete'.
    """
    daily = await service.find_today_session(session, user.id, today=today)
    if daily is None:
        raise HTTPException(
            status_code=404,
            detail="No session today. POST /api/v1/uu/sessions/today/start first.",
        )

    prompts = await service.get_session_prompts(session, daily.id)
    pending = sum(1 for p in prompts if p.briefing_md is None)
    if pending == 0:
        return BriefingGenerateResponse(status="complete", pending_count=0)

    background_tasks.add_task(generate_briefings_for_session, daily.id)
    return BriefingGenerateResponse(status="started", pending_count=pending)


@router.get("/sessions/today/briefings", response_model=BriefingsResponse)
async def get_briefings(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    today: date = Depends(get_user_today),
) -> BriefingsResponse:
    """Poll endpoint for briefing generation progress.

    status is 'pending' (none ready), 'partial' (some ready), or 'complete'
    (all ready). The client typically polls every 1-2s until 'complete'.
    """
    daily = await service.find_today_session(session, user.id, today=today)
    if daily is None:
        raise HTTPException(
            status_code=404,
            detail="No session today. POST /api/v1/uu/sessions/today/start first.",
        )

    prompts = await service.get_session_prompts(session, daily.id)
    briefings = [
        BriefingItem(
            prompt_id=p.id,
            order_index=p.order_index,
            briefing_md=p.briefing_md,
            generated_at=p.briefing_generated_at,
        )
        for p in prompts
    ]
    pending = sum(1 for b in briefings if b.briefing_md is None)
    if pending == len(briefings):
        status = "pending"
    elif pending == 0:
        status = "complete"
    else:
        status = "partial"
    return BriefingsResponse(
        session_id=daily.id,
        briefings=briefings,
        pending_count=pending,
        status=status,
    )


@router.post("/recordings", response_model=RecordingRegisterResponse)
async def register_recording(
    body: RecordingRegisterRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RecordingRegisterResponse:
    """Register a completed S3 upload. Idempotent on (prompt_id, kind).
    Kicks off background transcription after the response is sent."""
    prompt = await service.find_prompt_for_user(session, body.prompt_id, user.id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found.")

    recording = await service.upsert_recording(
        session,
        prompt_id=body.prompt_id,
        kind=body.kind,
        s3_key=body.s3_key,
    )
    background_tasks.add_task(transcribe_recording, recording.id)
    return RecordingRegisterResponse(
        recording_id=recording.id,
        transcription_status="pending",
    )
