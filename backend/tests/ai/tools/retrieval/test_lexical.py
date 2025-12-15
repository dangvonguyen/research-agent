"""Unit tests for LexicalRetrieverTool with BM25."""

from unittest.mock import patch

import pytest

from app.ai.tools.retrieval.lexical import LexicalRetrievalInput, LexicalRetrieverTool


@pytest.fixture
def lexical_tool():
    """Create LexicalRetrieverTool instance."""
    return LexicalRetrieverTool()


@pytest.fixture
def mock_bm25_results():
    """Mock Zilliz BM25 search results."""
    return [
        {
            "id": "chunk-1",
            "distance": 8.4,
            "entity": {
                "chunk_id": "chunk-1",
                "paper_id": "paper-123",
                "paper_title": "ResNet: Deep Residual Learning",
                "authors": ["He et al."],
                "venue": "CVPR 2016",
                "year": 2016,
                "section_name": "Introduction",
                "section_index": 1,
                "chunk_index": 0,
                "chunk_content": "We propose ResNet, a deep residual neural network architecture for image classification.",
                "image_path": "",
            },
        },
        {
            "id": "chunk-2",
            "distance": 5.6,
            "entity": {
                "chunk_id": "chunk-2",
                "paper_id": "paper-456",
                "paper_title": "Training Deep Networks",
                "authors": ["Smith et al."],
                "venue": "ICML 2017",
                "year": 2017,
                "section_name": "Methods",
                "section_index": 2,
                "chunk_index": 0,
                "chunk_content": "ResNet and other residual networks have revolutionized deep learning.",
                "image_path": "",
            },
        },
        {
            "id": "chunk-3",
            "distance": 3.1,
            "entity": {
                "chunk_id": "chunk-3",
                "paper_id": "paper-789",
                "paper_title": "Image Classification Survey",
                "authors": ["Johnson et al."],
                "venue": "CVPR 2018",
                "year": 2018,
                "section_name": "Related Work",
                "section_index": 1,
                "chunk_index": 5,
                "chunk_content": "Various architectures including ResNet have been proposed for classification tasks.",
                "image_path": "",
            },
        },
    ]


class TestLexicalRetrievalInput:
    """Test LexicalRetrievalInput validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_data = LexicalRetrievalInput(
            query="ResNet",
            top_k=10,
        )
        assert input_data.query == "ResNet"
        assert input_data.top_k == 10

    def test_default_values(self):
        """Test default values."""
        input_data = LexicalRetrievalInput(query="BERT")
        assert input_data.top_k == 10
        assert input_data.metadata_filter is None

    def test_top_k_validation(self):
        """Test top_k must be between 1 and 50."""
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            LexicalRetrievalInput(query="test", top_k=0)

        with pytest.raises(ValueError, match="less than or equal to 50"):
            LexicalRetrievalInput(query="test", top_k=51)


class TestLexicalRetrieverTool:
    """Test LexicalRetrieverTool with BM25."""

    @pytest.mark.asyncio
    async def test_successful_bm25_search(self, lexical_tool, mock_bm25_results):
        """Test successful BM25 search."""
        with patch("app.ai.tools.retrieval.lexical.zilliz_service") as mock_zilliz:
            mock_zilliz.bm25_search.return_value = mock_bm25_results

            result = await lexical_tool.arun(
                query="ResNet architecture",
                top_k=5,
            )

            assert result.type == "json"
            assert result.value["count"] == 3
            assert len(result.value["records"]) == 3

            # Verify BM25 search was called with correct parameters
            mock_zilliz.bm25_search.assert_called_once()
            call_kwargs = mock_zilliz.bm25_search.call_args.kwargs
            assert call_kwargs["query_text"] == "ResNet architecture"
            assert call_kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_bm25_score_calculation(self, lexical_tool, mock_bm25_results):
        """Test BM25 scores."""
        with patch("app.ai.tools.retrieval.lexical.zilliz_service") as mock_zilliz:
            mock_zilliz.bm25_search.return_value = mock_bm25_results

            result = await lexical_tool.arun(
                query="ResNet",
                top_k=10,
            )

            assert result.type == "json"
            for chunk in result.value["records"]:
                assert chunk["score"] >= 0.0

            # Better matches should have higher scores (lower distance = higher score)
            scores = [chunk["score"] for chunk in result.value["records"]]
            assert scores[0] > scores[1]
            assert scores[1] > scores[2]

    @pytest.mark.asyncio
    async def test_metadata_filter(self, lexical_tool, mock_bm25_results):
        """Test filtering with metadata filter expression."""
        with patch("app.ai.tools.retrieval.lexical.zilliz_service") as mock_zilliz:
            mock_zilliz.bm25_search.return_value = mock_bm25_results

            await lexical_tool.arun(
                query="ResNet",
                metadata_filter='year > 2015 AND venue == "CVPR 2016"',
            )

            # Verify the filter was applied
            call_kwargs = mock_zilliz.bm25_search.call_args.kwargs
            filter_expr = call_kwargs.get("filter_expr")
            assert filter_expr is not None
            assert 'year > 2015 AND venue == "CVPR 2016"' in filter_expr

    @pytest.mark.asyncio
    async def test_no_results(self, lexical_tool):
        """Test when no chunks match the query."""
        with patch("app.ai.tools.retrieval.lexical.zilliz_service") as mock_zilliz:
            mock_zilliz.bm25_search.return_value = []

            result = await lexical_tool.arun(
                query="NonExistentTerm",
                top_k=5,
            )

            assert result.type == "json"
            assert result.value["count"] == 0
            assert len(result.value["records"]) == 0

    @pytest.mark.asyncio
    async def test_multi_term_query(self, lexical_tool, mock_bm25_results):
        """Test BM25 with multi-term query."""
        with patch("app.ai.tools.retrieval.lexical.zilliz_service") as mock_zilliz:
            mock_zilliz.bm25_search.return_value = mock_bm25_results

            result = await lexical_tool.arun(
                query="ResNet neural network architecture",
                top_k=10,
            )

            assert result.type == "json"
            assert result.value["count"] == 3

            # Verify query was passed as-is (BM25 handles tokenization)
            call_kwargs = mock_zilliz.bm25_search.call_args.kwargs
            assert call_kwargs["query_text"] == "ResNet neural network architecture"

    @pytest.mark.asyncio
    async def test_error_handling(self, lexical_tool):
        """Test error handling when BM25 search fails."""
        with patch("app.ai.tools.retrieval.lexical.zilliz_service") as mock_zilliz:
            mock_zilliz.bm25_search.side_effect = Exception("BM25 search error")

            result = await lexical_tool.arun(query="test")

            assert result.type == "error-json"
            assert "error_code" in result.value

    @pytest.mark.asyncio
    async def test_top_k_limit(self, lexical_tool):
        """Test that results are limited to top_k."""
        # Create many results
        many_results = []
        for i in range(20):
            many_results.append(
                {
                    "id": f"chunk-{i}",
                    "distance": 0.5 + (i * 0.1),
                    "entity": {
                        "chunk_id": f"chunk-{i}",
                        "paper_id": f"paper-{i}",
                        "paper_title": f"Paper about ResNet {i}",
                        "authors": ["Author"],
                        "venue": "Conf",
                        "year": 2023,
                        "section_name": "Methods",
                        "section_index": 1,
                        "chunk_index": 0,
                        "chunk_content": f"Content discussing ResNet and its applications {i}",
                        "image_path": "",
                    },
                }
            )

        with patch("app.ai.tools.retrieval.lexical.zilliz_service") as mock_zilliz:
            mock_zilliz.bm25_search.return_value = many_results[
                :5
            ]  # BM25 already limits

            result = await lexical_tool.arun(
                query="ResNet",
                top_k=5,
            )

            assert result.type == "json"
            # Should return exactly 5 results (top_k limit)
            assert result.value["count"] == 5
