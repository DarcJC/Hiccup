from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Union, Annotated

import sqlalchemy
import strawberry
from sqlalchemy import select

from hiccup.captcha import IsPassedCaptcha
from hiccup.db import AsyncSessionLocal, check_ed25519_signature
from hiccup.db.user import ClassicIdentify, AnonymousIdentify, AuthToken


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
class SessionToken:
    token: str


@strawberry.type
class UserQuery:
    @strawberry.field(description="Get user info by id")
    async def user_info(self, uid: Annotated[int, strawberry.argument(
        description="User id"
    )]) -> Union[ClassicUser, AnonymousUser]:
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

    @strawberry.mutation(description="Register anonymous user.", permission_classes=[IsPassedCaptcha])
    async def register_anonymous(self, public_key: Annotated[str, strawberry.argument(
        description="Ed25519 public key in hex"
    )]) -> AnonymousUser:
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

    @strawberry.mutation(description="Login classic user", permission_classes=[IsPassedCaptcha])
    async def login_classic(self, username: str, password: str) -> SessionToken:
        async with AsyncSessionLocal() as session:
            db_user: ClassicIdentify = (await session.scalars(select(ClassicIdentify).where(ClassicIdentify.user_name == username).limit(1))).one_or_none()
            if db_user is None or not db_user.is_password_valid(password.encode("utf-8")):
                raise ValueError(f"User {username} not found or invalid password")

            token = AuthToken.new_classic_token(db_user.id)
            session.add(token)
            await session.commit()
            return SessionToken(token=token.token)

    @strawberry.mutation(description="Login anonymous user.", permission_classes=[IsPassedCaptcha])
    async def login_anonymous(self, public_key: Annotated[str, strawberry.argument(description="Ed25519 public key in hex")],
                              timestamp: Annotated[int, strawberry.argument(description="Posix timestamp. The timestamp must within +-30s of server time")],
                              nonce: Annotated[str, strawberry.argument(description="A random string")],
                              signature: Annotated[str, strawberry.argument(description="Signature of utf-8(no-bom) encoded text 'login-{timestamp}-{nonce}' using private key")]) -> SessionToken:
        if abs(datetime.fromtimestamp(timestamp) - datetime.now()) > timedelta(seconds=30):
            raise ValueError("Invalid timestamp")
        if len(nonce) > 64 or len(nonce) < 5:
            raise ValueError("Nonce too long / too short")
        if not AnonymousIdentify.is_valid_ed25519_public_key(bytes.fromhex(public_key)):
            raise ValueError("Invalid public key")

        public_key_bytes = bytes.fromhex(public_key)

        if not check_ed25519_signature(public_key=public_key_bytes, message=f'login-{timestamp}-{nonce}'.encode('utf-8'), signature=bytes.fromhex(signature)):
            raise ValueError("Invalid signature")

        async with AsyncSessionLocal() as session:
            db_user: AnonymousIdentify = (await session.scalars(select(AnonymousIdentify).where(AnonymousIdentify.public_key == public_key_bytes).limit(1))).one_or_none()
            if db_user is None:
                raise ValueError(f"User with public key '{public_key}' not found")

            token = AuthToken.new_anonymous_token(db_user.id)
            session.add(token)
            await session.commit()
            return SessionToken(token=token.token)
