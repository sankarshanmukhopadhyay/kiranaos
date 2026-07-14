from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name:               str  = "KiranaOS"
    app_version:            str  = "2.4.0"
    database_url:           str  = "sqlite:///./data/kiranaos.db"
    default_store_id:        int  = 1
    whatsapp_verify_token:  str  = "change-me-before-deploy"
    public_base_url:        str  = "http://localhost:8000"
    frontend_origin:        str  = "http://localhost:5173"
    twilio_auth_token:      str | None = None
    twilio_account_sid:     str | None = None
    twilio_whatsapp_from:   str | None = None
    whatsapp_provider:      str = "simulation"
    meta_whatsapp_token:    str | None = None
    meta_phone_number_id:   str | None = None
    provider_timeout_seconds: int = 20
    provider_retry_attempts: int = 1
    parse_confidence_threshold: float = 0.70
    ai_order_quota_per_day: int = 500
    catalog_enabled: bool = True
    staff_assignment_enabled: bool = True
    repeat_orders_enabled: bool = True
    ai_usage_tracking_enabled: bool = True
    payments_enabled: bool = True
    delivery_enabled: bool = True
    upi_webhook_secret:     str | None = None
    webhook_timestamp_tolerance_seconds: int = 300
    demo_mode:              bool = True
    auth_required:          bool = False
    jwt_secret:             str  = "change-me-before-deploy"
    jwt_expiry_minutes:     int  = 480
    password_pbkdf2_iterations: int = 310_000
    log_level:              str  = "INFO"

    # External service keys — all optional; features degrade gracefully without them
    google_vision_key_json: str | None = None
    openai_api_key:         str | None = None
    openai_transcription_model: str = "whisper-1"
    openai_parser_model: str = "gpt-4o-mini"
    sarvam_api_key: str | None = None
    sarvam_stt_model: str = "saaras:v2"
    sarvam_llm_model: str = "sarvam-m"
    stt_provider: Literal["openai", "sarvam", "none"] = "openai"
    ocr_provider: Literal["google_vision", "sarvam", "none"] = "google_vision"
    parser_ai_provider: Literal["openai", "sarvam", "none"] = "openai"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KIRANA_",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
