import strawberry

from hiccup.graphql.user import UserQuery, UserMutation


@strawberry.type
class Query(UserQuery):
    pass


@strawberry.type
class Mutation(UserMutation):
    pass


__all__ = ['Query', 'Mutation']
