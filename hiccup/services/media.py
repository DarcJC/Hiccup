from typing import Optional, Literal

import aiohttp
from unicodedata import category

from hiccup.services.registry import ServiceController, ServiceHealthType, SERVICE_REGISTRY, ServiceRegistry, ServiceInfo


class MediaServiceController(ServiceController):
    def __init__(self, service: ServiceInfo):
        super().__init__(service)

    async def check_health(self) -> ServiceHealthType:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.info.domain_or_ip}/") as resp:
                if resp.status == 418:
                    return ServiceHealthType.Healthy

        return ServiceHealthType.Unavailable


# noinspection PyProtectedMember
class MediaController:
    registry: ServiceRegistry
    category: Literal['media'] = 'media'

    def __init__(self, registry: ServiceRegistry):
        self.registry = registry

    async def get_or_allocate_channel_room(self, channel_id: int, tags: Optional[list[str]] = None) -> Optional[ServiceInfo]:
        key = f"room_of_{channel_id}"
        async with self.registry._redis_session() as session:
            async with self.registry._redis_lock(session, lock_key=f"lock::{key}", timeout=3.0):
                async def perform_allocate() -> Optional[ServiceInfo]:
                    service = await self.registry.find_service(category=self.category, tags=tags)
                    if service is None:
                        return None
                    await self.registry.set_service_metadata(category=self.category, name=key, metadata=service.model_dump(), lock=False)
                    return service

                allocated_info = await self.registry.get_service_metadata(category=self.category, name=key, lock=False)

                if allocated_info is None:
                    allocated_info = await perform_allocate()
                else:
                    allocated_info = ServiceInfo(**allocated_info)
                    # TODO: Check if service available

                return allocated_info

    async def deallocate_channel_room(self, channel_id: int) -> bool:
        key = self.registry.get_key(category=self.category, key=f"metadata::room_of_{channel_id}")
        return await self.registry.delete_service_metadata(category=self.category, name=key, lock=True)

def get_media_controller(service_registry: ServiceRegistry = SERVICE_REGISTRY) -> MediaController:
    return MediaController(registry=service_registry)
