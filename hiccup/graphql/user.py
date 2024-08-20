from datetime import datetime
from enum import Enum
from typing import Optional

import strawberry

from hiccup.db import AsyncSessionLocal
from hiccup.db.user import ClassicIdentify, AnonymousIdentify


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


class ClassicUser(UserBase):
    type: UserType = UserType.CLASSIC
    user_name: str


class AnonymousUser(UserBase):
    type: UserType = UserType.ANONYMOUS
    public_key: str


@strawberry.type
class UserQuery:
    @strawberry.field(description="Get user by id")
    async def get_user(self, uid: int) -> UserBase:
        async with AsyncSessionLocal() as session:
            user: Optional[AnonymousIdentify] = await session.get(AnonymousIdentify, uid)
            if user is not None:
                result = AnonymousUser()
                result.id = uid
                result.type = UserType.ANONYMOUS
                result.created_at = user.created_at
                result.updated_at = user.updated_at
                result.public_key = user.public_key
                return result

            user: Optional[ClassicIdentify]= await session.get(ClassicIdentify, uid)
            if user is not None:
                result = ClassicUser()
                result.id = uid
                result.type = UserType.CLASSIC
                result.created_at = user.created_at
                result.updated_at = user.updated_at
                result.user_name = user.user_name
                return result

            raise ValueError(f"User {uid} not found")


@strawberry.type
class UserMutation:
    @strawberry.mutation(description="Register user")
    async def test(self) -> UserBase:
        pass

