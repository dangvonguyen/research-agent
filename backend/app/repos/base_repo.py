import logging
from abc import ABC
from datetime import UTC, datetime
from typing import Any, TypeVar

from bson import ObjectId
from pymongo import IndexModel

from app.core.db import mongodb
from app.models import (
    BaseCreate,
    BaseDocument,
    BaseUpdate,
    CreateResponse,
    DeleteResponse,
    UpdateResponse,
)

DocT = TypeVar("DocT", bound=BaseDocument)
CreateT = TypeVar("CreateT", bound=BaseCreate)
UpdateT = TypeVar("UpdateT", bound=BaseUpdate)

logger = logging.getLogger(__name__)


class BaseRepository[DocT: BaseDocument, CreateT: BaseCreate, UpdateT: BaseUpdate](ABC):
    """Base repository with common CRUD operations for MongoDB collections."""

    collection_name: str
    model_class: type[DocT]
    indexes: list[IndexModel] | None = None

    @classmethod
    async def _create_indexes(cls) -> None:
        """
        Create indexes for the collection.
        """
        logger.debug("Creating indexes for collection '%s'", cls.collection_name)
        collection = mongodb.get_collection(cls.collection_name)

        indexes = [
            *(cls.indexes or []),
            IndexModel([("updated_at", 1)], name=f"{cls.collection_name[:-1]}_updated_at"),
        ]

        try:
            result = await collection.create_indexes(indexes)
            logger.debug(
                "Created %d indexes for collection '%s'",
                len(result), cls.collection_name,
            )
        except Exception as e:
            logger.error(
                "Error creating indexes for collection '%s': %s",
                cls.collection_name, str(e),
            )
            raise

    @classmethod
    async def get_by_id(cls, id: str) -> DocT | None:
        """
        Get a document by ID.
        """
        return await cls.get_one({"_id": ObjectId(id)})

    @classmethod
    async def update_by_id(
        cls, id: str, obj: UpdateT | None = None, **additional_fields: Any
    ) -> UpdateResponse:
        """
        Update a document by ID.
        """
        logger.debug(
            "Updating document in collection '%s' by ID '%s'",
            cls.collection_name, id,
        )
        return await cls.update_one({"_id": ObjectId(id)}, obj, **additional_fields)

    @classmethod
    async def delete_by_id(cls, id: str) -> DeleteResponse:
        """
        Delete a document by ID.
        """
        logger.debug(
            "Deleting document from collection '%s' by ID '%s'",
            cls.collection_name, id,
        )
        return await cls.delete_one({"_id": ObjectId(id)})

    @classmethod
    async def create_one(cls, obj: CreateT) -> CreateResponse:
        """
        Create a new document.
        """
        logger.debug("Creating new document in collection '%s'", cls.collection_name)
        collection = mongodb.get_collection(cls.collection_name)

        now = datetime.now(UTC)
        obj_dict = obj.model_dump(mode="json")
        obj_dict["created_at"] = now
        obj_dict["updated_at"] = now

        try:
            result = await collection.insert_one(obj_dict)
            obj_id = str(result.inserted_id)
            logger.debug(
                "Successfully created document '%s' in collection '%s'",
                obj_id, cls.collection_name,
            )

            return CreateResponse(
                success=True,
                message="Document successfully created",
                created_count=1,
                created_ids=[obj_id],
            )

        except Exception as e:
            logger.error(
                "Error creating document in collection '%s': %s",
                cls.collection_name, str(e),
            )
            raise

    @classmethod
    async def create_many(cls, objs: list[CreateT]) -> CreateResponse:
        """
        Create many documents.
        """
        logger.debug(
            "Creating %d documents in collection '%s'", len(objs), cls.collection_name
        )
        collection = mongodb.get_collection(cls.collection_name)

        if not objs:
            logger.warning(
                "No documents to create in collection '%s'", cls.collection_name
            )
            return CreateResponse(
                success=False,
                message="No documents to create",
                created_count=0,
                created_ids=[],
            )

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
                "Successfully created %d documents in collection '%s'",
                len(obj_ids), cls.collection_name,
            )

            return CreateResponse(
                success=True,
                message="Documents successfully created",
                created_count=len(obj_ids),
                created_ids=obj_ids,
            )

        except Exception as e:
            logger.error(
                "Error creating many documents in collection '%s': %s",
                cls.collection_name, str(e),
            )
            raise

    @classmethod
    async def get_one(cls, query: dict[str, Any] | None = None) -> DocT | None:
        """
        Get a single document by a query.
        """
        if query is None:
            query = {}

        logger.debug(
            "Retrieving document in collection '%s' by query '%s'",
            cls.collection_name, query,
        )
        collection = mongodb.get_collection(cls.collection_name)

        try:
            obj_data = await collection.find_one(query)
            if obj_data:
                logger.debug(
                    "Found document in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                obj_data["_id"] = str(obj_data["_id"])
                return cls.model_class(**obj_data)  # type: ignore
            else:
                logger.debug(
                    "Document not found in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                return None

        except Exception as e:
            logger.error(
                "Error retrieving document in collection '%s' by query '%s': %s",
                cls.collection_name, query, str(e),
            )
            raise

    @classmethod
    async def get_many(
        cls, query: dict[str, Any] | None = None, skip: int = 0, limit: int = 100
    ) -> list[DocT]:
        """
        Get many documents with pagination and optional query.
        """
        if query is None:
            query = {}

        logger.debug(
            "Retrieving documents in collection '%s' (skip=%d, limit=%d, query=%s)",
            cls.collection_name, skip, limit, query,
        )
        collection = mongodb.get_collection(cls.collection_name)

        objects = []
        try:
            cursor = (
                collection.find(query).skip(skip).limit(limit).sort("updated_at", -1)
            )

            doc_count = 0
            async for obj in cursor:
                obj["_id"] = str(obj["_id"])
                objects.append(cls.model_class(**obj))
                doc_count += 1

            logger.debug(
                "Successfully retrieved %d documents in collection '%s'",
                doc_count, cls.collection_name,
            )
            return objects

        except Exception as e:
            logger.error(
                "Error retrieving documents in collection '%s': %s",
                cls.collection_name, str(e),
            )
            raise

    @classmethod
    async def update_one(
        cls, query: dict[str, Any], obj: UpdateT | None = None, **additional_fields: Any
    ) -> UpdateResponse:
        """
        Update a document.
        """
        logger.debug(
            "Updating document in collection '%s' by query '%s'",
            cls.collection_name, query,
        )
        collection = mongodb.get_collection(cls.collection_name)

        update_data = obj.model_dump(mode="json", exclude_unset=True) if obj else {}
        update_data.update(additional_fields)

        if not update_data:
            logger.debug(
                "No fields to update for document in collection '%s' by query '%s'",
                cls.collection_name, query,
            )
            return UpdateResponse(
                success=False,
                message="No fields to update",
                matched_count=0,
                modified_count=0,
            )

        update_data["updated_at"] = datetime.now(UTC)

        try:
            result = await collection.update_one(query, {"$set": update_data})

            if result.matched_count == 0:
                logger.debug(
                    "Document not found for update in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                return UpdateResponse(
                    success=False,
                    message="Document not found for update",
                    matched_count=0,
                    modified_count=0,
                )

            if result.modified_count > 0:
                logger.debug(
                    "Document successfully updated in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                return UpdateResponse(
                    success=True,
                    message="Document successfully updated",
                    matched_count=result.matched_count,
                    modified_count=result.modified_count,
                )
            else:
                logger.debug(
                    "Document found but no changes made in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                return UpdateResponse(
                    success=False,
                    message="Document found but no changes made",
                    matched_count=result.matched_count,
                    modified_count=0,
                )

        except Exception as e:
            logger.error(
                "Error updating document in collection '%s' by query '%s': %s",
                cls.collection_name, query, str(e),
            )
            raise

    @classmethod
    async def update_many(
        cls, query: dict[str, Any], obj: UpdateT | None = None, **additional_fields: Any
    ) -> UpdateResponse:
        """
        Update many documents.
        """
        logger.debug(
            "Updating many documents in collection '%s' by query '%s'",
            cls.collection_name, query,
        )
        collection = mongodb.get_collection(cls.collection_name)

        update_data = obj.model_dump(mode="json", exclude_unset=True) if obj else {}
        update_data.update(additional_fields)

        if not update_data:
            logger.debug(
                "No fields to update for many documents in collection '%s' by query '%s'",
                cls.collection_name, query,
            )
            return UpdateResponse(
                success=False,
                message="No fields to update",
                matched_count=0,
                modified_count=0,
            )

        update_data["updated_at"] = datetime.now(UTC)

        try:
            result = await collection.update_many(query, {"$set": update_data})

            if result.matched_count == 0:
                logger.debug(
                    "Documents not found for update in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                return UpdateResponse(
                    success=False,
                    message="Documents not found for update",
                    matched_count=0,
                    modified_count=0,
                )

            if result.modified_count > 0:
                logger.debug(
                    "Documents successfully updated in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                return UpdateResponse(
                    success=True,
                    message="Documents successfully updated",
                    matched_count=result.matched_count,
                    modified_count=result.modified_count,
                )
            else:
                logger.debug(
                    "Documents found but no changes made in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                return UpdateResponse(
                    success=False,
                    message="Documents found but no changes made",
                    matched_count=result.matched_count,
                    modified_count=0,
                )

        except Exception as e:
            logger.error(
                "Error updating document in collection '%s' by query '%s': %s",
                cls.collection_name, query, str(e),
            )
            raise

    @classmethod
    async def delete_one(cls, query: dict[str, Any] | None = None) -> DeleteResponse:
        """
        Delete a document by a query.
        """
        if query is None:
            query = {}

        logger.debug(
            "Deleting document in collection '%s' by query '%s'",
            cls.collection_name, query,
        )
        collection = mongodb.get_collection(cls.collection_name)

        try:
            result = await collection.delete_one(query)
            if result.deleted_count > 0:
                logger.debug(
                    "Successfully deleted document in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                return DeleteResponse(
                    success=True,
                    message="Document successfully deleted",
                    deleted_count=result.deleted_count,
                )
            else:
                logger.debug(
                    "Document not found for deletion in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                return DeleteResponse(
                    success=False,
                    message="Document not found for deletion",
                    deleted_count=0,
                )

        except Exception as e:
            logger.error(
                "Error deleting document in collection '%s' by query '%s': %s",
                cls.collection_name, query, str(e),
            )
            raise

    @classmethod
    async def delete_many(cls, query: dict[str, Any] | None = None) -> DeleteResponse:
        """
        Delete many documents by a query.
        """
        if query is None:
            query = {}

        logger.debug(
            "Deleting many documents in collection '%s' by query '%s'",
            cls.collection_name, query,
        )
        collection = mongodb.get_collection(cls.collection_name)

        try:
            result = await collection.delete_many(query)
            if result.deleted_count > 0:
                logger.debug(
                    "Successfully deleted %d documents in collection '%s' by query '%s'",
                    result.deleted_count, cls.collection_name, query,
                )
                return DeleteResponse(
                    success=True,
                    message="Documents successfully deleted",
                    deleted_count=result.deleted_count,
                )
            else:
                logger.debug(
                    "Documents not found for deletion in collection '%s' by query '%s'",
                    cls.collection_name, query,
                )
                return DeleteResponse(
                    success=False,
                    message="Documents not found for deletion",
                    deleted_count=0,
                )

        except Exception as e:
            logger.error(
                "Error deleting many documents in collection '%s' by query '%s': %s",
                cls.collection_name, query, str(e),
            )
            raise
