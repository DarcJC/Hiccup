from datetime import timedelta

from hiccup.cache import AsyncRedisSessionLocal

PREFIX_MAP = {
    "nonce": 'NONCE-',
}


async def cache_nonce(nonce: str, expire_in: timedelta = timedelta(minutes=5)) -> bool:
    async with AsyncRedisSessionLocal() as session:
        return await session.set(f'{PREFIX_MAP["nonce"]}{nonce}', 1, ex=expire_in, nx=True)
