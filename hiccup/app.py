import logging
from contextlib import asynccontextmanager

import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL
from strawberry.extensions import ParserCache, QueryDepthLimiter

from hiccup import SETTINGS
from hiccup.graphql import Query, Mutation, get_context
from hiccup.services import SERVICE_REGISTRY

# GraphQL
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    config=StrawberryConfig(
        disable_field_suggestions=not SETTINGS.debug_enabled,
    ),
    extensions=[
        ParserCache(maxsize=SETTINGS.graphql_parser_cache_size),
        QueryDepthLimiter(max_depth=SETTINGS.graphql_max_query_depth),
    ],
)
logging.getLogger("strawberry.execution").setLevel(logging.INFO if SETTINGS.debug_enabled else logging.CRITICAL)

graphql_app = GraphQLRouter(
    schema,
    debug=SETTINGS.debug_enabled,
    context_getter=get_context,
    subscription_protocols=[
        GRAPHQL_TRANSPORT_WS_PROTOCOL,
        GRAPHQL_WS_PROTOCOL,
    ],
)


@asynccontextmanager
async def lifespan(a: FastAPI):
    # Setup
    await SERVICE_REGISTRY.setup()
    yield
    # Clean up
    await SERVICE_REGISTRY.dispose()

app = FastAPI(lifespan=lifespan)
app.include_router(graphql_app, prefix="/graphql")
