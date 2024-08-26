import abc
import enum
import json
from datetime import timedelta
from functools import cached_property
from typing import Optional

import redis.asyncio as redis
from pydantic import BaseModel

from hiccup import SETTINGS


class ServiceInfo(BaseModel):
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
        return Session(pool=self.pool)

    @property
    def service_ttl(self):
        return SETTINGS.service_registry_ttl

    async def register_service(self, category: str, service_id: str, service_info: ServiceInfo):
        key = f'{self._namespace}:{category}:{service_id}'
        async with self._redis_session() as client:
            await client.setex(key, timedelta(seconds=self.service_ttl), service_info.model_dump_json())

    async def find_service(self, category:str, tags: Optional[set[str]] = None) -> Optional[ServiceInfo]:
        async with self._redis_session() as client:
            keys = await client.keys(f'{self._namespace}:{category}:*')
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
        key = f'{self._namespace}:{category}:{service_id}'
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
        key = f'{self._namespace}:{category}:{service_id}'
        async with self._redis_session() as client:
            return await client.delete(key)

    async def set_service_metadata(self, category: str, name: str, metadata: dict, ex: timedelta = None):
        key = f'{self._namespace}:{category}:metadata:{name}'
        async with self._redis_session() as client:
            await client.set(key, json.dumps(metadata), ex=ex)

    async def get_service_metadata(self, category: str, name: str) -> Optional[dict]:
        key = f'{self._namespace}:{category}:metadata:{name}'
        async with self._redis_session() as client:
            res = await client.get(key)
            if res is not None:
                return json.loads(res)
        return None


SERVICE_REGISTRY = ServiceRegistry()
