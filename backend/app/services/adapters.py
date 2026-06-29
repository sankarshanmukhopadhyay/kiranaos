"""Provider and AI adapters kept outside core parser/business logic."""

import base64
import hashlib
import hmac
import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings


def validate_twilio_signature(signature: str | None, url: str, params: dict[str, str]) -> bool:
    """Validate Twilio X-Twilio-Signature without depending on the Twilio SDK."""
    settings = get_settings()
    token = settings.twilio_auth_token
    if not token:
        return settings.demo_mode
    if not signature:
        return False

    payload = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(token.encode(), payload.encode(), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature)


def extract_items_with_openai(text: str) -> list[str] | None:
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
