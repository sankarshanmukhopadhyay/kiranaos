"""Provider-dispatched voice transcription facade."""

import logging

from app.core.config import get_settings
from app.services.security import validate_external_media_url

logger = logging.getLogger(__name__)


async def transcribe_voice_note(media_url: str, media_type: str | None = None) -> str | None:
    """Transcribe a WhatsApp voice note using the configured STT provider."""
    settings = get_settings()
    if settings.stt_provider == "none":
        return None
    validate_external_media_url(media_url)
    try:
        if settings.stt_provider == "sarvam":
            from app.services.stt.sarvam import transcribe
            return await transcribe(media_url, media_type)
        from app.services.stt.openai_whisper import transcribe
        return await transcribe(media_url, media_type)
    except Exception as exc:
        logger.warning("Voice transcription failed via %s: %s", settings.stt_provider, exc)
        return None
