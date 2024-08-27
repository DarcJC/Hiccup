import re
from typing import Type, Optional, Any

import strawberry
from sqlalchemy import select, Column, ARRAY, VARCHAR, BOOLEAN, String, JSON
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.type_api import TypeEngine
from strawberry.annotation import StrawberryAnnotation
from strawberry.permission import PermissionExtension
from strawberry.tools import create_type
from strawberry.types.base import StrawberryType
from strawberry.types.field import StrawberryField
from strawberry import scalars

from hiccup.db import AsyncSessionLocal
from hiccup.graphql.permission import HasPermission


def map_sqlalchemy_engine_type(t: Type[TypeEngine]):
    if isinstance(t, VARCHAR):
        return str
    elif isinstance(t, BOOLEAN):
        return bool
    elif isinstance(t, String):
        return str
    return t


def map_sqlalchemy_column_type(column: Column) -> object:
    sql_type = column.type
    result = sql_type.python_type
    if isinstance(sql_type, ARRAY):
        result = list[map_sqlalchemy_engine_type(sql_type.item_type)]
    elif isinstance(sql_type, JSON):
        result = scalars.JSON

    if column.name == 'id':
        result = Optional[result]

    return result


def generate_graphql_types(model: Type[DeclarativeBase], exclude_fields: Optional[list[str]] = None) -> (Type, Type):
    exclude_fields = exclude_fields or []

    fields = [
        StrawberryField(
            python_name=col.name,
            type_annotation=StrawberryAnnotation(map_sqlalchemy_column_type(col)),
            description=f"{col.name} of the {model.__name__}",
        )
        for col in model.__table__.columns
        if col.name not in exclude_fields
    ]

    graphql_type = create_type(name=model.__name__, fields=fields)
    input_type = create_type(name=f'{model.__name__}Input', fields=[f for f in fields if f.python_name != "id"], is_input=True)

    return graphql_type, input_type


def generate_mutations(model: Type[DeclarativeBase], exclude_fields: Optional[list[str]] = None,
                       required_permissions=None) -> strawberry.type:
    required_permissions = required_permissions or ["admin::admin"]

    graphql_type, input_type = generate_graphql_types(model, exclude_fields)

    def create_mutation_class():
        mutations: dict[str, any] = {}

        async def create_item(data: input_type) -> graphql_type:
            async with AsyncSessionLocal() as session:
                item = model(**data.__dict__)
                session.add(item)
                await session.commit()
                await session.refresh(item)
                return item

        setattr(create_item, "__name__", to_camel_case(f"create_{model.__name__}"))
        mutations[to_camel_case(f"create_{model.__name__}")] = strawberry.mutation(create_item, description=f"Create {model.__name__}",
                             extensions=[PermissionExtension(permissions=[HasPermission(*required_permissions)])],
                             name=to_camel_case(f"create_{model.__name__}"))

        async def update_item(item_id: int, data: input_type) -> graphql_type:
            async with AsyncSessionLocal() as session:
                item = await session.scalar(select(model).where(model.id == item_id).limit(1))
                if item:
                    for key, value in data.__dict__.items():
                        setattr(item, key, value)
                else:
                    item = model(**data.__dict__)
                session.add(item)
                await session.commit()
                await session.refresh(item)
                return item

        setattr(update_item, "__name__", to_camel_case(f"update_{model.__name__}"))
        mutations[to_camel_case(f"update_{model.__name__}")] = strawberry.mutation(update_item, description=f"Update {model.__name__}. Create if not exist.",
                             extensions=[PermissionExtension(permissions=[HasPermission(*required_permissions)])],
                             name=to_camel_case(f"update_{model.__name__}"))

        async def delete_item(item_id: int) -> graphql_type:
            async with AsyncSessionLocal() as session:
                item = await session.scalar(select(model).where(model.id == item_id).limit(1))
                if item:
                    await session.delete(item)
                    await session.flush()
                    return True
                return False

        setattr(delete_item, "__name__", to_camel_case(f"delete_{model.__name__}"))
        mutations[f"delete_{model.__name__}"] = strawberry.mutation(delete_item, description=f"Delete {model.__name__}.",
                             extensions=[PermissionExtension(permissions=[HasPermission(*required_permissions)])],
                             name=to_camel_case(f"delete_{model.__name__}"))

        return create_type(name=f"{model.__name__}Mutation", fields=list(mutations.values()), description=f"Auto generated cud mutation for {model.__name__}")

    return create_mutation_class()


def to_camel_case(s: str) -> str:
    words = re.split(r'[\s_-]+', s)
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:])
