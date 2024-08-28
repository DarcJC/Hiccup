import strawberry
from sqlalchemy import select

from hiccup.db import AsyncSessionLocal
from hiccup.db.server import Channel
from hiccup.graphql.base import IsAuthenticated, create_jwt, Context, ObfuscatedID
from hiccup.graphql.base import obfuscated_id
from hiccup.graphql.services import IsValidService
from hiccup.services import get_media_controller


@strawberry.type
class MediaTokenType:
    service_id: str
    room_id: obfuscated_id
    server_id: obfuscated_id
    display_name: str
    max_incoming_bitrate: int


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
    async def allocate_media_server(self, channel_id: obfuscated_id, _info: strawberry.Info[Context]) -> MediaSignalServerConnectionInfo:
        # TODO: check permission, waiting for channel controller impl
        async with AsyncSessionLocal() as session:
            channel = await session.scalar(select(Channel).where(Channel.id == channel_id).limit(1))

            if channel is None:
                raise ValueError("Channel not found")

            allocated_service = await get_media_controller().get_or_allocate_channel_room(channel_id)
            if allocated_service is None:
                raise ValueError("Allocating room failed")

            payload = {
                "service_id": allocated_service.id,
                "room_id": ObfuscatedID.serialize(channel_id),
                "server_id": ObfuscatedID.serialize(channel.server_id),
                "display_name": f'AnonymousUser',
                "max_incoming_bitrate": 32000,
            }

            return MediaSignalServerConnectionInfo(
                hostname=allocated_service.hostname,
                port=allocated_service.port,
                token=create_jwt(payload),
            )

    @strawberry.field(
        description="Deallocate a media server. Might occur when room is empty for a period.",
        permission_classes=[IsValidService],
    )
    async def deallocate_media_server(self, channel_id: obfuscated_id) -> bool:
        return await get_media_controller().deallocate_channel_room(channel_id)
