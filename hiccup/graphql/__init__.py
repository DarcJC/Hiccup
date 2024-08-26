import strawberry

from hiccup.db.permission import PermissionGroup
from hiccup.graphql.base import generate_mutations
from hiccup.graphql.channel import ChannelMutation
from hiccup.graphql.context import Context
from hiccup.graphql.services import ServiceMutation, ServiceQuery
from hiccup.graphql.user import UserQuery, UserMutation
from hiccup.graphql.system import SystemQuery


PermissionGroupMutation = generate_mutations(PermissionGroup)


@strawberry.type
class Query(
    UserQuery,
    SystemQuery,
    ServiceQuery,
):
    pass


@strawberry.type
class Mutation(
    UserMutation,
    PermissionGroupMutation,
    ServiceMutation,
    ChannelMutation,
):
    pass


async def get_context() -> Context:
    return Context()


__all__ = ['Query', 'Mutation', 'get_context']
