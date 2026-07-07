"""
ocr/__init__.py — OCR provider dispatch.

ingestion.py depends only on `extract_text(media_url)`. Which
underlying provider actually runs is controlled entirely by
KIRANA_OCR_PROVIDER ("google_vision" | "sarvam" | "none"), defaulting
to "google_vision" so existing deployments see no behaviour change.
"""

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def extract_text(media_url: str) -> str:
    provider = get_settings().ocr_provider

    if provider == "google_vision":
        from app.services.ocr import google_vision
        return await google_vision.extract_text(media_url)
    if provider == "sarvam":
        from app.services.ocr import sarvam_vision
        return await sarvam_vision.extract_text(media_url)
    if provider == "none":
        return ""

    logger.warning("Unknown KIRANA_OCR_PROVIDER=%r; no OCR performed", provider)
    return ""
