import logging
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoDBManger:
    def __init__(self) -> None:
        self.client: AsyncMongoClient[Any] | None = None
        self.database: AsyncDatabase[Any] | None = None
        self._collections: dict[str, AsyncCollection[Any]] = {}  # Cache for references

    async def connect(self) -> None:
        """
        Establish a connection to MongoDB.
        """
        try:
            self.client = AsyncMongoClient(
                settings.MONGODB_URI,
                maxPoolSize=50,  # Maximum connections in pool
                minPoolSize=5,   # Minimum connections to maintain
            )

            # Explicitly connect to verify connection
            await self.client.aconnect()

            # Get database reference
            self.database = self.client[settings.MONGODB_NAME]

            # Test the database connection
            await self.database.command("ping")
            logger.info("Connected to MongoDB database: %s", settings.MONGODB_NAME)

        except Exception as e:
            logger.error("Failed to connect to MongoDB: %s", str(e))
            raise

    async def disconnect(self) -> None:
        """
        Clean shutdown of MongoDB connection.
        """
        if self.client:
            try:
                # Clear collection cache
                self._collections.clear()

                # Close the client connection
                await self.client.aclose()
                logger.info("Disconnected from MongoDB")

            except Exception as e:
                logger.error("Error disconnecting from MongoDB: %s", str(e))

    async def get_collection(self, collection_name: str) -> AsyncCollection[Any]:
        """
        Get a collection reference with caching.
        """
        if collection_name not in self._collections:
            if self.database is None:
                raise RuntimeError("Database not connected. Call `connect()` first.")

            self._collections[collection_name] = self.database[collection_name]

        return self._collections[collection_name]

    async def health_check(self) -> bool:
        """
        Check if database connection is healthy.
        """
        if not self.database:
            return False

        try:
            # Ping the database to check if it's reachable
            await self.database.command("ping")
            return True
        except Exception:
            return False


mongodb = MongoDBManger()
