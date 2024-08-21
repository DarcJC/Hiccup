import strawberry

from hiccup.graphql.user import UserQuery, UserMutation
from hiccup.graphql.system import SystemQuery


@strawberry.type
class Query(UserQuery, SystemQuery):
    pass


@strawberry.type
class Mutation(UserMutation):
    pass


__all__ = ['Query', 'Mutation']
