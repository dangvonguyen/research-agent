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
        test_doc = {
            "_id": doc_id,
            "field1": "test",
            "field2": 123,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
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
    async def test_get_no_query(self, mock_mongodb) -> None:
        """
        Test getting a single document without query filter.
        """
        # Arrange
        test_create = SampleCreate(field1="test", field2=123)
        await SampleRepository.create_one(test_create)

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
        test_creates = [
            SampleCreate(field1="test1", field2=100),
            SampleCreate(field1="test2", field2=200),
            SampleCreate(field1="test3"),
        ]
        await SampleRepository.create_many(test_creates)

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
