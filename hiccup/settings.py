from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        validate_default=False,
    )

    database_url: Optional[str] = Field('sqlite:///test.db')

    captcha_enabled: Optional[bool] = Field(False)
    captcha_turnstile_secret: Optional[str] = Field('')
    captcha_turnstile_endpoint: Optional[str] = Field('https://challenges.cloudflare.com')

    debug_enabled: Optional[bool] = Field(False)

    session_valid_duration: Optional[int] = Field(86400)


SETTINGS = Settings()
