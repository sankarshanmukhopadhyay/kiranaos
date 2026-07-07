"""
llm/__init__.py — Parser-fallback LLM provider dispatch.

ingestion.py depends only on `extract_items(text)`. Which underlying
provider actually runs is controlled entirely by
KIRANA_PARSER_AI_PROVIDER ("openai" | "sarvam" | "none"), defaulting to
"openai" so existing deployments see no behaviour change.
"""

import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def extract_items(text: str) -> list[str] | None:
    provider = get_settings().parser_ai_provider

    if provider == "openai":
        from app.services.llm import openai_chat
        return openai_chat.extract_items(text)
    if provider == "sarvam":
        from app.services.llm import sarvam_chat
        return sarvam_chat.extract_items(text)
    if provider == "none":
        return None

    logger.warning("Unknown KIRANA_PARSER_AI_PROVIDER=%r; no AI fallback performed", provider)
    return None
