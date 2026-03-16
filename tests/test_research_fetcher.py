"""Unit tests for research fetcher module (aggregation and deduplication)."""

import pytest
from unittest.mock import patch, MagicMock

from src.research_fetcher import (
    fetch_ai_research,
    _deduplicate_papers,
    _title_similarity,
)


class TestTitleSimilarity:
    """Tests for title similarity calculation."""

    def test_identical_titles(self):
        """Test that identical titles have similarity of 1.0."""
        title = "GPT-4o mini now available in the API"
        assert _title_similarity(title, title) == 1.0

    def test_similar_titles(self):
        """Test that similar titles have high similarity."""
        title1 = "GPT-4o mini now available in the API"
        title2 = "GPT-4o mini now available in the API: A Developer Guide"
        similarity = _title_similarity(title1, title2)
        assert similarity > 0.7

    def test_different_titles(self):
        """Test that different titles have low similarity."""
        title1 = "GPT-4o mini now available in the API"
        title2 = "Claude 3.5 Sonnet launches with tool use"
        similarity = _title_similarity(title1, title2)
        assert similarity < 0.5

    def test_case_insensitive(self):
        """Test that similarity is case insensitive."""
        title1 = "New Model Release"
        title2 = "new model release"
        assert _title_similarity(title1, title2) == 1.0

    def test_whitespace_handling(self):
        """Test that whitespace is normalized."""
        title1 = "New API Launch  "
        title2 = "  New API Launch"
        assert _title_similarity(title1, title2) == 1.0


class TestDeduplication:
    """Tests for item deduplication."""

    def test_empty_list(self):
        """Test deduplication of empty list."""
        assert _deduplicate_papers([]) == []

    def test_no_duplicates(self, sample_papers):
        """Test that unique items are all kept."""
        result = _deduplicate_papers(sample_papers)
        assert len(result) == len(sample_papers)

    def test_removes_exact_duplicates(self, sample_paper):
        """Test that exact duplicates are removed."""
        papers = [sample_paper, sample_paper.copy()]
        result = _deduplicate_papers(papers)
        assert len(result) == 1

    def test_removes_similar_titles(self):
        """Test that items with similar titles are deduplicated."""
        papers = [
            {"title": "GPT-4o mini now available in the API", "source": "OpenAI"},
            {"title": "GPT-4o mini now available in the API: Guide", "source": "OpenAI"},
        ]
        result = _deduplicate_papers(papers, threshold=0.85)
        assert len(result) == 1

    def test_keeps_different_items(self):
        """Test that items with different titles are kept."""
        papers = [
            {"title": "GPT-4o mini API Launch", "source": "OpenAI"},
            {"title": "Claude 3.5 Sonnet Release", "source": "Anthropic"},
        ]
        result = _deduplicate_papers(papers)
        assert len(result) == 2

    def test_respects_threshold(self):
        """Test that similarity threshold is respected."""
        papers = [
            {"title": "API Update", "source": "OpenAI"},
            {"title": "API Updates", "source": "Anthropic"},
        ]
        # With high threshold, should keep both
        result_high = _deduplicate_papers(papers, threshold=0.99)
        assert len(result_high) == 2

        # With low threshold, should deduplicate
        result_low = _deduplicate_papers(papers, threshold=0.7)
        assert len(result_low) == 1


class TestFetchAIResearch:
    """Tests for the main fetch_ai_research function."""

    def test_fetch_ai_research_aggregates_sources(self):
        """Test that updates are aggregated from blog sources."""
        with patch("src.research_fetcher.fetch_blog_posts") as mock_blogs:
            mock_blogs.return_value = [
                {"title": "OpenAI Update", "published_at": "2024-07-18"},
                {"title": "Anthropic Update", "published_at": "2024-07-17"},
            ]

            result = fetch_ai_research(max_results=10)

            assert len(result) == 2
            assert result[0]["title"] == "OpenAI Update"

    def test_fetch_ai_research_handles_source_failure(self):
        """Test that empty result is returned if source fails."""
        with patch("src.research_fetcher.fetch_blog_posts") as mock_blogs:
            mock_blogs.side_effect = Exception("API Error")

            result = fetch_ai_research(max_results=10)

            assert len(result) == 0

    def test_fetch_ai_research_deduplicates(self):
        """Test that duplicate items are removed."""
        with patch("src.research_fetcher.fetch_blog_posts") as mock_blogs:
            mock_blogs.return_value = [
                {"title": "GPT-4o mini API Launch", "published_at": "2024-07-18", "source": "OpenAI"},
                {"title": "GPT-4o mini API Launch", "published_at": "2024-07-18", "source": "OpenAI"},
            ]

            result = fetch_ai_research(max_results=10)

            assert len(result) == 1

    def test_fetch_ai_research_respects_max_results(self):
        """Test that max_results limit is respected."""
        with patch("src.research_fetcher.fetch_blog_posts") as mock_blogs:
            distinct_titles = [
                "OpenAI GPT-4o Release",
                "Anthropic Claude 3.5",
                "Google Gemini 1.5 Pro",
                "Meta LLaMA 3 Launch",
                "OpenAI Whisper v3",
                "Anthropic MCP Protocol",
                "Google AI Studio Update",
                "Meta PyTorch 2.0",
                "OpenAI Sora Preview",
                "Anthropic Artifacts Launch",
            ]
            papers = [{"title": distinct_titles[i], "published_at": f"2024-07-{18-i:02d}"} for i in range(10)]
            mock_blogs.return_value = papers

            result = fetch_ai_research(max_results=3)

            assert len(result) == 3

    def test_fetch_ai_research_sorts_by_date(self):
        """Test that results are sorted by date (most recent first)."""
        with patch("src.research_fetcher.fetch_blog_posts") as mock_blogs:
            mock_blogs.return_value = [
                {"title": "Old Update", "published_at": "2024-01-01"},
                {"title": "New Update", "published_at": "2024-07-18"},
            ]

            result = fetch_ai_research(max_results=10)

            assert result[0]["title"] == "New Update"
            assert result[1]["title"] == "Old Update"
