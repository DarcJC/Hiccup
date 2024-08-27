import strawberry

from hiccup.db.permission import PermissionGroup
from hiccup.db.server import Channel
from hiccup.graphql.base import generate_multiple_mutations
from hiccup.graphql.channel import ChannelMutation
from hiccup.graphql.base import Context
from hiccup.graphql.services import ServiceMutation, ServiceQuery
from hiccup.graphql.user import UserQuery, UserMutation
from hiccup.graphql.system import SystemQuery


GeneratedMutation = generate_multiple_mutations(
    "GeneratedMutations",
    (PermissionGroup, None, None),
    (Channel, None, None),
)


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
    GeneratedMutation,
    ServiceMutation,
    ChannelMutation,
):
    pass


async def get_context() -> Context:
    return Context()


__all__ = ['Query', 'Mutation', 'get_context']
