from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name:               str  = "KiranaOS"
    database_url:           str  = "sqlite:///./data/kiranaos.db"
    default_store_id:        int  = 1
    whatsapp_verify_token:  str  = "change-me-before-deploy"
    public_base_url:        str  = "http://localhost:8000"
    frontend_origin:        str  = "*"
    twilio_auth_token:      str | None = None
    twilio_account_sid:     str | None = None
    twilio_whatsapp_from:   str | None = None
    demo_mode:              bool = True
    auth_required:          bool = False
    jwt_secret:             str  = "change-me-before-deploy"
    jwt_expiry_minutes:     int  = 480
    log_level:              str  = "INFO"

    # External service keys — all optional; features degrade gracefully without them
    google_vision_key_json: str | None = None
    openai_api_key:         str | None = None
    openai_transcription_model: str = "whisper-1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KIRANA_",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
