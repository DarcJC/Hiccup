from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from hiccup.cache import AsyncRedisSessionLocal
from hiccup.db import AsyncSessionLocal
from hiccup.db.permission import PermissionGroup
from hiccup.db.user import ClassicIdentify

PREFIX_MAP = {
    "nonce": 'NONCE::',
    "user-permission": 'USER-PERMISSION::'
}


async def cache_nonce(nonce: str, expire_in: timedelta = timedelta(minutes=5)) -> bool:
    async with AsyncRedisSessionLocal() as session:
        return await session.set(f'{PREFIX_MAP["nonce"]}{nonce}', 1, ex=expire_in, nx=True)


async def invalidate_permission_cache(uid: int) -> None:
    async with AsyncRedisSessionLocal() as session:
        await session.delete(f'{PREFIX_MAP["user-permission"]}{uid}')


async def get_user_permission_no_cache(uid: int) -> Optional[set[str]]:
    async with AsyncSessionLocal() as session:
        db_user: Optional[ClassicIdentify] = await session.scalar(select(ClassicIdentify).options(joinedload(ClassicIdentify.permission_groups)).where(ClassicIdentify.id == uid).limit(1))
        if db_user is None:
            return None
        permissions: set[str] = {p for p in db_user.permissions}
        if permissions is None:
            permissions = set()

        for group in db_user.permission_groups:
            permissions = permissions.union( { p for p in group.permissions } )

        return permissions


async def get_user_permission_cached(uid: int) -> set[str]:
    key = f'{PREFIX_MAP["user-permission"]}{uid}'
    async with AsyncRedisSessionLocal() as session:
        value: list[bytes] = await session.lrange(key, 0, -1)
        if len(value) > 0:
            return { p.decode('utf-8') for p in value }

        value: set[str] = await get_user_permission_no_cache(uid)
        await session.lpushx(key, *value)

    return value
