import re
import string
import time
import random
from datetime import datetime
from enum import Enum
from functools import cached_property, lru_cache
from typing import Type, Optional, Any, NewType, Union

import strawberry
from sqlalchemy import select, Column, ARRAY, VARCHAR, BOOLEAN, String, JSON, Table
from sqlalchemy.orm import DeclarativeBase, joinedload
from sqlalchemy.sql.type_api import TypeEngine
from strawberry.annotation import StrawberryAnnotation
from strawberry.fastapi import BaseContext
from strawberry.permission import PermissionExtension, BasePermission
from strawberry.tools import create_type
from strawberry.types.field import StrawberryField
from strawberry.tools import merge_types
from strawberry import scalars, Info

from authlib.jose import JsonWebToken

from hiccup import SETTINGS
from hiccup.cache import get_user_permission_cached
from hiccup.captcha import Turnstile
from hiccup.db import AsyncSessionLocal
from hiccup.db.user import AuthToken, AnonymousIdentify, ClassicIdentify


def map_sqlalchemy_engine_type(t: Type[TypeEngine]):
    if isinstance(t, VARCHAR):
        return str
    elif isinstance(t, BOOLEAN):
        return bool
    elif isinstance(t, String):
        return str
    return t


def map_sqlalchemy_column_type(column: Column) -> object:
    sql_type = column.type
    result = sql_type.python_type
    if isinstance(sql_type, ARRAY):
        result = list[map_sqlalchemy_engine_type(sql_type.item_type)]
    elif isinstance(sql_type, JSON):
        result = scalars.JSON

    if column.name == 'id':
        result = Optional[result]

    return result


@lru_cache(maxsize=None)
def generate_graphql_types(model: Type[DeclarativeBase], exclude_fields: Optional[list[str]] = None) -> (Type, Type):
    exclude_fields = exclude_fields or []

    table = model if isinstance(model, Table) else model.__table__
    table_name = table.name

    fields = [
        StrawberryField(
            python_name=col.name,
            type_annotation=StrawberryAnnotation(map_sqlalchemy_column_type(col)),
            description=f"{col.name} of the {table_name}",
        )
        for col in table.columns
        if col.name not in exclude_fields
    ]

    graphql_type = create_type(name=table_name, fields=fields)
    input_type = create_type(name=f'{table_name}Input', fields=[f for f in fields if f.python_name != "id"], is_input=True)

    return graphql_type, input_type


@lru_cache(maxsize=None)
def generate_mutations(
        model: Type[DeclarativeBase],
        exclude_fields: Optional[list[str]] = None,
        required_permissions: Optional[list[str]] = None
) -> strawberry.type:
    required_permissions = required_permissions or ["admin::super_admin"]

    graphql_type, input_type = generate_graphql_types(model, exclude_fields)

    table = model if isinstance(model, Table) else model.__table__
    table_name = table.name

    def create_mutation_class():
        mutations: dict[str, any] = {}

        async def create_item(data: input_type) -> graphql_type:
            async with AsyncSessionLocal() as session:
                item = model(**data.__dict__)
                session.add(item)
                await session.commit()
                await session.refresh(item)
                return item

        setattr(create_item, "__name__", to_camel_case(f"create_{table_name}"))
        mutations[to_camel_case(f"create_{table_name}")] = strawberry.mutation(create_item, description=f"Create {table_name}",
                             extensions=[PermissionExtension(permissions=[HasPermission(*required_permissions)])],
                             name=to_camel_case(f"create_{table_name}"))

        async def update_item(item_id: int, data: input_type) -> graphql_type:
            async with AsyncSessionLocal() as session:
                item = await session.scalar(select(model).where(model.id == item_id).limit(1))
                if item:
                    for key, value in data.__dict__.items():
                        setattr(item, key, value)
                else:
                    item = model(**data.__dict__)
                session.add(item)
                await session.commit()
                await session.refresh(item)
                return item

        setattr(update_item, "__name__", to_camel_case(f"update_{table_name}"))
        mutations[to_camel_case(f"update_{table_name}")] = strawberry.mutation(update_item, description=f"Update {table_name}. Create if not exist.",
                             extensions=[PermissionExtension(permissions=[HasPermission(*required_permissions)])],
                             name=to_camel_case(f"update_{table_name}"))

        async def delete_item(item_id: int) -> graphql_type:
            async with AsyncSessionLocal() as session:
                item = await session.scalar(select(model).where(model.id == item_id).limit(1))
                if item:
                    await session.delete(item)
                    await session.flush()
                    return True
                return False

        setattr(delete_item, "__name__", to_camel_case(f"delete_{table_name}"))
        mutations[f"delete_{table_name}"] = strawberry.mutation(delete_item, description=f"Delete {table_name}.",
                             extensions=[PermissionExtension(permissions=[HasPermission(*required_permissions)])],
                             name=to_camel_case(f"delete_{table_name}"))

        return create_type(name=f"{table_name}Mutation", fields=list(mutations.values()), description=f"Auto generated cud mutation for {table_name}")

    return create_mutation_class()


def generate_multiple_mutations(
        name: str = "GeneratedMutations",
        *models: tuple[ Type[DeclarativeBase], Optional[list[str]], Optional[list[str]] ]
) -> strawberry.type:
    created_types = tuple([ generate_mutations(*model) for model in models ])
    return merge_types(name, created_types)


@lru_cache(maxsize=None)
def generate_queries(
        model: Type[DeclarativeBase],
        exclude_fields: Optional[list[str]] = None,
        required_permission: Optional[list[str]] = None,
) -> strawberry.type:
    required_permissions = required_permission or ["admin::super_admin"]

    graphql_type, input_type = generate_graphql_types(model, exclude_fields)

    table = model if isinstance(model, Table) else model.__table__
    table_name = table.name

    async def retrieve_items(page: int = 0, page_size: int = 10) -> list[graphql_type]:
        async with AsyncSessionLocal() as session:
            offset = page * page_size
            result = await session.scalars(
                select(model).offset(offset).limit(page_size)
            ).all()
            return result

    retrieve_name = to_camel_case(f"retrieve_{table_name}")
    setattr(retrieve_items, "__name__", retrieve_name)

    return create_type(name=f'{table_name}Query', fields=[strawberry.field(
        retrieve_items,
        description=f"Retrieve paged {table_name} instances.",
        name=retrieve_name,
        extensions=[PermissionExtension(permissions=[HasPermission(*required_permissions)])],
    )])


def generate_multiple_queries(
        name: str = "GeneratedQueries",
        *models: tuple[ Type[DeclarativeBase], Optional[list[str]], Optional[list[str]] ],
) -> strawberry.type:
    created_types = tuple([ generate_queries(*model) for model in models ])
    return merge_types(name, created_types)


def to_camel_case(s: str) -> str:
    words = re.split(r'[\s_-]+', s)
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:])


class ObfuscatedID:
    @staticmethod
    def serialize(value: int) -> str:
        return SETTINGS.encrypt_id(value)

    @staticmethod
    def parse_value(value: str) -> int:
        return SETTINGS.decrypt_id(value)


obfuscated_id = strawberry.scalar(
    NewType("ObfuscatedID", str),
    name="obfuscatedId",
    description="Obfuscated ID",
    serialize=ObfuscatedID.serialize,
    parse_value=ObfuscatedID.parse_value,
)


class Context(BaseContext):
    async def user(self) -> Optional[Union['ClassicUser', 'AnonymousUser']]:
        if not self.request:
            return None

        token = self.request.headers.get('X-Hiccup-Token', None)

        if token is None:
            token = (self.connection_params or dict()).get('X-Hiccup-Token', None)

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
        if 'X-Hiccup-Captcha' in self.request.headers:
            return self.request.headers.get('X-Hiccup-Captcha', None)

        if self.connection_params and 'X-Hiccup-Captcha' in self.connection_params:
            return self.connection_params.get('X-Hiccup-Captcha', None)

        return None

    @cached_property
    def service_token(self) -> Optional[str]:
        if 'X-Hiccup-ServiceToken' in self.request.headers:
            return self.request.headers.get('X-Hiccup-ServiceToken', None)

        if self.connection_params and 'X-Hiccup-ServiceToken' in self.connection_params:
            return self.connection_params.get('X-Hiccup-ServiceToken', None)

        return None

@strawberry.enum
class UserType(str, Enum):
    CLASSIC = "classic"
    ANONYMOUS = "anonymous"


@strawberry.interface
class UserBase:
    id: obfuscated_id
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
            self, source: Any, info: Info[Context], **kwargs: Any
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
            self, source: Any, info: Info[Context], **kwargs: Any
    ) -> bool:
        user: Optional[Union['ClassicUser', 'AnonymousUser']] = await info.context.user()

        if user is not None:
            if isinstance(user, ClassicUser):
                permissions = await get_user_permission_cached(user.id)
            else:
                permissions = set()
            return self.required_permissions.issubset(permissions) or 'admin::super_admin' in permissions

        return False


class IsAuthenticated(BasePermission):
    message = "Authentication required"

    async def has_permission(
            self, source: Any, info: Info[Context], **kwargs: Any
    ) -> bool:
        return (await info.context.user()) is not None


jwt = JsonWebToken(algorithms=['EdDSA'])


def create_jwt(payload: dict) -> str:
    header = {'alg': 'EdDSA'}
    payload.setdefault('iss', 'Hiccup')
    payload.setdefault('timestamp', int(time.time()))
    payload.setdefault('nonce', ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(8)))
    private_key = SETTINGS.service_private_key_cryptography
    return jwt.encode(header=header, payload=payload, key=private_key).decode('utf-8')
