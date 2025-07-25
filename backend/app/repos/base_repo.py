import logging
from abc import ABC
from datetime import UTC, datetime
from typing import TypeVar

from bson import ObjectId

from app.core.db import mongodb
from app.models import BaseCreate, BaseDocument, BaseUpdate

DocT = TypeVar("DocT", bound=BaseDocument)
CreateT = TypeVar("CreateT", bound=BaseCreate)
UpdateT = TypeVar("UpdateT", bound=BaseUpdate)

logger = logging.getLogger(__name__)


class BaseRepository[DocT: BaseDocument, CreateT: BaseCreate, UpdateT: BaseUpdate](ABC):
    """Base repository with common CRUD operations for MongoDB collections."""

    collection_name: str
    model_class: type[DocT]

    @classmethod
    async def create(cls, obj: CreateT) -> DocT:
        """
        Create a new document.
        """
        logger.debug("Creating new document in collection: %s", cls.collection_name)
        collection = mongodb.get_collection(cls.collection_name)

        now = datetime.now(UTC)
        obj_dict = obj.model_dump(mode="json")
        obj_dict["created_at"] = now
        obj_dict["updated_at"] = now

        try:
            result = await collection.insert_one(obj_dict)
            obj_id = str(result.inserted_id)
            logger.debug(
                "Created document with ID %s in collection %s",
                obj_id, cls.collection_name,
            )

            obj_dict["_id"] = obj_id
            return cls.model_class(**obj_dict)  # type: ignore

        except Exception as e:
            logger.error(
                "Failed to create document in %s: %s", cls.collection_name, str(e)
            )
            raise

    @classmethod
    async def create_many(cls, objs: list[CreateT]) -> list[DocT]:
        """
        Create many documents.
        """
        collection = mongodb.get_collection(cls.collection_name)

        obj_dicts = []
        for obj in objs:
            now = datetime.now(UTC)
            obj_dict = obj.model_dump(mode="json")
            obj_dict["created_at"] = now
            obj_dict["updated_at"] = now
            obj_dicts.append(obj_dict)

        try:
            result = await collection.insert_many(obj_dicts)
            obj_ids = [str(obj_id) for obj_id in result.inserted_ids]
            logger.debug(
                "Created %d documents in collection %s",
                len(obj_ids), cls.collection_name,
            )

            objects = []
            for obj_dict in obj_dicts:
                obj_dict["_id"] = obj_ids[obj_dicts.index(obj_dict)]
                objects.append(cls.model_class(**obj_dict))
            return objects

        except Exception as e:
            logger.error(
                "Failed to create many documents in %s: %s", cls.collection_name, str(e)
            )
            raise

    @classmethod
    async def get(cls, id: str) -> DocT | None:
        """
        Get a document by ID.
        """
        logger.debug(
            "Retrieving document with ID %s from collection %s", id, cls.collection_name
        )
        collection = mongodb.get_collection(cls.collection_name)

        try:
            obj_data = await collection.find_one({"_id": ObjectId(id)})
            if obj_data:
                logger.debug(
                    "Found document with ID %s in collection %s",
                    id, cls.collection_name,
                )
                obj_data["_id"] = str(obj_data["_id"])
                return cls.model_class(**obj_data)  # type: ignore
            else:
                logger.debug(
                    "Document with ID %s not found in collection %s",
                    id, cls.collection_name,
                )
                return None

        except Exception as e:
            logger.error(
                "Error retrieving document %s from %s: %s",
                id, cls.collection_name, str(e),
            )
            raise

    @classmethod
    async def list(cls, skip: int = 0, limit: int = 100) -> list[DocT]:
        """
        List documents with pagination.
        """
        logger.debug(
            "Retrieving documents from %s (skip=%d, limit=%d)",
            cls.collection_name, skip, limit,
        )
        collection = mongodb.get_collection(cls.collection_name)

        objects = []
        try:
            cursor = collection.find().skip(skip).limit(limit).sort("updated_at", -1)

            doc_count = 0
            async for obj in cursor:
                obj["_id"] = str(obj["_id"])
                objects.append(cls.model_class(**obj))
                doc_count += 1

            logger.debug(
                "Retrieved %d documents from collection %s",
                doc_count, cls.collection_name,
            )
            return objects

        except Exception as e:
            logger.error(
                "Error retrieving documents from %s: %s", cls.collection_name, str(e)
            )
            raise

    @classmethod
    async def update(cls, id: str, obj: UpdateT) -> DocT | None:
        """
        Update a document.
        """
        logger.debug("Updating document %s in collection %s", id, cls.collection_name)
        collection = mongodb.get_collection(cls.collection_name)

        update_data = obj.model_dump(mode="json", exclude_unset=True)
        if not update_data:
            logger.debug("No fields to update for document %s", id)
            return await cls.get(id)

        update_data["updated_at"] = datetime.now(UTC)

        try:
            result = await collection.update_one(
                {"_id": ObjectId(id)}, {"$set": update_data}
            )

            if result.matched_count == 0:
                logger.debug(
                    "Document %s not found for update in collection %s",
                    id, cls.collection_name,
                )
                return None

            if result.modified_count > 0:
                logger.debug(
                    "Document %s successfully updated in collection %s",
                    id,
                    cls.collection_name,
                )
            else:
                logger.debug(
                    "Document %s found but no changes made in collection %s",
                    id,
                    cls.collection_name,
                )

            return await cls.get(id)

        except Exception as e:
            logger.error(
                "Error updating document %s in %s: %s", id, cls.collection_name, str(e)
            )
            raise

    @classmethod
    async def delete(cls, id: str) -> bool:
        """
        Delete a document.
        """
        logger.debug("Deleting document %s from collection %s", id, cls.collection_name)
        collection = mongodb.get_collection(cls.collection_name)

        try:
            result = await collection.delete_one({"_id": ObjectId(id)})

            if result.deleted_count > 0:
                logger.debug(
                    "Successfully deleted document %s from collection %s",
                    id,
                    cls.collection_name,
                )
                return True
            else:
                logger.debug(
                    "Document %s not found for deletion in collection %s",
                    id,
                    cls.collection_name,
                )
                return False

        except Exception as e:
            logger.error(
                "Error deleting document %s from %s: %s",
                id,
                cls.collection_name,
                str(e),
            )
            raise
