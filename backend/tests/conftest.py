from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any

import mongomock
import pytest
from pymongo.results import (
    DeleteResult,
    InsertManyResult,
    InsertOneResult,
    UpdateResult,
)

from app.core.db import MongoDBManger, mongodb


@pytest.fixture
def mock_mongodb() -> Generator[MongoDBManger, None, None]:
    """
    Mock MongoDB connection for testing.
    """
    # Save original client
    original_client = mongodb.client
    original_database = mongodb.database

    # Create mock client
    mock_client = AsyncMongoClientMock()
    mock_database = mock_client["test_db"]

    # Replace the app's MongoDB client and database
    mongodb.client = mock_client  # type: ignore
    mongodb.database = mock_database  # type: ignore
    mongodb._collections = {}

    yield mongodb

    # Restore original client
    mongodb.client = original_client
    mongodb.database = original_database
    mongodb._collections = {}


class AsyncMongoClientMock:
    """Async wrapper around mongomock MongoClient"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._sync_client = mongomock.MongoClient(*args, **kwargs)  # type: ignore

    def __getitem__(self, database: str) -> AsyncMongoDatabaseMock:
        """Get database by name"""
        return AsyncMongoDatabaseMock(self._sync_client[database])

    def __getattr__(self, database: str) -> AsyncMongoDatabaseMock:
        """Get database by attribute access"""
        return AsyncMongoDatabaseMock(getattr(self._sync_client, database))


class AsyncMongoDatabaseMock:
    """Async wrapper around mongomock Database"""

    def __init__(self, database: mongomock.Database) -> None:  # type: ignore
        self._sync_database = database

    def __getitem__(self, collection: str) -> AsyncMongoCollectionMock:
        """Get collection by name"""
        return AsyncMongoCollectionMock(self._sync_database[collection])

    def __getattr__(self, collection: str) -> AsyncMongoCollectionMock:
        """Get collection by attribute access"""
        return AsyncMongoCollectionMock(getattr(self._sync_database, collection))


class AsyncMongoCollectionMock:
    """Async wrapper around mongomock Collection"""

    def __init__(self, collection: mongomock.Collection) -> None:  # type: ignore
        self._sync_collection = collection

    async def find_one(
        self, filter: dict[str, Any] | None = None, *args: Any, **kwargs: Any
    ) -> Any | None:
        return await asyncio.to_thread(
            self._sync_collection.find_one, filter, *args, **kwargs
        )

    def find(self, filter: dict[str, Any] | None = None, *args: Any, **kwargs: Any):
        # TODO: Implement this
        pass

    async def insert_one(
        self, document: dict[str, Any], *args: Any, **kwargs: Any
    ) -> InsertOneResult:
        return await asyncio.to_thread(
            self._sync_collection.insert_one, document, *args, **kwargs
        )

    async def insert_many(
        self, documents: list[dict[str, Any]], *args: Any, **kwargs: Any
    ) -> InsertManyResult:
        return await asyncio.to_thread(
            self._sync_collection.insert_many, documents, *args, **kwargs
        )

    async def update_one(
        self, filter: dict[str, Any], update: dict[str, Any], *args: Any, **kwargs: Any
    ) -> UpdateResult:
        return await asyncio.to_thread(
            self._sync_collection.update_one, filter, update, *args, **kwargs
        )

    async def update_many(
        self, filter: dict[str, Any], update: dict[str, Any], *args: Any, **kwargs: Any
    ) -> UpdateResult:
        return await asyncio.to_thread(
            self._sync_collection.update_many, filter, update, *args, **kwargs
        )

    async def delete_one(
        self, filter: dict[str, Any], *args: Any, **kwargs: Any
    ) -> DeleteResult:
        return await asyncio.to_thread(
            self._sync_collection.delete_one, filter, *args, **kwargs
        )

    async def delete_many(
        self, filter: dict[str, Any], *args: Any, **kwargs: Any
    ) -> DeleteResult:
        return await asyncio.to_thread(
            self._sync_collection.delete_many, filter, *args, **kwargs
        )

    async def count_documents(
        self, filter: dict[str, Any] | None = None, *args: Any, **kwargs: Any
    ) -> int:
        return await asyncio.to_thread(
            self._sync_collection.count_documents, filter or {}, *args, **kwargs
        )
