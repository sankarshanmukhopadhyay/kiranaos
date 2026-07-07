"""
llm/sarvam_chat.py — Sarvam AI (sarvam-30b) parser-fallback adapter.

API reference (pinned): https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/chat-completion/overview
Model (pinned): sarvam-30b — OpenAI-compatible /v1/chat/completions,
2.4B active parameters (MoE), trained natively on code-mixed Indian
language input, which is precisely the "atta 5kg, toor dal 1kg" style
text this fallback receives. Use sarvam-105b instead for higher-quality
extraction if sarvam-30b's accuracy proves insufficient in practice —
same endpoint contract, swap the model string only.

Same contract as llm/openai_chat.py: `extract_items(text) -> list[str] | None`.
"""

import json

import httpx

from app.core.config import get_settings

_SARVAM_CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"

_SYSTEM_PROMPT = (
    "Extract grocery order items from Indian kirana WhatsApp messages in any "
    "language or mix of languages. Return JSON only as {\"items\": [\"...\"]}."
)


def extract_items(text: str) -> list[str] | None:
    """Return normalized grocery item labels using Sarvam when configured."""
    settings = get_settings()
    api_key = settings.sarvam_api_key
    if not api_key:
        return None

    body = {
        "model": settings.sarvam_llm_model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }

    try:
        response = httpx.post(
            _SARVAM_CHAT_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=settings.provider_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        parsed = json.loads(content)
    except (httpx.HTTPError, json.JSONDecodeError, KeyError):
        return None

    items = parsed.get("items")
    return [str(item) for item in items if item] if isinstance(items, list) else None
