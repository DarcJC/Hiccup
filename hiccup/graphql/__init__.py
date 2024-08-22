import strawberry

from hiccup.graphql.context import Context
from hiccup.graphql.user import UserQuery, UserMutation
from hiccup.graphql.system import SystemQuery


@strawberry.type
class Query(UserQuery, SystemQuery):
    pass


@strawberry.type
class Mutation(UserMutation):
    pass


async def get_context() -> Context:
    return Context()


__all__ = ['Query', 'Mutation', 'get_context']
