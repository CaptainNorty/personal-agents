import asyncio

import httpx
from loguru import logger

from app.config import settings

ASSEMBLYAI_BASE = "https://api.assemblyai.com/v2"
POLL_INTERVAL = 5  # seconds
MAX_TIMEOUT = 1800  # 30 minutes


async def transcribe_audio(url: str) -> str:
    """Transcribe audio from a URL using AssemblyAI."""
    headers = {"authorization": settings.assemblyai_api_key}

    async with httpx.AsyncClient(timeout=30) as client:
        # Submit transcription request
        resp = await client.post(
            f"{ASSEMBLYAI_BASE}/transcript",
            headers=headers,
            json={"audio_url": url, "speech_models": ["universal-3-pro"]},
        )
        if resp.status_code != 200:
            logger.error(f"AssemblyAI submit failed ({resp.status_code}): {resp.text}")
            resp.raise_for_status()
        transcript_id = resp.json()["id"]
        logger.info(f"AssemblyAI transcription submitted: {transcript_id}")

        # Poll until complete
        elapsed = 0
        while elapsed < MAX_TIMEOUT:
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

            resp = await client.get(
                f"{ASSEMBLYAI_BASE}/transcript/{transcript_id}",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data["status"]

            if status == "completed":
                logger.info(f"Transcription complete: {transcript_id}")
                return data["text"]
            elif status == "error":
                raise RuntimeError(f"AssemblyAI transcription failed: {data.get('error', 'unknown error')}")

            logger.debug(f"Transcription {transcript_id} status: {status} ({elapsed}s elapsed)")

        raise TimeoutError(f"Transcription {transcript_id} timed out after {MAX_TIMEOUT}s")
