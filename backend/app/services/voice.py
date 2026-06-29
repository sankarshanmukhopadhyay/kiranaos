import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx

from app.core.config import get_settings
from app.services.security import validate_external_media_url

logger = logging.getLogger(__name__)


async def transcribe_voice_note(media_url: str, media_type: str | None = None) -> str | None:
    """
    Transcribe a WhatsApp voice note using OpenAI's audio transcription endpoint.
    Returns None when not configured so ingestion can fall back to needs_review.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    validate_external_media_url(media_url)

    suffix = ".ogg"
    if media_type and "mpeg" in media_type:
        suffix = ".mp3"
    elif media_type and "wav" in media_type:
        suffix = ".wav"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            media = await client.get(media_url)
            media.raise_for_status()
            with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(media.content)
                tmp_path = Path(tmp.name)

            try:
                with tmp_path.open("rb") as audio:
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                        data={"model": settings.openai_transcription_model},
                        files={"file": (tmp_path.name, audio, media_type or "audio/ogg")},
                    )
                    response.raise_for_status()
                    return str(response.json().get("text") or "").strip() or None
            finally:
                tmp_path.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Voice transcription failed: %s", exc)
        return None
