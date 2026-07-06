"""Provider and AI adapters kept outside core parser/business logic."""

import base64
import hashlib
import hmac
import json
from urllib.parse import urlencode
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


def send_twilio_whatsapp(to_phone: str, body: str) -> str:
    settings = get_settings()
    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_whatsapp_from:
        raise RuntimeError("Twilio outbound WhatsApp is not fully configured")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    payload = urlencode({
        "From": settings.twilio_whatsapp_from,
        "To": f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone,
        "Body": body,
    }).encode()
    auth = base64.b64encode(f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()).decode()
    request = Request(
        url,
        data=payload,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=settings.provider_timeout_seconds) as response:
        data = json.loads(response.read().decode())
    return str(data.get("sid") or "")


def send_meta_whatsapp(to_phone: str, body: str) -> str:
    settings = get_settings()
    if not settings.meta_whatsapp_token or not settings.meta_phone_number_id:
        raise RuntimeError("Meta outbound WhatsApp is not fully configured")

    url = f"https://graph.facebook.com/v20.0/{settings.meta_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone.replace("+", ""),
        "type": "text",
        "text": {"body": body},
    }
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {settings.meta_whatsapp_token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=settings.provider_timeout_seconds) as response:
        data = json.loads(response.read().decode())
    messages = data.get("messages") or []
    return str(messages[0].get("id") if messages else "")
