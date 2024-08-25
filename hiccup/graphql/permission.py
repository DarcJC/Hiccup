from datetime import datetime
from enum import Enum
from typing import Any, Union, Optional

import strawberry
from strawberry import BasePermission, Info

from hiccup import SETTINGS
from hiccup.cache import get_user_permission_cached
from hiccup.captcha import Turnstile


@strawberry.enum
class UserType(str, Enum):
    CLASSIC = "classic"
    ANONYMOUS = "anonymous"


@strawberry.interface
class UserBase:
    id: int
    type: UserType
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ClassicUser(UserBase):
    type: UserType = UserType.CLASSIC
    username: str


@strawberry.type
class AnonymousUser(UserBase):
    type: UserType = UserType.ANONYMOUS
    public_key: str


class IsPassedCaptcha(BasePermission):
    message = "User must finish captcha challenge"

    async def has_permission(
            self, source: Any, info: Info['Context'], **kwargs: Any
    ) -> bool:
        if not SETTINGS.captcha_enabled:
            return True

        if info.context.captcha_challenge_token is not None:
            return await Turnstile(secret_key=SETTINGS.captcha_turnstile_secret).verify(info.context.captcha_challenge_token)

        return False


class HasPermission(BasePermission):
    message = "Access denied"

    def __init__(self, *required_permissions: str):
        super().__init__()
        self.required_permissions = set(required_permissions)

    async def has_permission(
            self, source: Any, info: Info['Context'], **kwargs: Any
    ) -> bool:
        user: Optional[Union['ClassicUser', 'AnonymousUser']] = await info.context.user()

        if user is not None:
            if isinstance(user, ClassicUser):
                permissions = await get_user_permission_cached(user.id)
            else:
                permissions = set()
            return self.required_permissions.issubset(permissions) or 'admin:super_admin' in permissions

        return False


class IsAuthenticated(BasePermission):
    message = "Authentication required"

    async def has_permission(
            self, source: Any, info: Info['Context'], **kwargs: Any
    ) -> bool:
        return (await info.context.user()) is not None
