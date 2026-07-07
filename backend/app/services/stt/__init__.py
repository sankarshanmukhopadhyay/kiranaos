"""
stt/__init__.py — Speech-to-text provider dispatch.

ingestion.py depends only on `transcribe_voice_note(media_url, media_type)`.
Which underlying provider actually runs is controlled entirely by
KIRANA_STT_PROVIDER ("openai" | "sarvam" | "none"), defaulting to
"openai" so existing deployments see no behaviour change.
"""

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def transcribe_voice_note(media_url: str, media_type: str | None = None) -> str | None:
    provider = get_settings().stt_provider

    if provider == "openai":
        from app.services.stt import openai_whisper
        return await openai_whisper.transcribe(media_url, media_type)
    if provider == "sarvam":
        from app.services.stt import sarvam
        return await sarvam.transcribe(media_url, media_type)
    if provider == "none":
        return None

    logger.warning("Unknown KIRANA_STT_PROVIDER=%r; no transcription performed", provider)
    return None
