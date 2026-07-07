"""
stt/sarvam.py — Sarvam AI (Saaras) speech-to-text adapter.

API reference (pinned): https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/speech-to-text/rest-api
Model (pinned): saaras:v3 — streaming-capable ASR for 22 Indian languages
with native code-mixed (Hinglish/Tanglish/etc.) support, which is the
dominant input pattern for KiranaOS voice orders.

Architecture note: this module is an adapter, matching the shape of
stt/openai_whisper.py. `transcribe(media_url, media_type)` is the only
contract ingestion.py depends on; either implementation can be selected
via KIRANA_STT_PROVIDER without touching ingestion.py.
"""

import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx

from app.core.config import get_settings
from app.services.security import validate_external_media_url

logger = logging.getLogger(__name__)

_SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"


async def transcribe(media_url: str, media_type: str | None = None) -> str | None:
    """
    Transcribe a WhatsApp voice note using Sarvam's Saaras STT endpoint.
    Returns None when not configured or on failure, so ingestion falls
    back to needs_review exactly as the OpenAI adapter does.
    """
    settings = get_settings()
    if not settings.sarvam_api_key:
        return None
    validate_external_media_url(media_url)

    suffix = ".ogg"
    if media_type and "mpeg" in media_type:
        suffix = ".mp3"
    elif media_type and "wav" in media_type:
        suffix = ".wav"

    try:
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            media = await client.get(media_url)
            media.raise_for_status()
            with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(media.content)
                tmp_path = Path(tmp.name)

            try:
                with tmp_path.open("rb") as audio:
                    response = await client.post(
                        _SARVAM_STT_URL,
                        headers={"api-subscription-key": settings.sarvam_api_key},
                        data={"model": settings.sarvam_stt_model},
                        files={"file": (tmp_path.name, audio, media_type or "audio/ogg")},
                    )
                    response.raise_for_status()
                    return str(response.json().get("transcript") or "").strip() or None
            finally:
                tmp_path.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Sarvam STT transcription failed: %s", exc)
        return None
