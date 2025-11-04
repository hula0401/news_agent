#!/usr/bin/env python3
"""
Unit tests for web research tools.

Tests browser_read, research_loop, and compose_voice_answer functions.
"""
import pytest
import asyncio
from agent_core.tools.web_research import (
    browser_read,
    research_loop,
    compose_voice_answer,
    _score_chunks,
    _build_research_summary,
)


# ====== Browser Read Tests ======

@pytest.mark.asyncio
async def test_browser_read_success():
    """Test successful browser read with real URL"""
    result = await browser_read("https://www.example.com", max_length=1000)

    assert result["success"] == True
    assert result["title"] is not None
    assert result["content"] is not None
    assert len(result["content"]) > 0
    assert result["url"] == "https://www.example.com"
    assert result["error"] is None
    assert result["duration_ms"] > 0


@pytest.mark.asyncio
async def test_browser_read_with_timeout():
    """Test browser read respects timeout"""
    start = asyncio.get_event_loop().time()

    result = await browser_read(
        "https://httpbin.org/delay/30",  # Deliberately slow endpoint
        timeout=2000  # 2 second timeout
    )

    duration = asyncio.get_event_loop().time() - start

    # Should fail due to timeout
    assert result["success"] == False
    assert result["error"] is not None
    assert duration < 5  # Should timeout quickly, not wait 30s


@pytest.mark.asyncio
async def test_browser_read_invalid_url():
    """Test browser read with invalid URL"""
    result = await browser_read("https://this-domain-does-not-exist-12345.com")

    assert result["success"] == False
    assert result["error"] is not None
    assert result["title"] is None
    assert result["content"] is None


@pytest.mark.asyncio
async def test_browser_read_max_length():
    """Test content truncation at max_length"""
    result = await browser_read("https://www.example.com", max_length=100)

    assert result["success"] == True
    if result["content"]:
        assert len(result["content"]) <= 103  # 100 + "..."


# ====== Research Loop Tests ======

@pytest.mark.asyncio
async def test_research_loop_single_hop():
    """Test research loop with single hop"""
    news_items = [
        {
            "title": "Example Article",
            "url": "https://www.example.com",
            "source_website": "example.com",
        }
    ]

    result = await research_loop(
        news_items=news_items,
        query="test query",
        max_hops=1,
        max_urls=1,
    )

    assert "content_chunks" in result
    assert "citations" in result
    assert "confidence" in result
    assert "summary" in result
    assert "num_chunks" in result
    assert "num_sources" in result

    assert isinstance(result["confidence"], float)
    assert 0 <= result["confidence"] <= 1
    assert result["num_chunks"] >= 0
    assert result["num_sources"] >= 0


@pytest.mark.asyncio
async def test_research_loop_empty_news():
    """Test research loop with empty news list"""
    result = await research_loop(
        news_items=[],
        query="test",
        max_hops=2,
        max_urls=3,
    )

    assert result["num_chunks"] == 0
    assert result["num_sources"] == 0
    assert result["confidence"] == 0


@pytest.mark.asyncio
async def test_research_loop_scoring():
    """Test that research loop scores chunks correctly"""
    news_items = [
        {
            "title": "Test Article",
            "url": "https://www.example.com",
            "source_website": "example.com",
        }
    ]

    result = await research_loop(
        news_items=news_items,
        query="example test",  # Terms in the URL
        max_hops=1,
        max_urls=1,
    )

    # Chunks should be scored
    if result["content_chunks"]:
        for chunk in result["content_chunks"]:
            assert "score" in chunk
            assert isinstance(chunk["score"], float)
            assert 0 <= chunk["score"] <= 1


# ====== Chunk Scoring Tests ======

def test_score_chunks_relevance():
    """Test chunk scoring based on query relevance"""
    chunks = [
        {
            "content": "This article discusses Google stock performance and earnings.",
            "title": "Google Stock Analysis",
            "url": "https://example.com/1",
            "source": "example.com",
        },
        {
            "content": "Random unrelated content about weather.",
            "title": "Weather Report",
            "url": "https://example.com/2",
            "source": "example.com",
        },
    ]

    scored = _score_chunks(chunks, query="Google stock")

    # First chunk should score higher (more relevant)
    assert scored[0]["score"] > scored[1]["score"]
    assert scored[0]["content"].startswith("This article discusses Google")


def test_score_chunks_length_bonus():
    """Test that longer content gets bonus points"""
    chunks = [
        {
            "content": "Short content.",
            "title": "Test",
            "url": "https://example.com/1",
            "source": "example.com",
        },
        {
            "content": "Much longer content " * 100,  # >1000 chars
            "title": "Test",
            "url": "https://example.com/2",
            "source": "example.com",
        },
    ]

    scored = _score_chunks(chunks, query="test")

    # Longer content should get length bonus
    # (assuming other factors equal, longer content ranks higher)
    assert scored[0]["score"] != scored[1]["score"]


def test_score_chunks_title_bonus():
    """Test that title matches get bonus points"""
    chunks = [
        {
            "content": "Generic content.",
            "title": "Important Google News",
            "url": "https://example.com/1",
            "source": "example.com",
        },
        {
            "content": "Google content here.",
            "title": "Generic Title",
            "url": "https://example.com/2",
            "source": "example.com",
        },
    ]

    scored = _score_chunks(chunks, query="Google news")

    # First chunk should score higher due to title match
    assert scored[0]["score"] > scored[1]["score"]


# ====== Research Summary Tests ======

def test_build_research_summary():
    """Test research summary building"""
    chunks = [
        {
            "content": "First sentence. Second sentence. Third sentence.",
            "title": "Article 1",
            "url": "https://example.com/1",
            "source": "example.com",
            "score": 0.9,
        },
        {
            "content": "Another article content. More details here.",
            "title": "Article 2",
            "url": "https://example.com/2",
            "source": "news.com",
            "score": 0.7,
        },
    ]

    summary = _build_research_summary(chunks, query="test")

    assert len(summary) > 0
    assert "example.com" in summary  # Should cite sources
    assert "First sentence" in summary  # Should include content


def test_build_research_summary_empty():
    """Test summary with no chunks"""
    summary = _build_research_summary([], query="test")

    assert summary == "No detailed content available."


# ====== Voice Answer Composer Tests ======

def test_compose_voice_answer_basic():
    """Test voice answer composition"""
    chunks = [
        {
            "content": "Google stock reached a new high today at $300 per share. Analysts are optimistic.",
            "url": "https://example.com",
            "score": 0.8,
        }
    ]

    result = compose_voice_answer(
        content_chunks=chunks,
        query="Google stock",
        confidence=0.8,
        max_words=25,
    )

    assert "answer" in result
    assert "hedge" in result
    assert "citations" in result

    # Answer should be concise
    word_count = len(result["answer"].split())
    assert word_count <= 30  # Roughly 25 words +/- some margin

    # Should include citation
    assert len(result["citations"]) > 0
    assert "https://example.com" in result["citations"]


def test_compose_voice_answer_with_hedge():
    """Test voice answer includes hedge when confidence low"""
    chunks = [
        {
            "content": "Some information about stocks.",
            "url": "https://example.com",
            "score": 0.3,
        }
    ]

    result = compose_voice_answer(
        content_chunks=chunks,
        query="test",
        confidence=0.4,  # Low confidence
        max_words=25,
    )

    # Should include hedge for low confidence
    assert result["hedge"] is not None
    assert "limited" in result["hedge"].lower() or "based on" in result["hedge"].lower()


def test_compose_voice_answer_high_confidence():
    """Test voice answer without hedge when confidence high"""
    chunks = [
        {
            "content": "Detailed information about the topic.",
            "url": "https://example.com",
            "score": 0.9,
        }
    ]

    result = compose_voice_answer(
        content_chunks=chunks,
        query="test",
        confidence=0.8,  # High confidence
        max_words=25,
    )

    # Should NOT include hedge for high confidence
    assert result["hedge"] is None


def test_compose_voice_answer_empty_chunks():
    """Test voice answer with no chunks"""
    result = compose_voice_answer(
        content_chunks=[],
        query="test",
        confidence=0.0,
        max_words=25,
    )

    assert result["answer"] == "I couldn't find detailed information about that."
    assert result["hedge"] is None
    assert result["citations"] == []


# ====== Performance Tests ======

@pytest.mark.asyncio
@pytest.mark.slow
async def test_browser_read_performance():
    """Test browser read completes in reasonable time"""
    start = asyncio.get_event_loop().time()

    result = await browser_read("https://www.example.com")

    duration = asyncio.get_event_loop().time() - start

    # Should complete within 10 seconds
    assert duration < 10
    assert result["duration_ms"] < 10000


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
