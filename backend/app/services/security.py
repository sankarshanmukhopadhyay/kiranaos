"""Security helpers for auth, webhook validation, CORS, and outbound fetch safety."""

import hashlib
import hmac
import ipaddress
import socket
from time import time
from urllib.parse import urlparse

from app.core.config import get_settings

DEFAULT_SECRET_MARKERS = {"", "change-me", "change-me-before-deploy", "secret", "password"}


def is_default_secret(value: str | None) -> bool:
    return (value or "").strip().lower() in DEFAULT_SECRET_MARKERS


def assert_secure_runtime_config() -> None:
    """Fail closed when production-style flags are enabled with demo secrets."""
    settings = get_settings()
    if settings.auth_required and is_default_secret(settings.jwt_secret):
        raise RuntimeError("KIRANA_JWT_SECRET must be changed when KIRANA_AUTH_REQUIRED=true")
    if not settings.demo_mode and is_default_secret(settings.whatsapp_verify_token):
        raise RuntimeError("KIRANA_WHATSAPP_VERIFY_TOKEN must be changed when KIRANA_DEMO_MODE=false")
    if not settings.demo_mode and not settings.frontend_origin:
        raise RuntimeError("KIRANA_FRONTEND_ORIGIN must be set when KIRANA_DEMO_MODE=false")


def cors_origins() -> list[str]:
    settings = get_settings()
    raw = (settings.frontend_origin or "").strip()
    if raw == "*" and not settings.demo_mode:
        raise RuntimeError("Wildcard CORS is not allowed when KIRANA_DEMO_MODE=false")
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _is_public_host(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for item in addresses:
        ip = ipaddress.ip_address(item[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def validate_external_media_url(url: str) -> None:
    """Block SSRF-prone media URLs before OCR/transcription fetches."""
    settings = get_settings()
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError("Media URL must use http or https")
    if not parsed.hostname:
        raise ValueError("Media URL must include a hostname")
    if parsed.scheme == "http" and not settings.demo_mode:
        raise ValueError("Plain HTTP media URLs are disabled outside demo mode")
    if not _is_public_host(parsed.hostname):
        raise ValueError("Media URL host is not publicly routable")


def verify_upi_webhook_signature(
    body: bytes,
    signature: str | None,
    timestamp: str | None,
) -> bool:
    """Verify HMAC-SHA256 over '<timestamp>.<body>' for external UPI callbacks."""
    settings = get_settings()
    if not settings.upi_webhook_secret:
        return settings.demo_mode
    if not signature or not timestamp:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(int(time()) - ts) > settings.webhook_timestamp_tolerance_seconds:
        return False
    signed = timestamp.encode() + b"." + body
    expected = hmac.new(settings.upi_webhook_secret.encode(), signed, hashlib.sha256).hexdigest()
    supplied = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, supplied)
