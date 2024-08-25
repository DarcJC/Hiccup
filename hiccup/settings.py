from functools import cached_property
from typing import Optional, Annotated

from dotenv import load_dotenv
load_dotenv()

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


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

    service_registry_redis_url: Optional[str] = Field('redis://localhost:6379/1')
    service_registry_namespace: Optional[str] = Field('services:')
    service_token: str = Field(min_length=32, max_length=256)
    service_registry_ttl: int = Field(60, ge=10, le=600)
    service_private_key: str = Field(min_length=32)

    @cached_property
    def service_private_key_cryptography(self) -> ed25519.Ed25519PrivateKey:
        private_key_bytes = bytes.fromhex(self.service_private_key)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        return private_key

    @cached_property
    def service_public_key_cryptography(self) -> ed25519.Ed25519PublicKey:
        return self.service_private_key_cryptography.public_key()

    @cached_property
    def service_public_key(self) -> str:
        return self.service_public_key_cryptography.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()


SETTINGS = Settings()
