"""
test_sarvam_adapters.py — Conformance tests for the Sarvam AI provider adapters.

These tests never make a real network call and never require a real
SARVAM_API_KEY. They validate two things per adapter:
  1. A passing case: given a well-formed mocked API response, the
     adapter returns correctly parsed data.
  2. A failing case: given an unconfigured key, a malformed response,
     or an HTTP error, the adapter degrades to its documented failure
     value (None / "" ) rather than raising — this is what lets
     ingestion.py's needs_review fallback work.

Run with: pytest backend/tests/test_sarvam_adapters.py -v
"""

import httpx
import pytest
import respx

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def sarvam_configured(monkeypatch):
    monkeypatch.setenv("KIRANA_SARVAM_API_KEY", "test-key-not-real")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ── STT (Saaras) ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_sarvam_stt_transcribes_on_success(monkeypatch):
    from app.services.stt import sarvam
    monkeypatch.setattr(sarvam, "validate_external_media_url", lambda url: None)

    respx.get("https://storage.googleapis.com/kiranaos-test/voice.ogg").mock(
        return_value=httpx.Response(200, content=b"fake-audio-bytes")
    )
    respx.post("https://api.sarvam.ai/speech-to-text").mock(
        return_value=httpx.Response(200, json={"transcript": "atta 5kg, dal 1kg"})
    )

    result = await sarvam.transcribe("https://storage.googleapis.com/kiranaos-test/voice.ogg", "audio/ogg")
    assert result == "atta 5kg, dal 1kg"


@pytest.mark.asyncio
@respx.mock
async def test_sarvam_stt_returns_none_on_upstream_error(monkeypatch):
    from app.services.stt import sarvam
    monkeypatch.setattr(sarvam, "validate_external_media_url", lambda url: None)

    respx.get("https://storage.googleapis.com/kiranaos-test/voice.ogg").mock(
        return_value=httpx.Response(200, content=b"fake-audio-bytes")
    )
    respx.post("https://api.sarvam.ai/speech-to-text").mock(
        return_value=httpx.Response(503, json={"error": "upstream unavailable"})
    )

    result = await sarvam.transcribe("https://storage.googleapis.com/kiranaos-test/voice.ogg", "audio/ogg")
    assert result is None


# ── Vision OCR ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_sarvam_vision_extracts_text_on_success():
    from app.services.ocr import sarvam_vision

    respx.get("https://example.invalid/list.jpg").mock(
        return_value=httpx.Response(200, content=b"fake-image-bytes")
    )
    respx.post("https://api.sarvam.ai/vision/document-digitization").mock(
        return_value=httpx.Response(200, json={"text": "rice 10kg, tel 5L"})
    )

    result = await sarvam_vision.extract_text("https://example.invalid/list.jpg")
    assert result == "rice 10kg, tel 5L"


@pytest.mark.asyncio
@respx.mock
async def test_sarvam_vision_returns_empty_string_on_failure():
    from app.services.ocr import sarvam_vision

    respx.get("https://example.invalid/list.jpg").mock(
        return_value=httpx.Response(200, content=b"fake-image-bytes")
    )
    respx.post("https://api.sarvam.ai/vision/document-digitization").mock(
        return_value=httpx.Response(500)
    )

    result = await sarvam_vision.extract_text("https://example.invalid/list.jpg")
    assert result == ""


# ── LLM parser fallback (sarvam-30b) ─────────────────────────────────────────

@respx.mock
def test_sarvam_llm_extracts_items_on_success():
    from app.services.llm import sarvam_chat

    respx.post("https://api.sarvam.ai/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"items": ["atta 5kg", "toor dal 1kg"]}'}}
                ]
            },
        )
    )

    result = sarvam_chat.extract_items("atta panch kilo aur toor dal ek kilo")
    assert result == ["atta 5kg", "toor dal 1kg"]


@respx.mock
def test_sarvam_llm_returns_none_on_malformed_response():
    from app.services.llm import sarvam_chat

    respx.post("https://api.sarvam.ai/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})
    )

    result = sarvam_chat.extract_items("some text")
    assert result is None


# ── Provider dispatch ────────────────────────────────────────────────────────

def test_stt_dispatch_defaults_to_openai(monkeypatch):
    monkeypatch.delenv("KIRANA_STT_PROVIDER", raising=False)
    get_settings.cache_clear()
    assert get_settings().stt_provider == "openai"


def test_stt_dispatch_selects_sarvam(monkeypatch):
    monkeypatch.setenv("KIRANA_STT_PROVIDER", "sarvam")
    get_settings.cache_clear()
    assert get_settings().stt_provider == "sarvam"
    get_settings.cache_clear()


def test_ocr_dispatch_defaults_to_google_vision(monkeypatch):
    monkeypatch.delenv("KIRANA_OCR_PROVIDER", raising=False)
    get_settings.cache_clear()
    assert get_settings().ocr_provider == "google_vision"


def test_parser_ai_dispatch_defaults_to_openai(monkeypatch):
    monkeypatch.delenv("KIRANA_PARSER_AI_PROVIDER", raising=False)
    get_settings.cache_clear()
    assert get_settings().parser_ai_provider == "openai"
