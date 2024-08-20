from datetime import datetime
from enum import Enum
from typing import Optional, Union

import sqlalchemy
import strawberry

from hiccup.captcha import IsPassedCaptcha
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


@strawberry.type
class ClassicUser(UserBase):
    type: UserType = UserType.CLASSIC
    username: str


@strawberry.type
class AnonymousUser(UserBase):
    type: UserType = UserType.ANONYMOUS
    public_key: str


@strawberry.type
class UserQuery:
    @strawberry.field(description="Get user info by id")
    async def get_user(self, uid: int) -> Union[ClassicUser, AnonymousUser]:
        async with AsyncSessionLocal() as session:
            user: Optional[AnonymousIdentify] = await session.get(AnonymousIdentify, uid)
            if user is not None:
                return AnonymousUser(id=uid, public_key=user.public_key.hex(), created_at=datetime.now(), updated_at=datetime.now())

            user: Optional[ClassicIdentify]= await session.get(ClassicIdentify, uid)
            if user is not None:
                return ClassicUser(id=uid, username=user.user_name, created_at=user.created_at, updated_at=user.updated_at)

            raise ValueError(f"User {uid} not found")


@strawberry.type
class UserMutation:
    @strawberry.mutation(description="Register classic user", permission_classes=[IsPassedCaptcha])
    async def register_classic(self, username: str, password: str) -> ClassicUser:
        async with AsyncSessionLocal() as session:
            derived_key, salt = ClassicIdentify.encrypt_password(password.encode("utf-8"))
            new_user = ClassicIdentify(user_name=username, password=derived_key, salt=salt)
            session.add(new_user)
            try:
                await session.commit()
            except sqlalchemy.exc.IntegrityError:
                raise ValueError(f"User {username} already registered")
            await session.refresh(new_user)
            return ClassicUser(id=new_user.id, username=new_user.user_name, updated_at=new_user.updated_at, created_at=new_user.created_at)

    @strawberry.mutation(description="Register anonymous user", permission_classes=[IsPassedCaptcha])
    async def register_anonymous(self, public_key: str) -> AnonymousUser:
        public_key_bytes = bytes.fromhex(public_key)
        if not AnonymousIdentify.is_valid_ed25519_public_key(public_key_bytes):
            raise ValueError("Invalid public key")

        async with AsyncSessionLocal() as session:
            new_user = AnonymousIdentify(public_key=public_key_bytes)
            session.add(new_user)
            try:
                await session.commit()
            except sqlalchemy.exc.IntegrityError:
                raise ValueError(f"User with public key '{public_key}' already registered")
            await session.refresh(new_user)
            return AnonymousUser(id=new_user.id, public_key=new_user.public_key.hex(), created_at=datetime.now(), updated_at=datetime.now())
