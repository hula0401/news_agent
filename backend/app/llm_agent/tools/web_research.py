"""
Web Research Tools with Playwright Browser Automation

Features:
1. Browser reading with JS rendering
2. Clean text extraction
3. Research loop (2-3 hops max)
4. Citation tracking
5. Confidence scoring
"""
import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
import re

logger = logging.getLogger(__name__)


# ====== BROWSER READING ======

async def browser_read(
    url: str,
    max_length: int = 5000,
    timeout: int = 10000,
) -> Dict[str, any]:
    """
    Read webpage content using Playwright headless browser.

    Renders JavaScript and extracts clean text from the page.

    **Skips PDF files and other binary documents** to avoid download errors.

    Args:
        url: URL to fetch
        max_length: Maximum content length to extract
        timeout: Page load timeout in milliseconds

    Returns:
        Dict with:
        - url: Original URL
        - title: Page title
        - content: Extracted clean text
        - metadata: Additional page info
        - success: Whether fetch succeeded
        - error: Error message if failed
    """
    start_time = asyncio.get_event_loop().time()

    # Check if URL is a PDF or other binary file
    binary_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar']
    url_lower = url.lower()

    if any(url_lower.endswith(ext) or ext in url_lower for ext in binary_extensions):
        logger.warning(f"⏭️  Skipping binary file (PDF/document): {url}")
        return {
            "url": url,
            "title": "Binary file (skipped)",
            "content": "",
            "metadata": {"skipped": True, "reason": "Binary file format"},
            "success": False,
            "error": "Binary file format not supported (PDF/document)",
            "duration_ms": 0,
        }

    try:
        async with async_playwright() as p:
            # Launch headless browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()

            # Navigate to URL with timeout
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")

            # Wait a bit for dynamic content
            await page.wait_for_timeout(1000)

            # Extract title
            title = await page.title()

            # Extract main content
            content = await _extract_clean_content(page)

            # Truncate if too long
            if len(content) > max_length:
                content = content[:max_length] + "..."

            # Get metadata
            metadata = {
                "loaded_at": datetime.now().isoformat(),
                "content_length": len(content),
                "has_javascript": True,
            }

            await browser.close()

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            logger.info(f"✅ Browser read: {url} ({duration_ms:.0f}ms, {len(content)} chars)")

            return {
                "url": url,
                "title": title,
                "content": content,
                "metadata": metadata,
                "success": True,
                "error": None,
                "duration_ms": duration_ms,
            }

    except Exception as e:
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.error(f"❌ Browser read failed: {url} - {str(e)}")

        return {
            "url": url,
            "title": None,
            "content": None,
            "metadata": {},
            "success": False,
            "error": str(e),
            "duration_ms": duration_ms,
        }


async def _extract_clean_content(page: Page) -> str:
    """
    Extract clean, readable text from page.

    Strategy:
    1. Remove unwanted elements first
    2. Try <article> tag (news sites)
    3. Try main content selectors
    4. Try paragraphs within main areas
    5. Fall back to body text
    """
    # First, remove all unwanted elements
    await page.evaluate("""
        () => {
            // Remove navigation, headers, footers, ads, scripts, styles
            const unwantedSelectors = [
                'nav', 'header', 'footer', 'aside',
                '.nav', '.navigation', '.header', '.footer', '.sidebar',
                '.ad', '.ads', '.advertisement', '.promo',
                '.social', '.social-share', '.share-buttons',
                '.comments', '.related-articles',
                'script', 'style', 'noscript',
                '[role="navigation"]', '[role="complementary"]',
                '.menu', '.site-header', '.site-footer'
            ];

            unwantedSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => el.remove());
            });
        }
    """)

    # Try article tag (common in news sites)
    article = await page.query_selector("article")
    if article:
        # Get paragraphs within article
        paragraphs = await article.query_selector_all("p")
        if paragraphs and len(paragraphs) > 2:
            texts = []
            for p in paragraphs:
                text = await p.inner_text()
                if len(text.strip()) > 20:  # Meaningful paragraph
                    texts.append(text.strip())
            if texts:
                return _clean_text('\n\n'.join(texts))

    # Try main content selectors
    main_selectors = [
        "main article",
        "main",
        "[role='main']",
        ".article-body",
        ".article-content",
        ".story-body",
        ".entry-content",
        ".post-content",
        "#article-body",
        "#content article",
    ]

    for selector in main_selectors:
        element = await page.query_selector(selector)
        if element:
            # Try to get paragraphs first
            paragraphs = await element.query_selector_all("p")
            if paragraphs and len(paragraphs) >= 2:
                texts = []
                for p in paragraphs:
                    text = await p.inner_text()
                    if len(text.strip()) > 20:
                        texts.append(text.strip())
                if texts:
                    return _clean_text('\n\n'.join(texts))

            # Fall back to full element text
            text = await element.inner_text()
            if len(text.strip()) > 200:
                return _clean_text(text)

    # Last resort: get all paragraphs from body
    paragraphs = await page.query_selector_all("body p")
    if paragraphs:
        texts = []
        for p in paragraphs:
            text = await p.inner_text()
            if len(text.strip()) > 30:  # Longer threshold for body paragraphs
                texts.append(text.strip())

        if texts:
            # Take first 10-15 meaningful paragraphs
            return _clean_text('\n\n'.join(texts[:15]))

    # Ultimate fallback
    body = await page.query_selector("body")
    if body:
        text = await body.inner_text()
        return _clean_text(text)

    return ""


def _clean_text(text: str) -> str:
    """Clean extracted text"""
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r' +', ' ', text)

    # Remove common noise
    text = re.sub(r'Cookie Policy|Privacy Policy|Terms of Service', '', text, flags=re.IGNORECASE)

    return text.strip()


# ====== RESEARCH LOOP ======

async def research_loop(
    news_items: List[Dict],
    query: str,
    max_hops: int = 2,
    max_urls: int = 3,
) -> Dict[str, any]:
    """
    Perform research loop: search → browse → score → (optional) browse next → answer.

    Args:
        news_items: List of news items from initial search
        query: User query
        max_hops: Maximum number of browsing hops (2-3)
        max_urls: Maximum URLs to browse per hop

    Returns:
        Dict with:
        - content_chunks: List of content chunks with citations
        - citations: List of source URLs
        - confidence: Confidence score (0-1)
        - summary: Research summary
    """
    logger.info(f"🔍 Research loop: {max_hops} hops, {max_urls} URLs/hop")

    # Hop 1: Browse top news URLs
    hop1_results = await _browse_hop(news_items[:max_urls], query, hop_num=1)

    # Score results
    scored = _score_chunks(hop1_results["chunks"], query)

    # Decide if we need hop 2
    avg_confidence = sum(c["score"] for c in scored) / len(scored) if scored else 0

    content_chunks = []
    citations = set()

    # Add hop 1 results
    for chunk in scored:
        content_chunks.append(chunk)
        citations.add(chunk["url"])

    # Hop 2: If confidence low and we have more URLs, browse them
    if avg_confidence < 0.7 and max_hops >= 2 and len(news_items) > max_urls:
        logger.info(f"📊 Hop 1 confidence: {avg_confidence:.2f} < 0.7, proceeding to hop 2")

        hop2_results = await _browse_hop(news_items[max_urls:max_urls*2], query, hop_num=2)
        hop2_scored = _score_chunks(hop2_results["chunks"], query)

        for chunk in hop2_scored:
            content_chunks.append(chunk)
            citations.add(chunk["url"])

        # Recalculate confidence
        avg_confidence = sum(c["score"] for c in content_chunks) / len(content_chunks) if content_chunks else 0

    # Build summary
    summary = _build_research_summary(content_chunks, query)

    logger.info(f"✅ Research complete: {len(content_chunks)} chunks, {len(citations)} sources, confidence={avg_confidence:.2f}")

    return {
        "content_chunks": content_chunks,
        "citations": list(citations),
        "confidence": avg_confidence,
        "summary": summary,
        "num_chunks": len(content_chunks),
        "num_sources": len(citations),
    }


async def _browse_hop(news_items: List[Dict], query: str, hop_num: int) -> Dict:
    """Browse URLs in parallel for this hop"""
    logger.info(f"📖 Hop {hop_num}: Browsing {len(news_items)} URLs...")

    # Browse URLs in parallel
    tasks = [browser_read(item["url"]) for item in news_items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results into chunks
    chunks = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"⚠️  URL {i+1} failed: {result}")
            continue

        if not result["success"]:
            continue

        # Create content chunk with citation
        chunk = {
            "content": result["content"],
            "title": result["title"],
            "url": result["url"],
            "source": news_items[i].get("source_website", "unknown"),
            "hop": hop_num,
            "score": 0.0,  # To be scored later
        }
        chunks.append(chunk)

    logger.info(f"✅ Hop {hop_num}: Retrieved {len(chunks)}/{len(news_items)} URLs successfully")

    return {"chunks": chunks, "hop": hop_num}


def _score_chunks(chunks: List[Dict], query: str) -> List[Dict]:
    """
    Score content chunks by relevance to query.

    Simple scoring:
    - Query term presence
    - Content length (longer = more detailed)
    - Title relevance
    """
    query_terms = set(query.lower().split())

    for chunk in chunks:
        score = 0.0
        content = chunk["content"] or ""
        title = chunk["title"] or ""

        # Score based on query term presence
        content_lower = content.lower()
        title_lower = title.lower()

        matching_terms = sum(1 for term in query_terms if term in content_lower)
        score += matching_terms * 0.2

        # Title bonus
        title_matches = sum(1 for term in query_terms if term in title_lower)
        score += title_matches * 0.3

        # Length bonus (more content = more detailed)
        if len(content) > 1000:
            score += 0.2
        elif len(content) > 500:
            score += 0.1

        # Cap at 1.0
        chunk["score"] = min(score, 1.0)

    # Sort by score descending
    chunks.sort(key=lambda x: x["score"], reverse=True)

    return chunks


def _build_research_summary(chunks: List[Dict], query: str) -> str:
    """Build research summary from chunks"""
    if not chunks:
        return "No detailed content available."

    # Take top 3 chunks
    top_chunks = chunks[:3]

    # Extract key sentences
    summary_parts = []
    for chunk in top_chunks:
        # Get first 2 sentences
        sentences = chunk["content"].split('. ')[:2]
        snippet = '. '.join(sentences)
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."
        summary_parts.append(f"- {snippet} (Source: {chunk['source']})")

    summary = "\n".join(summary_parts)
    return summary


# ====== ANSWER COMPOSER ======

def compose_voice_answer(
    content_chunks: List[Dict],
    query: str,
    confidence: float,
    max_words: int = 25,
) -> Dict[str, str]:
    """
    Compose voice-friendly answer (15-25 words).

    Includes hedge when confidence < 0.6

    Args:
        content_chunks: Research chunks
        query: User query
        confidence: Confidence score (0-1)
        max_words: Maximum words for answer

    Returns:
        Dict with:
        - answer: Voice-friendly summary
        - hedge: Hedge statement if low confidence
        - citations: Source links
    """
    if not content_chunks:
        return {
            "answer": "I couldn't find detailed information about that.",
            "hedge": None,
            "citations": [],
        }

    # Extract key facts from top chunk
    top_chunk = content_chunks[0]
    content = top_chunk["content"]

    # Extract first sentence or first N words
    sentences = content.split('. ')
    first_sentence = sentences[0] if sentences else content

    # Truncate to max_words
    words = first_sentence.split()
    if len(words) > max_words:
        answer = ' '.join(words[:max_words]) + "..."
    else:
        answer = first_sentence

    # Add hedge if low confidence
    hedge = None
    if confidence < 0.6:
        hedge = "Based on limited sources available."

    # Get citations
    citations = [c["url"] for c in content_chunks[:3]]

    return {
        "answer": answer,
        "hedge": hedge,
        "citations": citations,
    }


# ====== EXPORT ======

__all__ = [
    "browser_read",
    "research_loop",
    "compose_voice_answer",
]
