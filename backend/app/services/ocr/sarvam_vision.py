"""
ocr/sarvam_vision.py — Sarvam AI Vision document-digitisation adapter.

API reference (pinned): https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/document-digitization/overview
Model family (pinned): Sarvam Vision — 3B state-space vision-language
model trained for OCR/layout extraction on Indian-script documents
(Devanagari, Tamil, Telugu, Kannada, Malayalam, Bengali, etc.), which
covers the handwritten/printed order-list photos this adapter receives.

Rate limit note: vis-doc-dig is capped at 10 req/min on every plan tier
(see docs.sarvam.ai/.../ratelimits) — uniform across Starter/Pro/Business.
A production deployment with higher photo-order volume should queue
these calls rather than assume linear scaling with plan upgrades.
"""

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SARVAM_VISION_URL = "https://api.sarvam.ai/vision/document-digitization"


async def extract_text(media_url: str) -> str:
    """
    Download an image from media_url and return extracted text via
    Sarvam Vision. Returns an empty string if not configured or on
    failure, matching ocr/google_vision.py's contract exactly.
    """
    settings = get_settings()
    if not settings.sarvam_api_key:
        return ""

    try:
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            image = await client.get(media_url)
            image.raise_for_status()

            response = await client.post(
                _SARVAM_VISION_URL,
                headers={"api-subscription-key": settings.sarvam_api_key},
                files={"file": ("order.jpg", image.content, "image/jpeg")},
            )
            response.raise_for_status()
            data = response.json()

        text = str(data.get("text") or "").strip()
        logger.info("Sarvam Vision OCR extracted %d chars from %s", len(text), media_url)
        return text

    except Exception as exc:
        logger.error("Sarvam Vision OCR extraction failed: %s", exc)
        return ""
