from typing import Any, Optional, Annotated

import strawberry

from hiccup import SETTINGS
from hiccup.graphql.base import Context
from hiccup.services import ServiceInfo, SERVICE_REGISTRY


class IsValidService(strawberry.BasePermission):
    message = "This is not a valid service"

    async def has_permission(
            self, source: Any, info: strawberry.Info[Context], **kwargs: Any
    ) -> bool:
        return info.context.service_token == SETTINGS.service_token


@strawberry.experimental.pydantic.type(model=ServiceInfo, all_fields=True, is_input=True)
class ServiceInfoInputType:
    pass


@strawberry.experimental.pydantic.type(model=ServiceInfo, all_fields=True)
class ServiceInfoType:
    pass


@strawberry.type
class ServiceRegistryInfo:
    public_key: str


@strawberry.type
class ServiceQuery:
    @strawberry.field(description="Service Registry Info")
    async def service_registry_info(self) -> ServiceRegistryInfo:
        return ServiceRegistryInfo(public_key=SETTINGS.service_public_key)


@strawberry.type
class ServiceMutation:
    @strawberry.mutation(description="Register a service", permission_classes=[IsValidService])
    async def register_service(self, category: str, service_info: ServiceInfoInputType) -> ServiceRegistryInfo:
        await SERVICE_REGISTRY.register_service(category, service_info.id, service_info.to_pydantic())
        return ServiceRegistryInfo(public_key=SETTINGS.service_public_key)

    @strawberry.mutation(description="Lookup services with tags", permission_classes=[IsValidService])
    async def lookup_services(self,
                              category: str,
                              tags: Annotated[Optional[list[str]], strawberry.argument(
                                  description="Required tags of services. If tags is null, will lookup in all services"
                              )] = None) -> ServiceInfoType:
        service_info = await SERVICE_REGISTRY.find_service(category, None if tags is None else set(tags))
        if service_info is None:
            raise ValueError("No services found")

        return ServiceInfoType.from_pydantic(service_info)

    @strawberry.mutation(description="Refresh service ttl", permission_classes=[IsValidService])
    async def refresh_service(self, category: str, service_id: str) -> bool:
        return await SERVICE_REGISTRY.refresh_service(category, service_id)

    @strawberry.mutation(description="Remove service", permission_classes=[IsValidService])
    async def remove_service(self, category: str, service_id: str) -> bool:
        return await SERVICE_REGISTRY.remove_service(category, service_id)
