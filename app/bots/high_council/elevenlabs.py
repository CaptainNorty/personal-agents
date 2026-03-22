import io

import httpx
from loguru import logger
from pydub import AudioSegment

from app.bots.high_council.council import VOICE_MAP
from app.config import settings

ELEVENLABS_API = "https://api.elevenlabs.io/v1"
SILENCE_MS = 1500


async def text_to_speech(text: str, voice_id: str) -> bytes:
    """Convert text to speech using ElevenLabs API with a specific voice. Returns OGG/Opus audio bytes."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_API}/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": settings.elevenlabs_api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
            },
            params={"output_format": "mp3_44100_128"},
        )
        if not resp.is_success:
            logger.error(f"ElevenLabs TTS failed: {resp.status_code} {resp.text}")
            raise RuntimeError(f"ElevenLabs TTS failed: {resp.status_code}")
        return resp.content


async def generate_council_audio(conclusions: list[tuple[str, str]]) -> bytes:
    """Generate stitched audio from all council member conclusions.

    Takes a list of (member_name, conclusion_text) tuples, generates TTS for each
    member using their assigned voice, and concatenates with silence between members.

    Returns OGG/Opus audio bytes ready for Telegram.
    """
    silence = AudioSegment.silent(duration=SILENCE_MS)
    combined = AudioSegment.empty()

    for member_name, conclusion_text in conclusions:
        voice_id = VOICE_MAP.get(member_name)
        if not voice_id:
            logger.warning(f"No voice ID for {member_name}, skipping audio")
            continue

        spoken_text = f"{member_name}: {conclusion_text}"
        audio_bytes = await text_to_speech(spoken_text, voice_id)
        segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))

        if len(combined) > 0:
            combined += silence
        combined += segment

    # Export as OGG/Opus for Telegram voice messages
    buffer = io.BytesIO()
    combined.export(buffer, format="ogg", codec="opus")
    return buffer.getvalue()
