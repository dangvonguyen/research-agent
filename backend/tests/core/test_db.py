from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.core.db import MongoDBManger


class TestMongoDBManger:
    """Tests for the MongoDB connection manager."""

    @pytest.mark.asyncio
    async def test_connect(self) -> None:
        mongodb = MongoDBManger()

        # Setup mocks
        mock_client = AsyncMock()
        mock_db = AsyncMock()

        with patch("app.core.db.AsyncMongoClient", return_value=mock_client):
            # Mock client to return mock database
            mock_client.__getitem__.return_value = mock_db

            # Call connect
            await mongodb.connect()

            # Assertions
            assert mongodb.client == mock_client
            assert mongodb.database == mock_db
            mock_client.aconnect.assert_called_once()
            mock_db.command.assert_called_once_with("ping")

    @pytest.mark.asyncio
    async def test_connect_failure(self) -> None:
        mongodb = MongoDBManger()

        # Setup to raise an exception
        with patch(
            "app.core.db.AsyncMongoClient", side_effect=Exception("Connection error")
        ):
            with pytest.raises(Exception, match="Connection error"):
                await mongodb.connect()

            # Assertions
            assert mongodb.client is None
            assert mongodb.database is None

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        mongodb = MongoDBManger()

        # Setup mocks
        mongodb.client = AsyncMock()
        mongodb.database = AsyncMock()
        mongodb._collections = {"test": Mock()}

        # Call disconnect
        await mongodb.disconnect()

        # Assertions
        assert len(mongodb._collections) == 0
        mongodb.client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_no_client(self) -> None:
        mongodb = MongoDBManger()
        mongodb.client = None

        # Should not raise any exceptions
        await mongodb.disconnect()

    @pytest.mark.asyncio
    async def test_get_collection_with_cache(self) -> None:
        mongodb = MongoDBManger()
        mock_db = MagicMock()
        mock_coll_1, mock_coll_2 = Mock(), Mock()

        # Setup mocks
        mongodb.database = mock_db
        mock_db.__getitem__.side_effect = [mock_coll_1, mock_coll_2]

        # First call - should access database
        assert mongodb.get_collection("test_collection_1") == mock_coll_1
        assert len(mongodb._collections) == 1
        mock_db.__getitem__.assert_called_once_with("test_collection_1")

        # Reset mock to check no additional calls
        mock_db.__getitem__.reset_mock()

        # Second call - should use cache
        assert mongodb.get_collection("test_collection_1") == mock_coll_1
        assert len(mongodb._collections) == 1
        mock_db.__getitem__.assert_not_called()

        # Third call - different collection name
        assert mongodb.get_collection("test_collection_2") == mock_coll_2
        assert len(mongodb._collections) == 2
        mock_db.__getitem__.assert_called_once_with("test_collection_2")

    @pytest.mark.asyncio
    async def test_get_collection_not_connected(self) -> None:
        mongodb = MongoDBManger()
        mongodb.database = None

        with pytest.raises(RuntimeError, match="Database not connected"):
            mongodb.get_collection("test_collection")

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        mongodb = MongoDBManger()
        mongodb.database = AsyncMock()

        assert await mongodb.health_check() is True
        mongodb.database.command.assert_called_once_with("ping")

    @pytest.mark.asyncio
    async def test_health_check_failure_no_database(self) -> None:
        mongodb = MongoDBManger()
        mongodb.database = None

        assert await mongodb.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_failure_exception(self) -> None:
        mongodb = MongoDBManger()
        mock_db = AsyncMock()
        mock_db.command.side_effect = Exception("Database error")
        mongodb.database = mock_db

        assert await mongodb.health_check() is False
