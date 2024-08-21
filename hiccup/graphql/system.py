from datetime import datetime

import strawberry


@strawberry.type
class SystemQuery:
    @strawberry.field(description="Get server time")
    def server_time(self) -> datetime:
        return datetime.now()

    @strawberry.field(description="Get system time")
    def server_timestamp(self) -> int:
        return int(datetime.now().timestamp())
