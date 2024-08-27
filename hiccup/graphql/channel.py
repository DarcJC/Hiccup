import strawberry

from hiccup.graphql.permission import IsAuthenticated
from hiccup.graphql.services import IsValidService
from hiccup.services import get_media_controller
from hiccup.graphql.base import obfuscated_id


@strawberry.type
class MediaSignalServerConnectionInfo:
    hostname: str
    port: int
    token: str


@strawberry.type
class ChannelMutation:
    @strawberry.field(
        description="Allocate a media server and get connection info",
        permission_classes=[IsAuthenticated],
    )
    async def allocate_media_server(self, channel_id: obfuscated_id) -> MediaSignalServerConnectionInfo:
        allocated_service = await get_media_controller().get_or_allocate_channel_room(channel_id)
        if allocated_service is None:
            raise ValueError("Allocating room failed")
        return MediaSignalServerConnectionInfo(
            hostname=allocated_service.hostname,
            port=allocated_service.port,
            token="NO",
        )

    @strawberry.field(
        description="Deallocate a media server. Might occur when room is empty for a period.",
        permission_classes=[IsValidService],
    )
    async def deallocate_media_server(self, channel_id: obfuscated_id) -> bool:
        return await get_media_controller().deallocate_channel_room(channel_id)
