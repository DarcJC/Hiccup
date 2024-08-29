import abc
import asyncio
import enum
import json
from datetime import timedelta
from functools import cached_property
from typing import Optional

import redis.asyncio as redis
import redis.asyncio.lock as redis_lock
from pydantic import BaseModel

from hiccup import SETTINGS


class ServiceInfo(BaseModel):
    id: str
    tags: list[str]
    ip: str
    hostname: Optional[str] = None
    port: int
    load_factor: float

    @cached_property
    def domain_or_ip(self):
        if self.host is None:
            return self.ip
        return self.hostname


class ServiceHealthType(str, enum.Enum):
    Healthy = "healthy"
    Unstable = "unstable"
    Unavailable = "unavailable"


class ServiceController(abc.ABC):
    info: ServiceInfo

    def __init__(self, service_info: ServiceInfo):
        self.info = service_info

    @abc.abstractmethod
    async def check_health(self) -> ServiceHealthType:
        pass


class ServiceRegistry:
    pool: redis.ConnectionPool
    _namespace: str

    def __init__(self):
        self.pool = redis.ConnectionPool().from_url(SETTINGS.service_registry_redis_url)
        self._namespace = SETTINGS.service_registry_namespace

    async def setup_key_notification(self):
        async with self._redis_session() as session:
            await session.config_set("notify-keyspace-events", "KEgx")

    def _redis_session(self):
        class Session:
            pool: redis.ConnectionPool
            client: Optional[redis.Redis]

            def __init__(self, pool: redis.ConnectionPool):
                self.pool = pool
                self.client = None

            async def __aenter__(self):
                self.client = redis.Redis(connection_pool=self.pool)
                return self.client

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await self.client.close()
                self.client = None
                return True

        return Session(pool=self.pool)

    def _redis_lock(self, client: redis.Redis, lock_key: str, timeout: Optional[float] = None):
        class LockManager:
            _client: redis.Redis
            lock: redis_lock.Lock

            def __init__(self, _client: redis.Redis, _lock_key: str, _timeout: Optional[float] = None):
                self._client = _client
                self.lock = self._client.lock(name=_lock_key, timeout=_timeout)

            async def __aenter__(self):
                await self.lock.acquire()
                return None

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await self.lock.release()
                return True

        return LockManager(_client=client, _lock_key=lock_key, _timeout=timeout)

    @property
    def service_ttl(self):
        return SETTINGS.service_registry_ttl

    def get_key(self, category: str, key: str) -> str:
        return f"{self._namespace}:{category}::{key}"

    async def register_service(self, category: str, service_id: str, service_info: ServiceInfo):
        key = self.get_key(category, service_id)
        async with self._redis_session() as client:
            await client.setex(key, timedelta(seconds=self.service_ttl), service_info.model_dump_json())

    async def find_service(self, category:str, tags: Optional[set[str]] = None) -> Optional[ServiceInfo]:
        async with self._redis_session() as client:
            keys = await client.keys(f'{self._namespace}:{category}::*')
            services: list[(str, ServiceInfo)] = []
            for key in keys:
                service_info = ServiceInfo.model_validate_json(await client.get(key))
                if tags is None or set(service_info.tags).issubset(tags):
                    services.append((key, service_info))

            if not services:
                return None

            _, selected_service = min(services, key=lambda x: x[1].load_factor)
            return selected_service

    async def refresh_service(self, category: str, service_id: str) -> bool:
        key = self.get_key(category, service_id)
        async with self._redis_session() as client:
            service_info = await client.get(key)
            if service_info is None:
                return False
            service_info = ServiceInfo.model_validate_json(service_info)
            if service_info is not None:
                await client.setex(key, timedelta(seconds=self.service_ttl), service_info.model_dump_json())
                return True
        return False

    async def remove_service(self, category: str, service_id: str) -> bool:
        key = self.get_key(category, service_id)
        async with self._redis_session() as client:
            return await client.delete(key)

    async def set_service_metadata(self, category: str, name: str, metadata: dict, ex: timedelta = None, lock: bool = False):
        key = self.get_key(category, f'metadata::{name}')
        lock_key = f'lock::{key}'
        async with self._redis_session() as client:
            async def action():
                return await client.set(key, json.dumps(metadata), ex=ex)
            if lock:
                async with self._redis_lock(client, lock_key, 1.0):
                    return await action()
            else:
                return await action()

    async def get_service_metadata(self, category: str, name: str, lock: bool = False) -> Optional[dict]:
        key = self.get_key(category, f'metadata::{name}')
        lock_key = f'lock::{key}'
        async with self._redis_session() as client:
            async def action():
                res = await client.get(key)
                if res is not None:
                    return json.loads(res)
                return None

            if lock:
                async with self._redis_lock(client, lock_key, 1.0):
                    return await action()
            else:
                return await action()

    async def delete_service_metadata(self, category: str, name: str, lock: bool = False) -> bool:
        key = self.get_key(category, f'metadata::{name}')
        lock_key = f'lock::{key}'
        async with self._redis_session() as client:
            async def action():
                return await client.delete(key)
            if lock:
                async with self._redis_lock(client, lock_key, 1.0):
                    return await action()
            else:
                return await action()


SERVICE_REGISTRY = ServiceRegistry()
