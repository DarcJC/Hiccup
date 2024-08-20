from typing import Any, Union, Awaitable

from starlette.requests import Request
from starlette.websockets import WebSocket
from strawberry import BasePermission, Info

from hiccup import SETTINGS
from hiccup.captcha.turnstile import Turnstile


class IsPassedCaptcha(BasePermission):
    message = "User must finish captcha challenge"

    async def has_permission(
        self, source: Any, info: Info, **kwargs: Any
    ) -> bool:
        if not SETTINGS.captcha_enabled:
            return True

        request: Union[Request, WebSocket] = info.context["request"]
        if "X-Hiccup-Captcha" in request.headers:
            return await Turnstile(secret_key=SETTINGS.captcha_turnstile_secret).verify(request.headers.get("X-Hiccup-Captcha"))

        return False


__all__ = ['Turnstile', 'IsPassedCaptcha']
