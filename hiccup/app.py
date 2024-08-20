from dotenv import load_dotenv
load_dotenv()

import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from hiccup.graphql import Query, Mutation


# GraphQL
schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)

app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")
