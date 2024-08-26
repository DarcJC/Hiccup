import strawberry


@strawberry.type
class MediaSignalServerConnectionInfo:
    hostname: str
    port: int
    token: str


@strawberry.type
class ChannelMutation:
    @strawberry.field(description="Allocate a media server and get connection info")
    async def allocate_media_server(self) -> MediaSignalServerConnectionInfo:
        pass
