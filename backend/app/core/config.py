import os
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Marathon Registration & Marketing Automation Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Event Constants
    EVENT_NAME: str = "City Marathon 2026"
    EVENT_DATE: str = "Sunday, October 18, 2026"
    EVENT_VENUE: str = "Kanteerava Stadium, Bengaluru"
    EVENT_REPORTING_TIME: str = "05:00 AM"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Admin Security Configuration
    ADMIN_API_KEY: str = "marathon_admin_secret_2026"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://marathon_user:marathon_pass@localhost:5432/marathon_db"
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Ensure the database URL has the async driver prefix."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Synchronous database URL for Alembic migrations and synchronous scripts."""
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return url

    # Razorpay Payment Gateway (TEST MODE)
    RAZORPAY_KEY_ID: str = "rzp_test_placeholder"
    RAZORPAY_KEY_SECRET: str = "placeholder_secret"
    RAZORPAY_WEBHOOK_SECRET: str = "placeholder_webhook_secret"

    # Global Integration Mock Mode (Enables offline/deterministic mock adapters for testing)
    INTEGRATIONS_MOCK_MODE: bool = True

    # 1. Zoho CRM Configuration (Phase 5)
    ZOHO_ENABLED: bool = True
    ZOHO_MODE: str = "mock" # "mock" or "live"
    ZOHO_CLIENT_ID: str = ""
    ZOHO_CLIENT_SECRET: str = ""
    ZOHO_REFRESH_TOKEN: str = ""
    ZOHO_API_DOMAIN: str = "https://www.zohoapis.com"
    ZOHO_ACCOUNTS_URL: str = "https://accounts.zoho.com"
    ZOHO_ORG_ID: Optional[str] = None

    # 2. WhatsApp Business Cloud API Configuration
    WHATSAPP_ENABLED: bool = True
    WHATSAPP_MOCK_MODE: bool = True
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_API_VERSION: str = "v20.0"
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = "marathon_wa_verify_token_2026"

    # 3. n8n Automation Engine Configuration
    N8N_ENABLED: bool = True
    N8N_MOCK_MODE: bool = True
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_WEBHOOK_SECRET: str = "marathon_n8n_secret_2026"

    # 4. Meta Conversions API (CAPI) Configuration
    META_CAPI_ENABLED: bool = True
    META_CAPI_MOCK_MODE: bool = True
    META_PIXEL_ID: str = ""
    META_ACCESS_TOKEN: str = ""
    META_API_VERSION: str = "v20.0"
    META_TEST_EVENT_CODE: Optional[str] = None

    # Helper validation methods
    def is_zoho_configured(self) -> bool:
        return bool(self.ZOHO_CLIENT_ID and self.ZOHO_CLIENT_SECRET and self.ZOHO_REFRESH_TOKEN)

    def is_zoho_mock_active(self) -> bool:
        return (not self.ZOHO_ENABLED) or self.ZOHO_MODE.lower() == "mock" or self.INTEGRATIONS_MOCK_MODE or (not self.is_zoho_configured())

    def is_whatsapp_configured(self) -> bool:
        return bool(self.WHATSAPP_ENABLED and self.WHATSAPP_ACCESS_TOKEN and self.WHATSAPP_PHONE_NUMBER_ID)

    def is_whatsapp_mock_active(self) -> bool:
        return self.WHATSAPP_MOCK_MODE or self.INTEGRATIONS_MOCK_MODE or not self.is_whatsapp_configured()

    def is_n8n_configured(self) -> bool:
        return bool(self.N8N_ENABLED and self.N8N_BASE_URL and self.N8N_BASE_URL.startswith("http"))

    def is_n8n_mock_active(self) -> bool:
        return self.N8N_MOCK_MODE or self.INTEGRATIONS_MOCK_MODE or not self.is_n8n_configured()

    def is_meta_capi_configured(self) -> bool:
        return bool(self.META_CAPI_ENABLED and self.META_PIXEL_ID and self.META_ACCESS_TOKEN)

    def is_meta_capi_mock_active(self) -> bool:
        return self.META_CAPI_MOCK_MODE or self.INTEGRATIONS_MOCK_MODE or not self.is_meta_capi_configured()

    @staticmethod
    def mask_secret(secret: Optional[str]) -> str:
        """Safely mask API tokens and secrets for structured logging without exposing sensitive data."""
        if not secret:
            return "[NOT SET]"
        if len(secret) <= 8:
            return "***"
        return f"{secret[:4]}...{secret[-4:]}"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
