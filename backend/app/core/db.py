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
        logger.debug("MongoDB manager initialized")

    async def connect(self) -> None:
        """
        Establish a connection to MongoDB.
        """
        try:
            # Log without credentials
            logger.debug("Creating MongoDB client with URI: %s", settings.MONGODB_URI)

            self.client = AsyncMongoClient(
                settings.MONGODB_URI,
                maxPoolSize=50,  # Maximum connections in pool
                minPoolSize=5,   # Minimum connections to maintain
            )

            # Explicitly connect to verify connection
            logger.debug("Establishing MongoDB connection...")
            await self.client.aconnect()

            # Get database reference
            self.database = self.client[settings.MONGODB_NAME]
            logger.debug("Database reference created for: %s", settings.MONGODB_NAME)

            # Test the database connection
            await self.database.command("ping")
            logger.info(
                "Connected successfully to MongoDB database: %s", settings.MONGODB_NAME
            )

        except Exception as e:
            logger.error("MongoDB connection failed: %s", str(e))
            raise

    async def disconnect(self) -> None:
        """
        Clean shutdown of MongoDB connection.
        """
        if self.client:
            try:
                # Clear collection cache
                collection_count = len(self._collections)
                self._collections.clear()
                logger.debug(
                    "Cleared %d cached collection references", collection_count
                )

                # Close the client connection
                logger.debug("Closing MongoDB connection...")
                await self.client.aclose()
                logger.info("MongoDB connection closed successfully")

            except Exception as e:
                logger.error("Error during MongoDB disconnection: %s", str(e))
        else:
            logger.warning("Disconnect called but MongoDB client was not initialized")

    def get_collection(self, collection_name: str) -> AsyncCollection[Any]:
        """
        Get a collection reference with caching.
        """
        if collection_name not in self._collections:
            if self.database is None:
                logger.error(
                    "Attempted to access collection '%s' but database is not connected",
                    collection_name,
                )
                raise RuntimeError("Database not connected. Call `connect()` first.")

            logger.debug("Creating new collection reference: %s", collection_name)
            self._collections[collection_name] = self.database[collection_name]
        else:
            logger.debug("Using cached collection reference: %s", collection_name)

        return self._collections[collection_name]

    async def health_check(self) -> bool:
        """
        Check if database connection is healthy.
        """
        if self.database is None:
            logger.warning("Health check failed: database connection not initialized")
            return False

        try:
            # Ping the database to check if it's reachable
            logger.debug("Performing database health check...")
            await self.database.command("ping")
            logger.debug("Health check successful: database connection is healthy")
            return True
        except Exception as e:
            logger.error("Health check failed: %s", str(e))
            return False


mongodb = MongoDBManger()
