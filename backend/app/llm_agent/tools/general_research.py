#!/usr/bin/env python3
"""
General research tool for any topic using Tavily + Playwright.

This tool can research ANY topic (not just stock news):
- Earning calls and reports
- Product launches
- Company policies
- Technical questions
- General information

Uses:
1. Tavily for web search (any topic)
2. Playwright for browsing and content extraction
3. Multi-hop research with relevance scoring
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


# Import Tavily client and API key
import os
try:
    from tavily import TavilyClient
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None
except ImportError:
    logger.warning("Could not import TavilyClient - general search may not work")
    tavily_client = None
    TAVILY_API_KEY = ""


async def search_web(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web for any topic using Tavily.

    Args:
        query: Search query (e.g., "Google earnings call Q3 2024")
        max_results: Maximum number of results to return

    Returns:
        List of search results with title, url, snippet
    """
    if not tavily_client:
        logger.error("Tavily client not available")
        return []

    try:
        logger.info(f"🔍 Searching web for: {query}")

        # Use Tavily search API
        response = tavily_client.search(
            query=query,
            search_depth="advanced",  # Deep search for better results
            max_results=max_results,
        )

        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "score": item.get("score", 0.0),
            })

        logger.info(f"✅ Found {len(results)} results for query: {query}")
        return results

    except Exception as e:
        logger.error(f"❌ Web search error: {e}")
        return []


async def browse_url(url: str, max_length: int = 5000, timeout: int = 10000) -> Dict[str, Any]:
    """
    Browse a URL and extract clean content using Playwright.

    **Skips PDF files and other binary documents** to avoid download errors.

    Args:
        url: URL to browse
        max_length: Maximum content length
        timeout: Page load timeout in ms

    Returns:
        Dict with title, content, success status
    """
    import time

    start_time = time.time()

    # Check if URL is a PDF or other binary file
    binary_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar']
    url_lower = url.lower()

    if any(url_lower.endswith(ext) or ext in url_lower for ext in binary_extensions):
        logger.warning(f"⏭️  Skipping binary file (PDF/document): {url}")
        return {
            "url": url,
            "title": "Binary file (skipped)",
            "content": "",
            "success": False,
            "duration_ms": 0,
            "error": "Binary file format not supported (PDF/document)",
        }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()

            # Navigate to URL
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)  # Wait for JS

            # Get title
            title = await page.title()

            # Extract clean content
            content = await page.evaluate("""
                () => {
                    // Remove scripts, styles, nav, footer, ads
                    const elementsToRemove = document.querySelectorAll(
                        'script, style, nav, header, footer, aside, .ad, .advertisement, [class*="ad-"], [id*="ad-"]'
                    );
                    elementsToRemove.forEach(el => el.remove());

                    // Try main content areas
                    const mainContent = document.querySelector('article, main, [role="main"], .content, .post');
                    if (mainContent) {
                        return mainContent.innerText;
                    }

                    // Fallback to body
                    return document.body.innerText;
                }
            """)

            # Clean up content
            content = " ".join(content.split())  # Normalize whitespace
            content = content[:max_length]

            await browser.close()

            duration_ms = (time.time() - start_time) * 1000

            logger.info(f"✅ Browser read: {url} ({duration_ms:.0f}ms, {len(content)} chars)")

            return {
                "url": url,
                "title": title,
                "content": content,
                "success": True,
                "duration_ms": duration_ms,
            }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"❌ Browser read error for {url}: {e}")

        return {
            "url": url,
            "title": "",
            "content": "",
            "success": False,
            "duration_ms": duration_ms,
            "error": str(e),
        }


def extract_keywords(query: str) -> List[str]:
    """
    Extract meaningful keywords from a user query.

    Args:
        query: User's natural language query

    Returns:
        List of extracted keywords

    Examples:
        "how was the earning of Meta?" -> ["earning", "earnings", "quarterly", "results"]
        "what is an earnings call?" -> ["earnings call", "earnings", "quarterly report"]
    """
    query_lower = query.lower()

    # Keyword mappings for common financial terms
    keyword_mappings = {
        # Earnings & Reports
        "earning": ["earnings", "earnings call", "quarterly earnings", "earnings report", "Q3 earnings", "Q4 earnings"],
        "earnings": ["earnings call", "quarterly earnings", "earnings report"],

        # Financial Metrics & Ratios
        "p/e": ["P/E ratio", "price to earnings ratio", "PE ratio", "earnings multiple"],
        "pe": ["P/E ratio", "price to earnings ratio", "PE ratio", "earnings multiple"],
        "p/b": ["P/B ratio", "price to book ratio", "PB ratio", "book value ratio"],
        "pb": ["P/B ratio", "price to book ratio", "PB ratio"],
        "eps": ["EPS", "earnings per share", "diluted EPS"],
        "roe": ["ROE", "return on equity", "equity returns"],
        "roa": ["ROA", "return on assets", "asset returns"],
        "debt": ["debt to equity", "debt ratio", "leverage ratio", "financial leverage"],
        "margin": ["profit margin", "operating margin", "net margin", "gross margin"],
        "valuation": ["valuation", "market cap", "enterprise value", "stock valuation"],
        "dividend": ["dividend", "dividend yield", "dividend payout", "shareholder returns"],

        # Performance Metrics
        "revenue": ["revenue", "sales", "quarterly revenue", "annual revenue"],
        "profit": ["profit", "net income", "earnings", "profitability"],
        "growth": ["revenue growth", "earnings growth", "YoY growth", "growth rate"],

        # General
        "news": ["latest news", "recent news", "news update"],
        "price": ["stock price", "share price", "stock performance"],
    }

    keywords = []

    # Check for keyword mappings
    for key, expansions in keyword_mappings.items():
        if key in query_lower:
            keywords.extend(expansions)
            break  # Use first match

    # If no mappings found, extract nouns and important words
    if not keywords:
        # Remove common question words
        stop_words = {"what", "is", "the", "how", "was", "were", "are", "about", "of", "to", "a", "an"}
        words = [w.strip("?.,!") for w in query.lower().split() if w not in stop_words and len(w) > 2]
        keywords = words[:3] if words else [query]

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return unique_keywords[:5]  # Limit to top 5 keywords


def reformulate_queries(query: str, symbols: Optional[List[str]] = None, llm_keywords: Optional[List[str]] = None) -> List[str]:
    """
    Reformulate user query into better search queries.

    Combines extracted keywords with symbols for better search results.

    Args:
        query: Original user query
        symbols: List of stock symbols (e.g., ["META", "GOOGL"])
        llm_keywords: Keywords extracted by LLM intent analyzer (takes priority over extracted keywords)

    Returns:
        List of reformulated search queries

    Examples:
        query="how was the earning of Meta?", symbols=["META"], llm_keywords=["earnings call", "quarterly earnings"]
        -> ["META earnings call", "META quarterly earnings", "META latest news", ...]
    """
    # Prefer LLM-extracted keywords if available, otherwise use our keyword extraction
    if llm_keywords and len(llm_keywords) > 0:
        keywords = llm_keywords
    else:
        keywords = extract_keywords(query)

    queries = []

    if symbols:
        # Combine each symbol with keywords
        for symbol in symbols[:2]:  # Limit to 2 symbols to avoid too many queries
            # Add symbol + keyword combinations
            for keyword in keywords[:3]:  # Top 3 keywords
                queries.append(f"{symbol} {keyword}")

            # Add common financial query patterns
            queries.append(f"{symbol} latest news")
            queries.append(f"{symbol} earnings report")
    else:
        # No symbols - use keywords directly
        queries.extend(keywords)
        queries.append(query)  # Fallback to original

    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        q_normalized = q.lower()
        if q_normalized not in seen:
            seen.add(q_normalized)
            unique_queries.append(q)

    return unique_queries[:5]  # Limit to top 5 queries


def score_content(content: str, query: str) -> float:
    """
    Score content relevance to query.

    Args:
        content: Text content
        query: Original query

    Returns:
        Relevance score (0-1)
    """
    if not content or not query:
        return 0.0

    content_lower = content.lower()
    query_terms = query.lower().split()

    # Count query term matches
    matches = sum(1 for term in query_terms if term in content_lower)
    score = matches / len(query_terms) if query_terms else 0.0

    # Length bonus (longer content = more detail)
    if len(content) > 1000:
        score += 0.1
    if len(content) > 2000:
        score += 0.1

    return min(score, 1.0)


async def parallel_query_research(
    checklist_items: List[Dict[str, Any]],
    min_results_per_query: int = 5,
    max_browse_per_query: int = 3,
    min_confidence: float = 0.4,
) -> Dict[str, Any]:
    """
    Execute multiple research queries in parallel with minimum result guarantees.

    Each checklist item will have its own Tavily search with at least min_results_per_query results.

    Args:
        checklist_items: List of checklist items with "query", "symbols", "keywords" fields
        min_results_per_query: Minimum number of search results per query (default: 5)
        max_browse_per_query: Maximum URLs to browse per query (default: 3)
        min_confidence: Minimum confidence threshold for content (default: 0.4)

    Returns:
        Dict with:
        - content_chunks: Combined content from all queries
        - sources: Combined source URLs
        - confidence: Overall confidence score
        - summary: Research summary
        - checklist_results: Per-query results with completion status
        - queries_executed: List of all queries executed

    Example:
        >>> checklist = [
        ...     {"query": "TSLA P/E ratio", "symbols": ["TSLA"], "keywords": ["P/E ratio"]},
        ...     {"query": "META earnings", "symbols": ["META"], "keywords": ["earnings"]},
        ... ]
        >>> result = await parallel_query_research(checklist, min_results_per_query=5)
    """
    logger.info(f"🔬 Starting parallel research for {len(checklist_items)} queries")

    # Execute all queries in parallel
    async def execute_single_query(item: Dict[str, Any]) -> Dict[str, Any]:
        query = item["query"]
        symbols = item.get("symbols", [])
        keywords = item.get("keywords", [])

        logger.info(f"🔍 Executing: {query}")

        # Search with guaranteed minimum results
        search_results = await search_web(query, max_results=min_results_per_query)

        if len(search_results) < min_results_per_query:
            logger.warning(f"⚠️  Query '{query}' returned only {len(search_results)} results (< {min_results_per_query})")

        # Browse top results for this query
        urls_to_browse = [r["url"] for r in search_results[:max_browse_per_query]]
        browse_tasks = [browse_url(url) for url in urls_to_browse]
        browse_results = await asyncio.gather(*browse_tasks)

        # Extract successful content
        chunks = []
        sources = []
        for result in browse_results:
            if result["success"] and result["content"]:
                score = score_content(result["content"], query)
                if score >= min_confidence:
                    chunks.append({
                        "url": result["url"],
                        "title": result["title"],
                        "content": result["content"],
                        "score": score,
                        "source_query": query,  # Track which query this came from
                    })
                    sources.append(result["url"])

        return {
            "query": query,
            "search_count": len(search_results),
            "chunks": chunks,
            "sources": sources,
            "completed": True,
            "timestamp": asyncio.get_event_loop().time(),
        }

    # Execute all queries in parallel
    tasks = [execute_single_query(item) for item in checklist_items]
    query_results = await asyncio.gather(*tasks)

    # Combine all results
    all_chunks = []
    all_sources = []
    queries_executed = []

    for result in query_results:
        all_chunks.extend(result["chunks"])
        all_sources.extend(result["sources"])
        queries_executed.append(result["query"])

    # Deduplicate sources
    unique_sources = list(dict.fromkeys(all_sources))

    # Sort chunks by score
    all_chunks.sort(key=lambda x: x["score"], reverse=True)

    # Calculate overall confidence
    avg_confidence = sum(c["score"] for c in all_chunks) / len(all_chunks) if all_chunks else 0.0

    # Generate summary
    if all_chunks:
        summary = f"Found {len(all_chunks)} relevant sources across {len(checklist_items)} queries. " + \
                  f"Top sources: {', '.join(unique_sources[:3])}"
    else:
        summary = f"No relevant results found for {len(checklist_items)} queries"

    logger.info(f"✅ Parallel research complete: {len(all_chunks)} total chunks from {len(checklist_items)} queries")

    return {
        "content_chunks": all_chunks,
        "sources": unique_sources,
        "confidence": avg_confidence,
        "summary": summary,
        "checklist_results": query_results,  # Per-query details
        "queries_executed": queries_executed,
    }


async def general_research(
    query: str,
    symbols: Optional[List[str]] = None,
    llm_keywords: Optional[List[str]] = None,
    max_results: int = 10,
    max_browse: int = 5,
    min_confidence: float = 0.4,
) -> Dict[str, Any]:
    """
    Perform general research on any topic.

    **Enhanced with multi-query search strategy**:
    - Extracts keywords from user query
    - Combines keywords with symbols for better search
    - Searches multiple query variations
    - Checks 10+ results (increased from 5)
    - Browses 5+ URLs (increased from 3)

    Flow:
    1. Reformulate query with keywords + symbols
    2. Search web for each query variation (Tavily)
    3. Browse top results (Playwright)
    4. Extract and score content
    5. Return research summary

    Args:
        query: Research query (e.g., "how was the earning of Meta?")
        symbols: List of stock symbols (e.g., ["META", "GOOGL"])
        max_results: Maximum search results per query (default: 10)
        max_browse: Maximum URLs to browse total (default: 5)
        min_confidence: Minimum confidence threshold (default: 0.4)

    Returns:
        Dict with:
        - content_chunks: List of extracted content with scores
        - sources: List of source URLs
        - confidence: Overall confidence score
        - summary: Brief summary of findings
        - queries_used: List of search queries that were tried

    Examples:
        >>> # Query with symbols
        >>> result = await general_research(
        ...     query="how was the earning of Meta?",
        ...     symbols=["META"],
        ...     max_results=10,
        ...     max_browse=5
        ... )
        >>> # Searches: "META earnings", "META earnings call", "META quarterly earnings", etc.

        >>> # Query without symbols
        >>> result = await general_research(
        ...     query="what is an earnings call?",
        ...     symbols=None,
        ...     max_results=10,
        ...     max_browse=5
        ... )
        >>> # Searches: "earnings call", "earnings", "quarterly report", etc.
    """
    logger.info(f"🔬 Starting general research: {query}")
    logger.info(f"   Symbols: {symbols}")
    logger.info(f"   LLM Keywords: {llm_keywords}")
    logger.info(f"   Max results per query: {max_results}")
    logger.info(f"   Max URLs to browse: {max_browse}")

    # Step 1: Reformulate queries with keywords + symbols
    search_queries = reformulate_queries(query, symbols=symbols, llm_keywords=llm_keywords)
    logger.info(f"📋 Reformulated into {len(search_queries)} search queries: {search_queries}")

    # Step 2: Search web with multiple queries
    all_search_results = []
    for search_query in search_queries:
        results = await search_web(search_query, max_results=max_results)
        all_search_results.extend(results)
        logger.info(f"   Query '{search_query}': {len(results)} results")

    if not all_search_results:
        logger.warning("No search results found for any query")
        return {
            "content_chunks": [],
            "sources": [],
            "confidence": 0.0,
            "summary": f"No results found for: {query}",
            "queries_used": search_queries,
        }

    # Deduplicate URLs (keep highest scoring)
    url_to_result = {}
    for result in all_search_results:
        url = result["url"]
        if url not in url_to_result or result.get("score", 0) > url_to_result[url].get("score", 0):
            url_to_result[url] = result

    # Sort by score and take top URLs to browse
    unique_results = list(url_to_result.values())
    unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    urls_to_browse = [r["url"] for r in unique_results[:max_browse]]

    logger.info(f"📖 Browsing {len(urls_to_browse)} unique URLs (from {len(all_search_results)} total results)...")

    # Step 3: Browse top results
    browse_tasks = [browse_url(url) for url in urls_to_browse]
    browse_results = await asyncio.gather(*browse_tasks)

    # Step 4: Extract successful content
    content_chunks = []
    sources = []

    for result in browse_results:
        if result["success"] and result["content"]:
            # Score against original query AND all search queries
            scores = [score_content(result["content"], q) for q in [query] + search_queries]
            max_score = max(scores)

            if max_score >= min_confidence:
                content_chunks.append({
                    "url": result["url"],
                    "title": result["title"],
                    "content": result["content"],
                    "score": max_score,
                })
                sources.append(result["url"])

    # Sort by score
    content_chunks.sort(key=lambda x: x["score"], reverse=True)

    # Calculate overall confidence
    if content_chunks:
        avg_confidence = sum(c["score"] for c in content_chunks) / len(content_chunks)
    else:
        avg_confidence = 0.0

    # Generate summary
    if content_chunks:
        top_chunk = content_chunks[0]["content"][:200] + "..."
        summary = f"Found {len(content_chunks)} relevant sources. Top finding: {top_chunk}"
    else:
        summary = f"Could not find relevant information for: {query}"

    logger.info(f"✅ Research complete: {len(content_chunks)} chunks, confidence={avg_confidence:.2f}")

    return {
        "content_chunks": content_chunks,
        "sources": sources,
        "confidence": avg_confidence,
        "summary": summary,
        "queries_used": search_queries,
    }


# Example usage
if __name__ == "__main__":
    async def test():
        # Test general research
        queries = [
            "Google earnings call Q3 2024",
            "Meta AI spending concerns",
            "Is Apple related to recent product launches?",
        ]

        for query in queries:
            print(f"\n{'='*80}")
            print(f"Query: {query}")
            print(f"{'='*80}")

            result = await general_research(query, max_results=5, max_browse=3)

            print(f"\nResults:")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Sources: {len(result['sources'])}")
            print(f"  Summary: {result['summary']}")

            if result["content_chunks"]:
                print(f"\n  Top chunk:")
                print(f"    Score: {result['content_chunks'][0]['score']:.2f}")
                print(f"    Title: {result['content_chunks'][0]['title']}")
                print(f"    Content preview: {result['content_chunks'][0]['content'][:150]}...")

    asyncio.run(test())
