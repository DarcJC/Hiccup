import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig

from hiccup import SETTINGS
from hiccup.graphql import Query, Mutation


# GraphQL
schema = strawberry.Schema(query=Query, mutation=Mutation, config=StrawberryConfig(
    disable_field_suggestions=not SETTINGS.debug_enabled,
))
graphql_app = GraphQLRouter(schema, debug=SETTINGS.debug_enabled)

app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")
