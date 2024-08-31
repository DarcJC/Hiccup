import random
import string
from typing import Optional

import sqlalchemy
import strawberry
from sqlalchemy import select, and_, Alias
from sqlalchemy.orm import joinedload
from strawberry import Info
from strawberry.scalars import JSON

from hiccup.db import AsyncSessionLocal, user_joined_server_table, VirtualServer
from hiccup.db.server import Channel, VirtualServerAlias
from hiccup.db.user import ClassicIdentify
from hiccup.graphql.base import IsAuthenticated, create_jwt, Context, ObfuscatedID, ClassicUser
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
class ChannelInfo:
    id: obfuscated_id
    server_id: obfuscated_id
    name: str
    joinable: bool
    configuration: JSON


@strawberry.type
class VirtualServerInfo:
    id: obfuscated_id
    name: str
    configuration: JSON

    @strawberry.field(
        description="Get list of channel in server",
        permission_classes=[IsAuthenticated],
    )
    async def channels(self) -> list[ChannelInfo]:
        server_id = self.id
        stmt = select(VirtualServer).options(joinedload(VirtualServer.channels)).where(VirtualServerAlias.id == server_id)
        async with AsyncSessionLocal() as session:
            virtual_server: Optional[VirtualServer] = await session.scalar(stmt)

            if virtual_server is None:
                raise ValueError("Server not found")

            return list(map(lambda x: ChannelInfo(id=x.id, server_id=x.server_id, name=x.name, joinable=x.joinable, configuration=x.configuration), virtual_server.channels))


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

    @strawberry.field(
        description="Create alias for server",
        permission_classes=[IsAuthenticated],
    )
    async def create_alias_for_server(self, server_id: obfuscated_id) -> str:
        async with AsyncSessionLocal() as session:
            virtual_server: Optional[VirtualServer] = await session.scalar(select(VirtualServer).where(VirtualServer.id == server_id))
            if virtual_server is None:
                raise ValueError(f"Virtual server #{ObfuscatedID.serialize(server_id)} not found")
            new_alias_name = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10))
            new_alias = VirtualServerAlias(name=new_alias_name, virtual_server_id=virtual_server.id)
            session.add(new_alias)
            await session.commit()
            return new_alias_name

    @strawberry.field(
        description="Join server via server alias",
        permission_classes=[IsAuthenticated],
    )
    async def join_server_by_alias(self, alias: str, info: Info[Context]) -> VirtualServerInfo:
        async with AsyncSessionLocal() as session:
            stmt = select(VirtualServerAlias).options(joinedload(VirtualServerAlias.virtual_server)).where(
                and_(
                    VirtualServerAlias.name == alias,
                    VirtualServerAlias.valid == True,
                )
            )
            result: Optional[VirtualServerAlias] = await session.scalar(stmt)

            if result is None:
                raise ValueError("Alias not found")

            virtual_server: VirtualServer = result.virtual_server

            if not virtual_server.config.allow_join_by_alias:
                raise ValueError("Server doesn't allow join using alias")

            user = await info.context.user()

            if isinstance(user, ClassicUser):
                new_row = user_joined_server_table.insert().values(classic_user_id=user.id, virtual_server_id=virtual_server.id)
                try:
                    await session.execute(new_row)
                    await session.commit()
                except sqlalchemy.exc.IntegrityError:
                    pass
                except sqlalchemy.exc.SQLAlchemyError:
                    raise ValueError("Internal Server Error")

            return VirtualServerInfo(id=virtual_server.id, name=virtual_server.name, configuration=virtual_server.configuration)


@strawberry.type
class ChannelQuery:
    @strawberry.field(
        description="Get list of server user joined",
        permission_classes=[IsAuthenticated],
    )
    async def user_server_list(self, info: Info[Context]) -> list[VirtualServerInfo]:
        user = await info.context.user()

        if isinstance(user, ClassicUser):
            stmt = select(ClassicIdentify).join(ClassicIdentify.joined_servers).options(joinedload(ClassicIdentify.joined_servers)).where(ClassicIdentify.id == user.id)
            async with AsyncSessionLocal() as session:
                user = await session.scalar(stmt)

            if user is None:
                raise ValueError("Internal Server Error")

            return list(map(lambda x: VirtualServerInfo(id=x.id, name=x.name, configuration=x.configuration), user.joined_servers))

        return []
