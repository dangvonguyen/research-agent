from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import settings


class MongoDBManger:
    def __init__(self) -> None:
        self.client: AsyncMongoClient[Any] | None = None
        self.database: AsyncDatabase[Any] | None = None

    async def connect(self) -> None:
        """
        Establish a connection to MongoDB.
        """
        self.client = AsyncMongoClient(settings.MONGODB_URI)

        await self.client.aconnect()

        self.database = self.client[settings.MONGODB_NAME]

    async def close(self) -> None:
        """
        Clean shutdown of MongoDB connection.
        """
        if self.client:
            await self.client.aclose()

    async def get_collection(self, collection_name: str) -> AsyncCollection[Any]:
        """
        Get a collection reference with caching.
        """
        return self.database[collection_name]


mongodb = MongoDBManger()
