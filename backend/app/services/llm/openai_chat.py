"""
llm/openai_chat.py — OpenAI parser-fallback adapter (moved from adapters.py).

Used when the rule-based parser (parser.py) finds zero items in
extracted text; returns normalized grocery item labels for a second
parse pass, or None if not configured / on failure.
"""

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings


def extract_items(text: str) -> list[str] | None:
    """Return normalized grocery item labels using OpenAI when configured."""
    api_key = get_settings().openai_api_key
    if not api_key:
        return None

    body = {
        "model": "gpt-4o-mini",
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extract grocery order items from Indian kirana WhatsApp messages in any "
                    "language or mix of languages. Return JSON only as {\"items\": [\"...\"]}."
                ),
            },
            {"role": "user", "content": text},
        ],
    }
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        parsed = json.loads(content)
    except (URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None

    items = parsed.get("items")
    return [str(item) for item in items if item] if isinstance(items, list) else None
