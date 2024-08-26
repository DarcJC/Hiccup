import aiohttp

from hiccup.services import ServiceInfo
from hiccup.services.registry import ServiceController, ServiceHealthType


class MediaServiceController(ServiceController):
    def __init__(self, service: ServiceInfo):
        super().__init__(service)

    async def check_health(self) -> ServiceHealthType:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.info.domain_or_ip}/") as resp:
                if resp.status == 418:
                    return ServiceHealthType.Healthy

        return ServiceHealthType.Unavailable
