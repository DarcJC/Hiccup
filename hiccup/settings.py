from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        validate_default=False,
    )

    database_url: Optional[str] = Field('postgresql+asyncpg://postgres:123456@localhost:5432/hiccup')
    redis_url: Optional[str] = Field('redis://localhost:6379/0')

    captcha_enabled: Optional[bool] = Field(False)
    captcha_turnstile_secret: Optional[str] = Field('')
    captcha_turnstile_endpoint: Optional[str] = Field('https://challenges.cloudflare.com')

    debug_enabled: Optional[bool] = Field(False)

    session_valid_duration: Optional[int] = Field(86400)

    permission_cache_ttl: Optional[int] = Field(600)


SETTINGS = Settings()
