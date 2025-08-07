import asyncio
from datetime import UTC, datetime

import pytest
from bson import ObjectId

from app.core.db import mongodb
from app.models import BaseCreate, BaseDocument, BaseUpdate
from app.repos import BaseRepository


# Define test models that inherit from BaseCreate, BaseUpdate, and BaseDocument
class SampleCreate(BaseCreate):
    field1: str
    field2: int | None = None


class SampleUpdate(BaseUpdate):
    field1: str | None = None
    field2: int | None = None


class SampleDoc(BaseDocument):
    field1: str
    field2: int | None = None


# Define a test repository that uses the test models
class SampleRepository(BaseRepository[SampleDoc, SampleCreate, SampleUpdate]):
    collection_name = "test_collection"
    model_class = SampleDoc


class TestBaseRepository:
    """Test for the BaseRepository class."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, mock_mongodb) -> None:
        """
        Test successfully retrieving a document by ID.
        """
        collection = mongodb.get_collection(SampleRepository.collection_name)

        # Arrange
        doc_id = ObjectId()
        now = datetime.now(UTC)
        test_doc = {
            "_id": doc_id,
            "field1": "test",
            "field2": 123,
            "created_at": now,
            "updated_at": now,
        }
        await collection.insert_one(test_doc)

        # Act
        result = await SampleRepository.get_by_id(str(doc_id))

        # Assert
        assert result is not None
        assert result.field1 == test_doc["field1"]
        assert result.field2 == test_doc["field2"]

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_mongodb) -> None:
        """
        Test retrieving a non-existent document by ID.
        """
        # Act
        result = await SampleRepository.get_by_id(str(ObjectId()))

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_create_one(self, mock_mongodb) -> None:
        """
        Test creating a single document.
        """
        # Arrange
        test_create = SampleCreate(field1="test", field2=123)

        # Act
        result = await SampleRepository.create_one(test_create)

        # Assert
        assert result.success is True
        assert result.created_count == 1
        assert len(result.created_ids) == 1

        # Verify the document was created
        sample = await SampleRepository.get_by_id(result.created_ids[0])
        assert sample is not None
        assert sample.field1 == "test"
        assert sample.field2 == 123
        assert sample.created_at is not None
        assert sample.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_many_success(self, mock_mongodb) -> None:
        """
        Test creating multiple documents.
        """
        # Arrange
        test_creates = [
            SampleCreate(field1="test1", field2=100),
            SampleCreate(field1="test2", field2=200),
            SampleCreate(field1="test3"),
        ]

        # Act
        result = await SampleRepository.create_many(test_creates)

        # Assert
        assert result.success is True
        assert result.created_count == 3
        assert len(result.created_ids) == 3

        # Verify all documents were created
        expected_fields = [("test1", 100), ("test2", 200), ("test3", None)]
        for i, doc_id in enumerate(result.created_ids):
            sample = await SampleRepository.get_by_id(doc_id)
            assert sample is not None
            assert sample.field1 == expected_fields[i][0]
            assert sample.field2 == expected_fields[i][1]

    @pytest.mark.asyncio
    async def test_create_many_empty_list(self, mock_mongodb) -> None:
        """
        Test creating many documents with empty list.
        """
        # Act
        result = await SampleRepository.create_many([])

        # Assert
        assert result.success is False
        assert result.created_count == 0
        assert len(result.created_ids) == 0

    @pytest.mark.asyncio
    async def test_get_one_no_query(self, mock_mongodb) -> None:
        """
        Test getting a single document without query filter.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        now = datetime.now(UTC)
        test_doc = {
            "_id": ObjectId(),
            "field1": "test",
            "field2": 123,
            "created_at": now,
            "updated_at": now,
        }
        await collection.insert_one(test_doc)

        # Act
        result = await SampleRepository.get_one()

        # Assert
        assert result is not None
        assert result.field1 == "test"
        assert result.field2 == 123

    @pytest.mark.asyncio
    async def test_get_one_with_query(self, mock_mongodb) -> None:
        """
        Test getting a single document with a query filter.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        now = datetime.now(UTC)
        test_docs = [
            {
                "_id": ObjectId(),
                "field1": "test1",
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "test2",
                "field2": 200,
                "created_at": now,
                "updated_at": now,
            },
        ]
        await collection.insert_many(test_docs)

        # Act
        result = await SampleRepository.get_one({"field1": "test2"})

        # Assert
        assert result is not None
        assert result.field1 == "test2"
        assert result.field2 == 200

    @pytest.mark.asyncio
    async def test_get_one_not_found(self, mock_mongodb) -> None:
        """
        Test getting a single document that doesn't exist.
        """
        # Act
        result = await SampleRepository.get_one({"field1": "nonexistent"})

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_many_no_query(self, mock_mongodb) -> None:
        """
        Test getting multiple documents without query filter.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        now = datetime.now(UTC)
        test_docs = [
            {
                "_id": ObjectId(),
                "field1": "test1",
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "test2",
                "created_at": now,
                "updated_at": now,
            },
        ]
        await collection.insert_many(test_docs)

        # Act
        results = await SampleRepository.get_many()

        assert len(results) == 2
        assert all(isinstance(doc, SampleDoc) for doc in results)

    @pytest.mark.asyncio
    async def test_get_many_with_query(self, mock_mongodb) -> None:
        """
        Test getting multiple documents with a query filter.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        now = datetime.now(UTC)
        test_docs = [
            {
                "_id": ObjectId(),
                "field1": "match",
                "field2": 1,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "match",
                "field2": 2,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "nomatch",
                "field2": 3,
                "created_at": now,
                "updated_at": now,
            },
        ]
        await collection.insert_many(test_docs)

        # Act
        results = await SampleRepository.get_many({"field1": "match"})

        # Assert
        assert len(results) == 2
        assert all(doc.field1 == "match" for doc in results)

    @pytest.mark.asyncio
    async def test_get_many_with_pagination(self, mock_mongodb) -> None:
        """
        Test getting multiple documents with a query filter.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        now = datetime.now(UTC)
        test_docs = []
        for i in range(5):
            test_docs.append(
                {
                    "_id": ObjectId(),
                    "field1": f"doc{i}",
                    "field2": i,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        await collection.insert_many(test_docs)

        # Act
        results = await SampleRepository.get_many(skip=2, limit=2)

        # Assert
        assert len(results) == 2
        assert all(doc.field1 in ["doc2", "doc3"] for doc in results)

    @pytest.mark.asyncio
    async def test_update_one_success(self, mock_mongodb) -> None:
        """
        Test getting multiple documents with a query filter.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        doc_id = ObjectId()
        now = datetime.now(UTC)
        test_doc = {
            "_id": doc_id,
            "field1": "original",
            "field2": 1,
            "created_at": now,
            "updated_at": now,
        }
        await collection.insert_one(test_doc)

        update_obj = SampleUpdate(field1="updated", field2=2)

        # Sleep to ensure the updated_at field is different
        await asyncio.sleep(0.01)

        # Act
        update_result = await SampleRepository.update_one(
            {"field1": "original"}, obj=update_obj
        )

        # Assert
        assert update_result.success is True
        assert update_result.matched_count == 1
        assert update_result.modified_count == 1

        # Verify the document was updated
        updated_doc = await SampleRepository.get_by_id(str(doc_id))
        assert updated_doc is not None
        assert updated_doc.field1 == "updated"
        assert updated_doc.field2 == 2
        assert updated_doc.updated_at > now.replace(tzinfo=None)

    @pytest.mark.asyncio
    async def test_update_one_with_additional_fields(self, mock_mongodb) -> None:
        """
        Test updating a document with additional fields.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        doc_id = ObjectId()
        now = datetime.now(UTC)
        test_doc = {
            "_id": doc_id,
            "field1": "original",
            "field2": 1,
            "created_at": now,
            "updated_at": now,
        }
        await collection.insert_one(test_doc)

        # Act
        update_result = await SampleRepository.update_one(
            {"field1": "original"}, None, field2=2
        )

        # Assert
        assert update_result.success is True
        assert update_result.matched_count == 1
        assert update_result.modified_count == 1

        # Verify the document was updated
        updated_doc = await SampleRepository.get_by_id(str(doc_id))
        assert updated_doc is not None
        assert updated_doc.field2 == 2

    @pytest.mark.asyncio
    async def test_update_one_not_found(self, mock_mongodb) -> None:
        """
        Test updating a document that doesn't exist.
        """
        # Arrange
        update_obj = SampleUpdate(field1="updated", field2=2)

        # Act
        update_result = await SampleRepository.update_one(
            {"field1": "nonexistent"}, obj=update_obj
        )

        # Assert
        assert update_result.success is False
        assert update_result.matched_count == 0
        assert update_result.modified_count == 0

    @pytest.mark.asyncio
    async def test_update_one_no_fields(self, mock_mongodb) -> None:
        """
        Test updating a document with no fields to update.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        doc_id = ObjectId()
        now = datetime.now(UTC)
        test_doc = {
            "_id": doc_id,
            "field1": "original",
            "field2": 1,
            "created_at": now,
            "updated_at": now,
        }
        await collection.insert_one(test_doc)

        # Act
        update_result = await SampleRepository.update_one({"field1": "original"}, None)

        # Assert
        assert update_result.success is False
        assert update_result.matched_count == 0
        assert update_result.modified_count == 0

    @pytest.mark.asyncio
    async def test_update_many_success(self, mock_mongodb) -> None:
        """
        Test updating multiple documents.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        now = datetime.now(UTC)
        test_docs = [
            {
                "_id": ObjectId(),
                "field1": "update_me",
                "field2": 1,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "update_me",
                "field2": 2,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "dont_update",
                "field2": 3,
                "created_at": now,
                "updated_at": now,
            },
        ]
        await collection.insert_many(test_docs)

        update_obj = SampleUpdate(field2=10)

        # Act
        result = await SampleRepository.update_many({"field1": "update_me"}, update_obj)

        # Assert
        assert result.success is True
        assert result.matched_count == 2
        assert result.modified_count == 2

        # Verify updates
        updated_docs = [
            await SampleRepository.get_by_id(str(doc["_id"]))
            for doc in test_docs
            if doc["field1"] == "update_me"
        ]
        assert len(updated_docs) == 2
        assert all(doc is not None and doc.field2 == 10 for doc in updated_docs)

    @pytest.mark.asyncio
    async def test_delete_one_success(self, mock_mongodb) -> None:
        """
        Test updating multiple documents that don't exist.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        doc_id = ObjectId()
        now = datetime.now(UTC)
        test_doc = {
            "_id": doc_id,
            "field1": "delete_me",
            "field2": 100,
            "created_at": now,
            "updated_at": now,
        }
        await collection.insert_one(test_doc)

        # Act
        result = await SampleRepository.delete_one({"field1": "delete_me"})

        # Assert
        assert result.success is True
        assert result.deleted_count == 1

        # Verify deletion
        deleted_doc = await SampleRepository.get_by_id(str(doc_id))
        assert deleted_doc is None
        assert result.deleted_count == 1

    @pytest.mark.asyncio
    async def test_delete_one_not_found(self, mock_mongodb) -> None:
        """
        Test deleting a document that doesn't exist.
        """
        # Act
        result = await SampleRepository.delete_one({"field1": "nonexistent"})

        # Assert
        assert result.success is False
        assert result.deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_one_with_none_query(self, mock_mongodb) -> None:
        """
        Test deleting a document with None query.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        now = datetime.now(UTC)
        test_doc = [
            {
                "_id": ObjectId(),
                "field1": "test1",
                "field2": 1,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "test2",
                "field2": 2,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "test3",
                "field2": 3,
                "created_at": now,
                "updated_at": now,
            },
        ]
        await collection.insert_many(test_doc)

        # Act
        result = await SampleRepository.delete_one(None)

        # Assert
        assert result.success is True
        assert result.deleted_count == 1

        # Verify deletion
        assert await collection.count_documents({}) == 2

    @pytest.mark.asyncio
    async def test_delete_many_success(self, mock_mongodb) -> None:
        """
        Test deleting multiple documents.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        now = datetime.now(UTC)
        test_docs = [
            {
                "_id": ObjectId(),
                "field1": "delete_me",
                "field2": 1,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "delete_me",
                "field2": 2,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "keep_me",
                "field2": 3,
                "created_at": now,
                "updated_at": now,
            },
        ]
        await collection.insert_many(test_docs)

        # Act
        result = await SampleRepository.delete_many({"field1": "delete_me"})

        # Assert
        assert result.success is True
        assert result.deleted_count == 2

        # Verify deletions
        assert await collection.count_documents({}) == 1

    @pytest.mark.asyncio
    async def test_delete_many_not_found(self, mock_mongodb) -> None:
        """
        Test deleting multiple documents that don't exist.
        """
        # Act
        result = await SampleRepository.delete_many({"field1": "nonexistent"})

        # Assert
        assert result.success is False
        assert result.deleted_count == 0

    @pytest.mark.asyncio
    async def test_delete_many_with_none_query(self, mock_mongodb) -> None:
        """
        Test deleting multiple documents with None query.
        """
        # Arrange
        collection = mongodb.get_collection(SampleRepository.collection_name)
        now = datetime.now(UTC)
        test_doc = [
            {
                "_id": ObjectId(),
                "field1": "test1",
                "field2": 1,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "test2",
                "field2": 2,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "field1": "test3",
                "field2": 3,
                "created_at": now,
                "updated_at": now,
            },
        ]
        await collection.insert_many(test_doc)

        # Act
        result = await SampleRepository.delete_many(None)

        # Assert
        assert result.success is True
        assert result.deleted_count == 3

        # Verify deletion
        assert await collection.count_documents({}) == 0
