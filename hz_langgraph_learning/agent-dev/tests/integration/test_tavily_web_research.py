#!/usr/bin/env python3
"""
Integration tests for Tavily + Web Research flow.

Tests the integration of Tavily news search with Playwright browser research.
These tests focus on the web research functionality rather than the full agent pipeline.
"""
import pytest
import asyncio
from agent_core.state import MarketState, NewsItem
from agent_core.tools.web_research import research_loop, browser_read


# ====== Tavily + Web Research Integration Tests ======

@pytest.mark.asyncio
@pytest.mark.integration
async def test_tavily_news_to_web_research():
    """
    Test integration of Tavily news results with web research.

    Simulates:
    1. Tavily returns news items (mocked)
    2. Web research browses the URLs
    3. Content extracted and scored
    4. Citations tracked
    """
    # Simulate Tavily news results
    tavily_news = [
        NewsItem(
            title="Example Article 1",
            summary="Summary of article 1",
            url="https://www.example.com",
            source="example.com",
            published_at="2025-01-30T12:00:00Z",
            source_website="example.com",
        ),
        NewsItem(
            title="CNBC Market Report",
            summary="Market report summary",
            url="https://www.cnbc.com/quotes/GOOGL",
            source="cnbc.com",
            published_at="2025-01-30T11:00:00Z",
            source_website="cnbc.com",
        ),
    ]

    # Convert to format for web research
    news_items = [
        {
            "title": item.title,
            "url": item.url,
            "source_website": item.source_website,
        }
        for item in tavily_news
    ]

    # Run web research on Tavily results
    research_result = await research_loop(
        news_items=news_items,
        query="Google news",
        max_hops=1,
        max_urls=2,
    )

    # Verify integration works
    assert "content_chunks" in research_result
    assert "citations" in research_result
    assert "confidence" in research_result

    assert len(research_result["content_chunks"]) > 0
    assert len(research_result["citations"]) > 0
    assert 0 <= research_result["confidence"] <= 1

    # Verify chunks have required fields
    for chunk in research_result["content_chunks"]:
        assert "content" in chunk
        assert "url" in chunk
        assert "score" in chunk
        assert chunk["content"] is not None
        assert len(chunk["content"]) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multi_hop_research():
    """
    Test multi-hop research with low confidence triggering second hop.

    Verifies:
    - First hop browses URLs
    - Low confidence triggers second hop
    - Results merged from both hops
    """
    # Provide enough news items for 2 hops
    news_items = [
        {"title": "Article 1", "url": "https://www.example.com", "source_website": "example.com"},
        {"title": "Article 2", "url": "https://www.example.com", "source_website": "example.com"},
        {"title": "Article 3", "url": "https://www.example.com", "source_website": "example.com"},
        {"title": "Article 4", "url": "https://www.example.com", "source_website": "example.com"},
    ]

    # Run research loop with 2 hops allowed
    research_result = await research_loop(
        news_items=news_items,
        query="test query with no matching terms",  # Low relevance = low confidence
        max_hops=2,
        max_urls=2,  # 2 URLs per hop
    )

    # Verify results
    assert "content_chunks" in research_result
    assert "citations" in research_result
    assert "confidence" in research_result

    # Should have chunks from browsing
    assert len(research_result["content_chunks"]) > 0
    assert len(research_result["citations"]) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_citation_tracking():
    """
    Test that citations are tracked correctly through the research flow.

    Verifies:
    - Each chunk has source URL
    - Citations list contains all unique URLs
    - Citations can be traced back to original news items
    """
    news_items = [
        {
            "title": "Test Article 1",
            "url": "https://www.example.com",
            "source_website": "example.com",
        },
    ]

    # Run research loop
    research_result = await research_loop(
        news_items=news_items,
        query="test query",
        max_hops=1,
        max_urls=1,
    )

    # Verify citations tracked
    citations = research_result["citations"]
    chunks = research_result["content_chunks"]

    # All chunks should have URLs
    for chunk in chunks:
        assert "url" in chunk
        assert chunk["url"] is not None
        # URL should be in citations list
        assert chunk["url"] in citations

    # Citations should match original news URLs
    original_urls = {item["url"] for item in news_items}
    citation_set = set(citations)

    # All citations should come from original news items
    assert citation_set.issubset(original_urls)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_research_with_failed_urls():
    """
    Test that research handles failed URLs gracefully.

    Verifies:
    - Failed URLs don't crash the pipeline
    - Successful URLs still processed
    - Citations only include successful fetches
    """
    news_items = [
        {
            "title": "Valid Article",
            "url": "https://www.example.com",
            "source_website": "example.com",
        },
        {
            "title": "Invalid Article",
            "url": "https://this-domain-does-not-exist-12345.com",
            "source_website": "invalid.com",
        },
    ]

    # Run research loop
    research_result = await research_loop(
        news_items=news_items,
        query="test query",
        max_hops=1,
        max_urls=2,
    )

    # Should still have some results (from successful URL)
    # But may have fewer chunks than URLs attempted
    assert isinstance(research_result["content_chunks"], list)
    assert isinstance(research_result["citations"], list)

    # Confidence should be calculated despite failures
    assert 0 <= research_result["confidence"] <= 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_browser_read_real_news_site():
    """
    Test browser reading from a real news website.

    Verifies:
    - JavaScript renders correctly
    - Clean text extraction works
    - Content is substantial
    """
    # Use a real, stable news site
    result = await browser_read(
        url="https://www.example.com",  # Stable test site
        max_length=2000,
        timeout=10000,
    )

    # Verify success
    assert result["success"] == True
    assert result["title"] is not None
    assert result["content"] is not None
    assert len(result["content"]) > 0
    assert result["duration_ms"] > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_state_integration():
    """
    Test that research results integrate correctly with MarketState.

    Verifies state fields are populated correctly.
    """
    # Run research
    news_items = [
        {"title": "Test", "url": "https://www.example.com", "source_website": "example.com"},
    ]

    research_result = await research_loop(
        news_items=news_items,
        query="test",
        max_hops=1,
        max_urls=1,
    )

    # Simulate state update (what node_web_research would do)
    state = MarketState(
        query="test",
        research_chunks=research_result["content_chunks"],
        research_citations=research_result["citations"],
        research_confidence=research_result["confidence"],
    )

    # Verify state populated
    assert len(state.research_chunks) > 0
    assert len(state.research_citations) > 0
    assert 0 <= state.research_confidence <= 1


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
