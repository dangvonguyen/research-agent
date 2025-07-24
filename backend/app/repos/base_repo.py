from abc import ABC
from datetime import UTC, datetime
from typing import TypeVar

from bson import ObjectId

from app.core.db import mongodb
from app.models import BaseCreate, BaseDocument, BaseUpdate

DocT = TypeVar("DocT", bound=BaseDocument)
CreateT = TypeVar("CreateT", bound=BaseCreate)
UpdateT = TypeVar("UpdateT", bound=BaseUpdate)


class BaseRepository[DocT: BaseDocument, CreateT: BaseCreate, UpdateT: BaseUpdate](ABC):
    """Base repository with common CRUD operations for MongoDB collections."""

    collection_name: str
    model_class: type[DocT]

    @classmethod
    async def create(cls, obj: CreateT) -> DocT:
        """
        Create a new document.
        """
        collection = mongodb.get_collection(cls.collection_name)

        now = datetime.now(UTC)
        obj_dict = obj.model_dump(mode="json")
        obj_dict["created_at"] = now
        obj_dict["updated_at"] = now

        result = await collection.insert_one(obj_dict)

        obj_dict["_id"] = str(result.inserted_id)
        return cls.model_class(**obj_dict)  # type: ignore

    @classmethod
    async def get(cls, id: str) -> DocT | None:
        """
        Get a document by ID.
        """
        collection = mongodb.get_collection(cls.collection_name)

        obj_data = await collection.find_one({"_id": ObjectId(id)})
        if obj_data:
            obj_data["_id"] = str(obj_data["_id"])
            return cls.model_class(**obj_data)  # type: ignore
        else:
            return None

    @classmethod
    async def list(cls, skip: int = 0, limit: int = 100) -> list[DocT]:
        """
        List documents with pagination.
        """
        collection = mongodb.get_collection(cls.collection_name)

        objects = []
        cursor = collection.find().skip(skip).limit(limit).sort("updated_at", -1)

        async for obj in cursor:
            obj["_id"] = str(obj["_id"])
            objects.append(cls.model_class(**obj))

        return objects

    @classmethod
    async def update(cls, id: str, obj: UpdateT) -> DocT | None:
        """
        Update a document.
        """
        collection = mongodb.get_collection(cls.collection_name)

        update_data = obj.model_dump(mode="json", exclude_unset=True)
        if not update_data:
            return await cls.get(id)

        update_data["updated_at"] = datetime.now(UTC)

        result = await collection.update_one(
            {"_id": ObjectId(id)}, {"$set": update_data}
        )

        if result.modified_count:
            return await cls.get(id)
        else:
            return None

    @classmethod
    async def delete(cls, id: str) -> bool:
        """
        Delete a document.
        """
        collection = mongodb.get_collection(cls.collection_name)

        result = await collection.delete_one({"_id": ObjectId(id)})

        return result.deleted_count > 0
