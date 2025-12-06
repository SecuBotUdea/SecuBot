from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class PyObjectId(ObjectId):
    """ObjectId compatible con Pydantic v2 (serializa como string)."""

    @classmethod
    def __get_pydantic_core_schema__(cls, _source, _handler):
        from pydantic_core import core_schema

        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.str_schema(),
                ]
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        json_schema = handler(schema)
        json_schema.update(type='string', title='ObjectId')
        return json_schema


class BaseModelDB(BaseModel):
    """
    Modelo base *solo datos* para documentos persistentes.

    - Define el contrato de datos entre componentes.
    - Compatible con Motor (MongoDB) y FastAPI/Pydantic v2.
    - SIN lógica de acceso a datos (upsert/get): eso va en el repository.
    """

    id: PyObjectId | None = Field(default=None, alias='_id')
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        from_attributes=True,
        json_encoders={ObjectId: lambda oid: str(oid)},
    )
