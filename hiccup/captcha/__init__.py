from typing import Any, Union, Optional

from sqlalchemy import select
from starlette.requests import Request
from starlette.websockets import WebSocket
from strawberry import BasePermission, Info

from hiccup import SETTINGS
from hiccup.cache import get_user_permission_cached
from hiccup.captcha.turnstile import Turnstile
from hiccup.db import AsyncSessionLocal
from hiccup.db.user import AuthToken


class IsPassedCaptcha(BasePermission):
    message = "User must finish captcha challenge"

    async def has_permission(
        self, source: Any, info: Info, **kwargs: Any
    ) -> bool:
        if not SETTINGS.captcha_enabled:
            return True

        request: Union[Request, WebSocket] = info.context.request
        if "X-Hiccup-Captcha" in request.headers:
            return await Turnstile(secret_key=SETTINGS.captcha_turnstile_secret).verify(request.headers.get("X-Hiccup-Captcha"))

        return False


class HasPermission(BasePermission):
    message = "Access denied"

    def __init__(self, *required_permissions: str):
        super().__init__()
        self.required_permissions = set(required_permissions)

    async def has_permission(
            self, source: Any, info: Info, **kwargs: Any
    ) -> bool:
        request: Union[Request, WebSocket] = info.context.request
        if "X-Hiccup-Token" in request.headers:
            access_token = request.headers.get("X-Hiccup-Token")
            async with AsyncSessionLocal() as session:
                db_token: Optional[AuthToken] = await session.scalar(select(AuthToken).where(AuthToken.token == access_token).limit(1))
                if db_token is not None and not db_token.is_expired:
                    if db_token.classic_user_id:
                        permissions = await get_user_permission_cached(db_token.classic_user_id)
                    else:
                        # TODO: bind anonymous identify to classic identify
                        permissions = set()
                    return self.required_permissions.issubset(permissions)

        return False


__all__ = ['Turnstile', 'IsPassedCaptcha', 'HasPermission']
