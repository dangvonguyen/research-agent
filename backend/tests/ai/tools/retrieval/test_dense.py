"""Unit tests for DenseRetrieverTool."""

from unittest.mock import AsyncMock

import pytest

from app.ai.tools.retrieval.dense import (
    DenseRetrieverInput,
    DenseRetrieverTool,
)


@pytest.fixture
def mock_rag_service() -> AsyncMock:
    """Create mock RAGService instance."""
    return AsyncMock()


@pytest.fixture
def dense_tool(mock_rag_service) -> DenseRetrieverTool:
    """Create DenseRetrieverTool instance with mock service."""
    return DenseRetrieverTool(rag_service=mock_rag_service)


@pytest.fixture
def mock_chunks():
    """Mock chunk results from RAG service."""
    return [
        {
            "text": "This is the first chunk about machine learning.",
            "score": 0.8765432,
            "metadata": {
                "chunk_id": "chunk-001",
                "paper_id": "paper-123",
                "paper_title": "Advances in Machine Learning",
                "authors": ["Alice Smith", "Bob Jones"],
                "venue": "NeurIPS 2023",
                "year": 2023,
                "section_name": "Introduction",
                "section_index": 1,
                "chunk_index": 0,
            },
        },
        {
            "text": "This is the second chunk discussing neural networks.",
            "score": 0.7234567,
            "metadata": {
                "chunk_id": "chunk-002",
                "paper_id": "paper-123",
                "paper_title": "Advances in Machine Learning",
                "authors": ["Alice Smith", "Bob Jones"],
                "venue": "NeurIPS 2023",
                "year": 2023,
                "section_name": "Methods",
                "section_index": 2,
                "chunk_index": 0,
            },
        },
    ]


class TestDenseRetrieverInput:
    """Test DenseRetrieverInput validation."""

    def test_valid_input(self):
        """Test valid input with all parameters."""
        input_data = DenseRetrieverInput(
            query="machine learning algorithms",
            top_k=20,
            metadata_filter="year >= 2020",
        )
        assert input_data.query == "machine learning algorithms"
        assert input_data.top_k == 20
        assert input_data.metadata_filter == "year >= 2020"

    def test_minimal_input(self):
        """Test minimal valid input with only required field."""
        input_data = DenseRetrieverInput(query="test query")
        assert input_data.query == "test query"
        assert input_data.top_k == 10  # default value
        assert input_data.metadata_filter is None

    def test_default_values(self):
        """Test default values are applied correctly."""
        input_data = DenseRetrieverInput(query="test")
        assert input_data.top_k == 10
        assert input_data.metadata_filter is None

    def test_top_k_validation_minimum(self):
        """Test top_k must be at least 1."""
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            DenseRetrieverInput(query="test", top_k=0)

    def test_top_k_validation_maximum(self):
        """Test top_k must not exceed 50."""
        with pytest.raises(ValueError, match="less than or equal to 50"):
            DenseRetrieverInput(query="test", top_k=51)

    def test_top_k_boundary_values(self):
        """Test top_k accepts boundary values 1 and 50."""
        input_min = DenseRetrieverInput(query="test", top_k=1)
        assert input_min.top_k == 1

        input_max = DenseRetrieverInput(query="test", top_k=50)
        assert input_max.top_k == 50


class TestDenseRetrieverTool:
    """Test DenseRetrieverTool functionality."""

    @pytest.mark.asyncio
    async def test_successful_retrieval(
        self, dense_tool, mock_rag_service, mock_chunks
    ):
        """Test successful dense retrieval with default parameters."""
        mock_rag_service.retrieve_chunks.return_value = mock_chunks

        result = await dense_tool.arun(query="machine learning")

        # Verify RAG service was called correctly
        mock_rag_service.retrieve_chunks.assert_called_once_with(
            query="machine learning",
            top_k=10,
            metadata_filter=None,
        )

        # Verify result structure
        assert result.type == "json"
        assert result.value["count"] == 2
        assert len(result.value["records"]) == 2

        # Verify first chunk formatting
        first_chunk = result.value["records"][0]
        assert first_chunk["text"] == "This is the first chunk about machine learning."
        assert first_chunk["score"] == 0.8765  # rounded to 4 decimals
        assert first_chunk["metadata"]["chunk_id"] == "chunk-001"
        assert first_chunk["metadata"]["paper_id"] == "paper-123"
        assert first_chunk["metadata"]["paper_title"] == "Advances in Machine Learning"
        assert first_chunk["metadata"]["authors"] == ["Alice Smith", "Bob Jones"]
        assert first_chunk["metadata"]["venue"] == "NeurIPS 2023"
        assert first_chunk["metadata"]["year"] == 2023
        assert first_chunk["metadata"]["section_name"] == "Introduction"
        assert first_chunk["metadata"]["section_index"] == 1
        assert first_chunk["metadata"]["chunk_index"] == 0

    @pytest.mark.asyncio
    async def test_score_rounding(self, dense_tool, mock_rag_service):
        """Test that scores are rounded to 4 decimal places."""
        chunks_with_precise_scores = [
            {
                "text": "Test content",
                "score": 0.123456789,
                "metadata": {
                    "chunk_id": "chunk-1",
                    "paper_id": "paper-1",
                    "paper_title": "Test",
                    "authors": [],
                    "venue": "",
                    "year": 2023,
                    "section_name": "",
                    "section_index": 0,
                    "chunk_index": 0,
                },
            }
        ]
        mock_rag_service.retrieve_chunks.return_value = chunks_with_precise_scores

        result = await dense_tool.arun(query="test")

        assert result.type == "json"
        assert result.value["records"][0]["score"] == 0.1235

    @pytest.mark.asyncio
    async def test_custom_top_k(self, dense_tool, mock_rag_service, mock_chunks):
        """Test retrieval with custom top_k parameter."""
        mock_rag_service.retrieve_chunks.return_value = mock_chunks

        result = await dense_tool.arun(query="neural networks", top_k=5)

        mock_rag_service.retrieve_chunks.assert_called_once_with(
            query="neural networks",
            top_k=5,
            metadata_filter=None,
        )
        assert result.type == "json"

    @pytest.mark.asyncio
    async def test_collection_names_filter(
        self, dense_tool, mock_rag_service, mock_chunks
    ):
        """Test retrieval with collection names filter."""
        mock_rag_service.retrieve_chunks.return_value = mock_chunks

        result = await dense_tool.arun(
            query="deep learning",
        )

        mock_rag_service.retrieve_chunks.assert_called_once_with(
            query="deep learning",
            top_k=10,
            metadata_filter=None,
        )
        assert result.type == "json"
        assert result.value["count"] == 2

    @pytest.mark.asyncio
    async def test_metadata_filter(self, dense_tool, mock_rag_service, mock_chunks):
        """Test retrieval with metadata filter."""
        mock_rag_service.retrieve_chunks.return_value = mock_chunks

        result = await dense_tool.arun(
            query="transformers",
            metadata_filter='year >= 2020 AND venue == "NeurIPS"',
        )

        mock_rag_service.retrieve_chunks.assert_called_once_with(
            query="transformers",
            top_k=10,
            metadata_filter='year >= 2020 AND venue == "NeurIPS"',
        )
        assert result.type == "json"

    @pytest.mark.asyncio
    async def test_combined_filters(self, dense_tool, mock_rag_service, mock_chunks):
        """Test retrieval with both collection names and metadata filter."""
        mock_rag_service.retrieve_chunks.return_value = mock_chunks

        result = await dense_tool.arun(
            query="attention mechanisms",
            top_k=15,
            metadata_filter="year == 2023",
        )

        mock_rag_service.retrieve_chunks.assert_called_once_with(
            query="attention mechanisms",
            top_k=15,
            metadata_filter="year == 2023",
        )
        assert result.type == "json"

    @pytest.mark.asyncio
    async def test_empty_results(self, dense_tool, mock_rag_service):
        """Test handling of no results returned."""
        mock_rag_service.retrieve_chunks.return_value = []

        result = await dense_tool.arun(query="nonexistent topic")

        assert result.type == "json"
        assert result.value["count"] == 0
        assert len(result.value["records"]) == 0

    @pytest.mark.asyncio
    async def test_missing_metadata_fields(self, dense_tool, mock_rag_service):
        """Test handling of chunks with missing metadata fields."""
        chunks_with_missing_metadata = [
            {
                "text": "Content without full metadata",
                "score": 0.75,
                "metadata": {
                    "chunk_id": "chunk-1",
                    "paper_id": "paper-1",
                    # Missing other fields
                },
            }
        ]
        mock_rag_service.retrieve_chunks.return_value = chunks_with_missing_metadata

        result = await dense_tool.arun(query="test")

        assert result.type == "json"
        chunk = result.value["records"][0]
        # Verify default values are used for missing fields
        assert chunk["metadata"]["paper_title"] == ""
        assert chunk["metadata"]["authors"] == []
        assert chunk["metadata"]["venue"] == ""
        assert chunk["metadata"]["year"] is None
        assert chunk["metadata"]["section_name"] == ""
        assert chunk["metadata"]["section_index"] == 0
        assert chunk["metadata"]["chunk_index"] == 0

    @pytest.mark.asyncio
    async def test_error_handling(self, dense_tool, mock_rag_service):
        """Test error handling when RAG service fails."""
        mock_rag_service.retrieve_chunks.side_effect = Exception("Vector search failed")

        result = await dense_tool.arun(query="test query")

        assert result.type == "error-json"
        assert result.value["query"] == "test query"
        assert "error" in result.value
        assert "message" in result.value

    @pytest.mark.asyncio
    async def test_error_with_parameters(self, dense_tool, mock_rag_service):
        """Test error handling preserves query context."""
        mock_rag_service.retrieve_chunks.side_effect = RuntimeError("Database timeout")

        result = await dense_tool.arun(
            query="complex query",
            top_k=20,
        )

        assert result.type == "error-json"
        assert result.value["query"] == "complex query"

    @pytest.mark.asyncio
    async def test_large_result_set(self, dense_tool, mock_rag_service):
        """Test handling of large result sets at boundary."""
        # Create 50 chunks (max top_k)
        large_chunk_set = [
            {
                "text": f"Chunk {i} content",
                "score": 0.9 - (i * 0.01),
                "metadata": {
                    "chunk_id": f"chunk-{i}",
                    "paper_id": f"paper-{i}",
                    "paper_title": f"Paper {i}",
                    "authors": [f"Author {i}"],
                    "venue": "Test Venue",
                    "year": 2023,
                    "section_name": "Section",
                    "section_index": i,
                    "chunk_index": 0,
                },
            }
            for i in range(50)
        ]
        mock_rag_service.retrieve_chunks.return_value = large_chunk_set

        result = await dense_tool.arun(query="test", top_k=50)

        assert result.type == "json"
        assert result.value["count"] == 50
        assert len(result.value["records"]) == 50
