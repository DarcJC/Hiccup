from datetime import datetime

import strawberry
from strawberry.permission import PermissionExtension

from hiccup import SETTINGS
from hiccup.graphql.base import HasPermission


@strawberry.type
class SystemQuery:
    @strawberry.field(description="Get server time")
    def server_time(self) -> datetime:
        return datetime.now()

    @strawberry.field(description="Get system time")
    def server_timestamp(self) -> int:
        return int(datetime.now().timestamp())

    @strawberry.field(
        description="Encrypt a number",
        extensions=[
            PermissionExtension(permissions=[
                HasPermission("system::encrypt_number")
            ])
        ]
    )
    def encrypt_number(self, number: int) -> str:
        return SETTINGS.encrypt_id(number)

    @strawberry.field(
        description="Decrypt a number",
        extensions=[
            PermissionExtension(permissions=[
                HasPermission("system::decrypt_number")
            ])
        ]
    )
    def decrypt_number(self, encrypted_number: str) -> int:
        return SETTINGS.decrypt_id(encrypted_number)
