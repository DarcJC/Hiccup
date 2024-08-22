from functools import cached_property
from typing import Optional, Union

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from strawberry.fastapi import BaseContext

from hiccup.db import AsyncSessionLocal
from hiccup.db.user import AuthToken, AnonymousIdentify, ClassicIdentify
from hiccup.graphql.permission import AnonymousUser, ClassicUser


class Context(BaseContext):
    async def user(self) -> Optional[Union['ClassicUser', 'AnonymousUser']]:
        if not self.request:
            return None

        token = self.request.headers.get('X-Hiccup-Token', None)
        if token is None:
            return None

        async with AsyncSessionLocal() as session:
            db_token: Optional[AuthToken] = await session.scalar(
                select(AuthToken)
                .options(
                    joinedload(AuthToken.anonymous_identify)
                        .options(joinedload(AnonymousIdentify.owner)),
                    joinedload(AuthToken.classic_identify))
                .where(AuthToken.token == token).limit(1))
            if db_token is None or db_token.is_expired:
                return None

            if db_token.anonymous_identify is not None:
                anonymous: AnonymousIdentify = db_token.anonymous_identify
                if anonymous.owner is None:
                    return AnonymousUser(id=anonymous.id, created_at=anonymous.created_at, updated_at=anonymous.updated_at, public_key=anonymous.public_key)
                classic: ClassicIdentify = anonymous.owner
                return ClassicUser(id=classic.id, created_at=classic.created_at, updated_at=classic.updated_at, username=classic.user_name)

            if db_token.classic_identify is not None:
                classic: ClassicIdentify = db_token.classic_identify
                return ClassicUser(id=classic.id, created_at=classic.created_at, updated_at=classic.updated_at, username=classic.user_name)

        return None

    @cached_property
    def captcha_challenge_token(self) -> Optional[str]:
        return self.request.headers.get('X-Hiccup-Captcha', None)
