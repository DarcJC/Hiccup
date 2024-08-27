import string
from functools import cached_property
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def base62_encode(num):
    characters = string.digits + string.ascii_letters
    base = len(characters)
    result = []
    while num:
        num, rem = divmod(num, base)
        result.append(characters[rem])
    return ''.join(reversed(result)) or '0'

def base62_decode(s):
    characters = string.digits + string.ascii_letters
    base = len(characters)
    num = 0
    for char in s:
        num = num * base + characters.index(char)
    return num


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

    graphql_parser_cache_size: int = Field(128, ge=8)
    graphql_max_query_depth: int = Field(10, ge=5, le=128)

    id_obf_module_number: int = Field(2**32, ge=2**16)
    id_obf_secret_key: int = Field(24542592794035)
    id_obf_secret_a: int = Field(2333)

    @cached_property
    def service_private_key_cryptography(self) -> ed25519.Ed25519PrivateKey:
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(self.private_key_bytes)
        return private_key

    @cached_property
    def service_public_key_cryptography(self) -> ed25519.Ed25519PublicKey:
        return self.service_private_key_cryptography.public_key()

    @cached_property
    def service_public_key(self) -> str:
        return self.service_public_key_cryptography.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex().upper()

    @cached_property
    def private_key_bytes(self) -> bytes:
        return bytes.fromhex(self.service_private_key)

    def encrypt_id(self, id_value: int) -> str:
        mixed_num = ((id_value * self.id_obf_secret_a) ^ self.id_obf_secret_key) % self.id_obf_module_number
        return base62_encode(mixed_num)

    def decrypt_id(self, encrypted_id: str) -> int:
        mixed_num = base62_decode(encrypted_id)
        original_num = (mixed_num ^ self.id_obf_secret_key) * pow(self.id_obf_secret_a, -1, self.id_obf_module_number) % self.id_obf_module_number
        return original_num


SETTINGS = Settings()
