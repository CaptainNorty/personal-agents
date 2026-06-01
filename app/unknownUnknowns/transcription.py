"""
Background transcription task for UU recordings.

Called from POST /recordings via FastAPI BackgroundTasks. The endpoint returns
immediately; transcription happens after the response is sent.

Flow:
    1. Look up the recording row by id.
    2. Generate a short-lived presigned GET URL for its S3 key.
    3. Hand the URL to AssemblyAI (existing app/common/audio.py helper).
    4. Persist the returned transcript on the row.

Failures log but don't raise — the recording row keeps transcript=null and the
frontend can retry later (a retry mechanism isn't wired yet; for now, surface
the gap via the null transcript).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.common.audio import transcribe_audio
from app.db.session import async_session
from app.unknownUnknowns.models import Recording
from app.unknownUnknowns.storage import generate_presigned_get


async def transcribe_recording(recording_id: uuid.UUID) -> None:
    """Background task: fetch transcript for a recording, persist it on the row.

    Creates its own DB session because the request-scope session that
    scheduled this task has already closed by the time it runs.
    """
    async with async_session() as session:
        result = await session.execute(
            select(Recording).where(Recording.id == recording_id)
        )
        recording = result.scalar_one_or_none()
        if recording is None:
            logger.warning(
                f"[uu transcription] Recording {recording_id} not found — skipping."
            )
            return

        if recording.transcript is not None:
            logger.info(
                f"[uu transcription] Recording {recording_id} already transcribed — skipping."
            )
            return

        audio_url = generate_presigned_get(recording.s3_key)
        logger.info(
            f"[uu transcription] Starting AssemblyAI for recording {recording_id} "
            f"(s3_key={recording.s3_key})"
        )

        try:
            transcript = await transcribe_audio(audio_url)
        except Exception:
            logger.exception(
                f"[uu transcription] Failed for recording {recording_id} — "
                "leaving transcript=null."
            )
            return

        recording.transcript = transcript
        # The column is TIMESTAMP WITHOUT TIME ZONE (matches the rest of the
        # BaseModel mixin). Pass a naive-UTC value to keep the wire format clean.
        recording.transcribed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.commit()
        logger.info(
            f"[uu transcription] Stored transcript for recording {recording_id} "
            f"({len(transcript)} chars)"
        )
