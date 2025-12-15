"""Unit tests for MetadataRetrieverTool."""

from unittest.mock import patch

import pytest

from app.ai.tools.retrieval.metadata import (
    MetadataRetrieverInput,
    MetadataRetrieverTool,
)


@pytest.fixture
def metadata_tool() -> MetadataRetrieverTool:
    """Create MetadataRetrieverTool instance."""
    return MetadataRetrieverTool()


@pytest.fixture
def mock_query_results():
    """Mock Zilliz query results."""
    return [
        {
            "chunk_id": "chunk-1",
            "paper_id": "paper-123",
            "paper_title": "Test Paper 1",
            "authors": ["Author A", "Author B"],
            "venue": "TestConf 2023",
            "year": 2023,
            "section_name": "Introduction",
            "section_index": 1,
            "chunk_index": 0,
            "chunk_content": "This is test content for chunk 1.",
            "image_path": "",
        },
        {
            "chunk_id": "chunk-2",
            "paper_id": "paper-123",
            "paper_title": "Test Paper 1",
            "authors": ["Author A", "Author B"],
            "venue": "TestConf 2023",
            "year": 2023,
            "section_name": "Methods",
            "section_index": 2,
            "chunk_index": 0,
            "chunk_content": "This is test content for chunk 2.",
            "image_path": "",
        },
    ]


class TestMetadataRetrieverInput:
    """Test MetadataRetrieverInput validation."""

    def test_valid_input(self):
        """Test valid input with all parameters."""
        input_data = MetadataRetrieverInput(
            metadata_filter="year == 2023",
            limit=10,
            offset=0,
            output_fields=["paper_id", "paper_title"],
        )
        assert input_data.metadata_filter == "year == 2023"
        assert input_data.limit == 10
        assert input_data.offset == 0
        assert input_data.output_fields == ["paper_id", "paper_title"]

    def test_minimal_input(self):
        """Test minimal valid input with only required field."""
        input_data = MetadataRetrieverInput(metadata_filter='paper_id == "test"')
        assert input_data.metadata_filter == 'paper_id == "test"'
        assert input_data.limit == 10  # default
        assert input_data.offset == 0  # default
        assert input_data.output_fields is None  # default

    def test_default_values(self):
        """Test default values are applied correctly."""
        input_data = MetadataRetrieverInput(metadata_filter="year == 2023")
        assert input_data.limit == 10
        assert input_data.offset == 0
        assert input_data.output_fields is None

    def test_limit_validation_minimum(self):
        """Test limit must be at least 1."""
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            MetadataRetrieverInput(metadata_filter="year == 2023", limit=0)

    def test_limit_validation_maximum(self):
        """Test limit must not exceed 100."""
        with pytest.raises(ValueError, match="less than or equal to 100"):
            MetadataRetrieverInput(metadata_filter="year == 2023", limit=101)

    def test_limit_boundary_values(self):
        """Test limit accepts boundary values 1 and 100."""
        input_min = MetadataRetrieverInput(metadata_filter="test", limit=1)
        assert input_min.limit == 1

        input_max = MetadataRetrieverInput(metadata_filter="test", limit=100)
        assert input_max.limit == 100

    def test_offset_validation(self):
        """Test offset must be non-negative."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            MetadataRetrieverInput(metadata_filter="year == 2023", offset=-1)

    def test_offset_zero(self):
        """Test offset can be zero."""
        input_data = MetadataRetrieverInput(metadata_filter="test", offset=0)
        assert input_data.offset == 0

    def test_large_offset(self):
        """Test large offset values are allowed."""
        input_data = MetadataRetrieverInput(metadata_filter="test", offset=1000)
        assert input_data.offset == 1000

    def test_empty_output_fields_list(self):
        """Test empty output fields list is allowed."""
        input_data = MetadataRetrieverInput(metadata_filter="test", output_fields=[])
        assert input_data.output_fields == []


class TestMetadataRetrieverTool:
    """Test MetadataRetrieverTool functionality."""

    @pytest.mark.asyncio
    async def test_successful_retrieval(self, metadata_tool, mock_query_results):
        """Test successful metadata-based retrieval with default fields."""
        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.return_value = mock_query_results

            result = await metadata_tool.arun(
                metadata_filter="year == 2023",
                limit=10,
                offset=0,
            )

            # Verify zilliz_service.query was called correctly
            mock_zilliz.query.assert_called_once_with(
                filter="year == 2023",
                limit=10,
                offset=0,
                output_fields=[
                    "chunk_id",
                    "paper_id",
                    "paper_title",
                    "authors",
                    "venue",
                    "year",
                    "section_name",
                    "section_index",
                    "chunk_index",
                    "chunk_content",
                    "image_path",
                ],
            )

            # Verify result structure
            assert result.type == "json"
            assert result.value["count"] == 2
            assert len(result.value["records"]) == 2

            # Verify first chunk metadata
            first_chunk = result.value["records"][0]
            assert "metadata" in first_chunk
            metadata = first_chunk["metadata"]
            assert metadata["chunk_id"] == "chunk-1"
            assert metadata["paper_id"] == "paper-123"
            assert metadata["paper_title"] == "Test Paper 1"
            assert metadata["authors"] == ["Author A", "Author B"]
            assert metadata["venue"] == "TestConf 2023"
            assert metadata["year"] == 2023
            assert metadata["section_name"] == "Introduction"
            assert metadata["section_index"] == 1
            assert metadata["chunk_index"] == 0
            assert metadata["chunk_content"] == "This is test content for chunk 1."
            assert metadata["image_path"] == ""

    @pytest.mark.asyncio
    async def test_empty_results(self, metadata_tool):
        """Test handling of no results."""
        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.return_value = []

            result = await metadata_tool.arun(
                metadata_filter="year == 2099",
                limit=10,
            )

            assert result.type == "json"
            assert result.value["count"] == 0
            assert len(result.value["records"]) == 0

    @pytest.mark.asyncio
    async def test_custom_output_fields(self, metadata_tool):
        """Test custom output fields filter results correctly."""
        custom_results = [
            {
                "paper_id": "paper-123",
                "paper_title": "Test Paper",
                "year": 2023,
                "extra_field": "should not appear",
            }
        ]

        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.return_value = custom_results

            result = await metadata_tool.arun(
                metadata_filter="year == 2023",
                output_fields=["paper_id", "paper_title", "year"],
            )

            # Verify custom output fields were passed
            mock_zilliz.query.assert_called_once()
            call_args = mock_zilliz.query.call_args
            assert call_args[1]["output_fields"] == ["paper_id", "paper_title", "year"]

            # Verify result structure
            assert result.type == "json"
            assert result.value["count"] == 1

            # Verify only requested fields are in metadata
            metadata = result.value["records"][0]["metadata"]
            assert metadata["paper_id"] == "paper-123"
            assert metadata["paper_title"] == "Test Paper"
            assert metadata["year"] == 2023
            # extra_field should be filtered out
            assert "extra_field" not in metadata

    @pytest.mark.asyncio
    async def test_pagination_with_offset(self, metadata_tool, mock_query_results):
        """Test pagination with offset parameter."""
        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.return_value = [mock_query_results[1]]

            result = await metadata_tool.arun(
                metadata_filter='paper_id == "paper-123"',
                limit=1,
                offset=1,
            )

            # Verify pagination parameters
            mock_zilliz.query.assert_called_once()
            call_args = mock_zilliz.query.call_args
            assert call_args[1]["limit"] == 1
            assert call_args[1]["offset"] == 1

            # Verify result
            assert result.type == "json"
            assert result.value["count"] == 1
            assert result.value["records"][0]["metadata"]["chunk_id"] == "chunk-2"

    @pytest.mark.asyncio
    async def test_pagination_large_offset(self, metadata_tool):
        """Test pagination with large offset returns empty when beyond results."""
        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.return_value = []

            result = await metadata_tool.arun(
                metadata_filter="year == 2023",
                limit=10,
                offset=1000,
            )

            assert result.type == "json"
            assert result.value["count"] == 0

    @pytest.mark.asyncio
    async def test_error_handling(self, metadata_tool):
        """Test error handling when query fails."""
        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.side_effect = Exception("Database connection failed")

            result = await metadata_tool.arun(
                metadata_filter="invalid filter",
            )

            assert result.type == "error-json"
            assert "error" in result.value
            assert "Database connection failed" in result.value["error"]
            assert result.value["filter"] == "invalid filter"
            assert "message" in result.value
            assert "Failed to filter chunks" in result.value["message"]

    @pytest.mark.asyncio
    async def test_error_preserves_context(self, metadata_tool):
        """Test error response includes filter context."""
        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.side_effect = RuntimeError("Query timeout")

            result = await metadata_tool.arun(
                metadata_filter='year > 2020 AND venue == "ACL"',
                limit=50,
            )

            assert result.type == "error-json"
            assert "Query timeout" in result.value["error"]
            assert result.value["filter"] == 'year > 2020 AND venue == "ACL"'

    @pytest.mark.asyncio
    async def test_filter_with_special_characters(
        self, metadata_tool, mock_query_results
    ):
        """Test filter with special characters in values."""
        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.return_value = mock_query_results

            result = await metadata_tool.arun(
                metadata_filter='paper_title == "Test: A Study of AI & ML"',
            )

            assert result.type == "json"
            mock_zilliz.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_maximum_limit(self, metadata_tool):
        """Test using maximum limit of 100."""
        large_results = [
            {
                "chunk_id": f"chunk-{i}",
                "paper_id": f"paper-{i}",
                "chunk_content": f"Content {i}",
            }
            for i in range(100)
        ]

        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.return_value = large_results

            result = await metadata_tool.arun(
                metadata_filter="year == 2023",
                limit=100,
            )

            assert result.type == "json"
            assert result.value["count"] == 100
            mock_zilliz.query.assert_called_once()
            call_args = mock_zilliz.query.call_args
            assert call_args[1]["limit"] == 100

    @pytest.mark.asyncio
    async def test_partial_metadata_fields(self, metadata_tool):
        """Test handling of results with only some metadata fields present."""
        partial_results = [
            {
                "chunk_id": "chunk-1",
                "paper_id": "paper-1",
                "year": 2023,
                # Other fields missing
            }
        ]

        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.return_value = partial_results

            result = await metadata_tool.arun(
                metadata_filter="year == 2023",
                output_fields=["chunk_id", "paper_id", "year", "paper_title"],
            )

            assert result.type == "json"
            metadata = result.value["records"][0]["metadata"]
            # Present fields should be included
            assert metadata["chunk_id"] == "chunk-1"
            assert metadata["paper_id"] == "paper-1"
            assert metadata["year"] == 2023
            # Missing fields should not be in metadata
            assert "paper_title" not in metadata

    def test_tool_metadata(self, metadata_tool):
        """Test tool metadata attributes."""
        assert metadata_tool.name == "metadata_search"
        assert "metadata" in metadata_tool.description.lower()
        assert metadata_tool.input_schema == MetadataRetrieverInput

    def test_tool_description_content(self, metadata_tool):
        """Test that tool description includes important usage info."""
        description = metadata_tool.description
        # Should mention when to use
        assert "Use when:" in description or "use when" in description.lower()
        # Should mention when NOT to use
        assert "NOT use" in description or "not use" in description.lower()
        # Should mention no semantic search
        assert "semantic" in description.lower() or "vector" in description.lower()
        # Should mention supported fields
        assert "paper_id" in description.lower()
        # Should mention filter syntax
        assert "filter" in description.lower()

    @pytest.mark.asyncio
    async def test_deterministic_ordering(self, metadata_tool, mock_query_results):
        """Test that results maintain storage order (not relevance ranked)."""
        with patch("app.ai.tools.retrieval.metadata.zilliz_service") as mock_zilliz:
            mock_zilliz.query.return_value = mock_query_results

            result = await metadata_tool.arun(metadata_filter="year == 2023")

            assert result.type == "json"
            # Verify order is preserved from query results
            assert result.value["records"][0]["metadata"]["section_index"] == 1
            assert result.value["records"][1]["metadata"]["section_index"] == 2
