import redis.asyncio as redis

from hiccup import SETTINGS


class RedisCache:
    pool: redis.ConnectionPool

    def __init__(self):
        self.pool = redis.ConnectionPool().from_url(SETTINGS.redis_url)


class AsyncRedisSessionMaker:
    def __init__(self, cache: RedisCache):
        self.cache = cache

    def __call__(self, *args, **kwargs) -> 'AsyncRedisSession':
        return AsyncRedisSession(self.cache)


class AsyncRedisSession:
    def __init__(self, cache: RedisCache):
        self.cache = cache
        self.client = None

    async def __aenter__(self):
        self.client = redis.Redis(connection_pool=self.cache.pool)
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()
        self.client = None


AsyncRedisSessionLocal = AsyncRedisSessionMaker(RedisCache())
