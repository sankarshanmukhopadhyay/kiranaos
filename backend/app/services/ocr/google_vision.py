"""
ocr/google_vision.py — Google Cloud Vision adapter for handwritten image OCR.

Architecture note: this module is an adapter. ingestion.py calls
`extract_text(media_url)` and receives plain text back. The parser
never knows where the text came from. Swap this file for a different
OCR provider without touching any other service.

Setup:
  Option A: Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
  Option B: Set KIRANA_GOOGLE_VISION_KEY_JSON to the JSON content directly
            (useful on Railway, Render, Fly.io where file mounts are awkward).
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# Lazily initialised to avoid import cost when OCR is not configured
_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    try:
        from google.cloud import vision  # type: ignore

        key_json_str = os.environ.get("KIRANA_GOOGLE_VISION_KEY_JSON")
        if key_json_str:
            credentials_info = json.loads(key_json_str)
            from google.oauth2 import service_account  # type: ignore
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            _client = vision.ImageAnnotatorClient(credentials=credentials)
        else:
            # Falls back to GOOGLE_APPLICATION_CREDENTIALS file
            _client = vision.ImageAnnotatorClient()

        return _client
    except ImportError:
        logger.warning(
            "google-cloud-vision not installed. "
            "Run: pip install google-cloud-vision"
        )
        return None
    except Exception as exc:
        logger.error("Failed to initialise Vision client: %s", exc)
        return None


async def extract_text(media_url: str) -> str:
    """
    Download an image from media_url and return extracted text via Google Vision.
    Returns an empty string if OCR is not configured or fails.
    """
    import httpx

    client = _get_client()
    if client is None:
        return ""

    try:
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.get(media_url)
            resp.raise_for_status()
            image_bytes = resp.content

        from google.cloud import vision  # type: ignore

        image = vision.Image(content=image_bytes)
        response = client.document_text_detection(
            image=image,
            image_context=vision.ImageContext(
                # Hint common Indian script languages for higher accuracy
                language_hints=["hi", "ta", "te", "kn", "ml", "mr", "bn", "en"]
            ),
        )

        if response.error.message:
            logger.error("Vision API error: %s", response.error.message)
            return ""

        text = response.full_text_annotation.text
        logger.info("OCR extracted %d chars from %s", len(text), media_url)
        return text

    except Exception as exc:
        logger.error("OCR extraction failed: %s", exc)
        return ""
