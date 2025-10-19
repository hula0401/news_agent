"""News-related Pydantic models."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class NewsSource(BaseModel):
    """News source model."""
    id: str = Field(..., description="Source ID")
    name: str = Field(..., description="Source name")
    url: Optional[str] = Field(None, description="Source URL")
    category: str = Field(..., description="Source category")
    reliability_score: float = Field(..., description="Reliability score (0-1)")
    is_active: bool = Field(default=True, description="Source active status")
    created_at: datetime = Field(..., description="Creation timestamp")


class NewsArticle(BaseModel):
    """News article model."""
    id: str = Field(..., description="Article ID")
    source_id: str = Field(..., description="Source ID")
    external_id: Optional[str] = Field(None, description="External source ID")
    title: str = Field(..., description="Article title")
    summary: Optional[str] = Field(None, description="Article summary")
    content: Optional[str] = Field(None, description="Article content")
    url: Optional[str] = Field(None, description="Article URL")
    published_at: datetime = Field(..., description="Publication timestamp")
    sentiment_score: Optional[float] = Field(None, description="Sentiment score (-1 to 1)")
    relevance_score: float = Field(default=0.5, description="Relevance score (0-1)")
    topics: List[str] = Field(default=[], description="Article topics")
    keywords: List[str] = Field(default=[], description="Article keywords")
    is_breaking: bool = Field(default=False, description="Breaking news flag")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    source: Optional[NewsSource] = Field(None, description="News source")


class NewsArticleCreate(BaseModel):
    """News article creation model."""
    source_id: str = Field(..., description="Source ID")
    external_id: Optional[str] = Field(None, description="External source ID")
    title: str = Field(..., description="Article title")
    summary: Optional[str] = Field(None, description="Article summary")
    content: Optional[str] = Field(None, description="Article content")
    url: Optional[str] = Field(None, description="Article URL")
    published_at: datetime = Field(..., description="Publication timestamp")
    sentiment_score: Optional[float] = Field(None, description="Sentiment score (-1 to 1)")
    relevance_score: float = Field(default=0.5, description="Relevance score (0-1)")
    topics: List[str] = Field(default=[], description="Article topics")
    keywords: List[str] = Field(default=[], description="Article keywords")
    is_breaking: bool = Field(default=False, description="Breaking news flag")


class NewsSearchRequest(BaseModel):
    """News search request model."""
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="News category filter")
    topics: Optional[List[str]] = Field(None, description="Topic filters")
    limit: int = Field(default=10, description="Maximum results")
    offset: int = Field(default=0, description="Results offset")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    sentiment_min: Optional[float] = Field(None, description="Minimum sentiment score")
    sentiment_max: Optional[float] = Field(None, description="Maximum sentiment score")


class NewsLatestRequest(BaseModel):
    """Latest news request model."""
    topics: Optional[List[str]] = Field(None, description="Topic filters")
    limit: int = Field(default=10, description="Maximum results")
    breaking_only: bool = Field(default=False, description="Breaking news only")
    category: Optional[str] = Field(None, description="Category filter")


class NewsSummaryRequest(BaseModel):
    """News summary request model."""
    article_ids: List[str] = Field(..., description="Article IDs to summarize")
    summary_type: str = Field(default="brief", description="Summary type (brief/deep_dive)")
    max_length: int = Field(default=200, description="Maximum summary length")


class NewsSummaryResponse(BaseModel):
    """News summary response model."""
    article_id: str = Field(..., description="Article ID")
    summary: str = Field(..., description="Generated summary")
    summary_type: str = Field(..., description="Summary type")
    word_count: int = Field(..., description="Summary word count")
    processing_time_ms: int = Field(..., description="Processing time")


class NewsResponse(BaseModel):
    """News response model."""
    articles: List[NewsArticle] = Field(..., description="News articles")
    total_count: int = Field(..., description="Total article count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    has_more: bool = Field(..., description="Has more pages")


class BreakingNewsAlert(BaseModel):
    """Breaking news alert model."""
    id: str = Field(..., description="Alert ID")
    article_id: str = Field(..., description="Article ID")
    title: str = Field(..., description="Alert title")
    summary: str = Field(..., description="Alert summary")
    severity: str = Field(..., description="Alert severity (low/medium/high)")
    topics: List[str] = Field(..., description="Alert topics")
    created_at: datetime = Field(..., description="Alert timestamp")
    expires_at: datetime = Field(..., description="Alert expiration")


class NewsTrend(BaseModel):
    """News trend model."""
    topic: str = Field(..., description="Trending topic")
    article_count: int = Field(..., description="Article count")
    sentiment_avg: float = Field(..., description="Average sentiment")
    trend_score: float = Field(..., description="Trend score")
    period: str = Field(..., description="Time period")
    created_at: datetime = Field(..., description="Trend timestamp")


# ==================== Economic News API Models ====================


class EconomicNewsItem(BaseModel):
    """Economic news item model."""
    id: str = Field(..., description="News article ID")
    title: str = Field(..., description="News title")
    summary: Optional[str] = Field(None, description="News summary")
    url: Optional[str] = Field(None, description="Article URL")
    published_at: datetime = Field(..., description="Publication timestamp")
    source: Dict[str, Any] = Field(..., description="News source information")
    category: str = Field(..., description="News category (federal_reserve, politics, etc.)")
    region: str = Field(default="us", description="Geographic region")
    impact_level: Optional[str] = Field(None, description="Market impact level (low/medium/high)")
    sentiment_score: Optional[float] = Field(None, description="Sentiment score (-1 to 1)")
    topics: List[str] = Field(default=[], description="Article topics")
    is_breaking: bool = Field(default=False, description="Breaking news flag")
    related_symbols: List[str] = Field(default=[], description="Related stock symbols")
    affected_sectors: List[str] = Field(default=[], description="Affected economic sectors")
    key_points: List[str] = Field(default=[], description="Key information points")
    market_impact: Optional[str] = Field(None, description="Market impact analysis")


class EconomicNewsResponse(BaseModel):
    """Economic news response model."""
    news: List[EconomicNewsItem] = Field(..., description="News articles")
    total_count: int = Field(..., description="Total number of articles")
    categories: List[str] = Field(..., description="Categories included")
    last_updated: datetime = Field(..., description="Last update timestamp")
    cache_hit: bool = Field(default=False, description="Whether data came from cache")


class FederalReserveNewsItem(BaseModel):
    """Federal Reserve news item model."""
    id: str = Field(..., description="Announcement ID")
    type: str = Field(..., description="Type (fomc_statement, speech, minutes, report, press_release)")
    title: str = Field(..., description="Announcement title")
    summary: Optional[str] = Field(None, description="Summary")
    url: Optional[str] = Field(None, description="Official URL")
    published_at: datetime = Field(..., description="Publication timestamp")
    key_points: List[str] = Field(default=[], description="Key points from announcement")
    market_impact: Optional[str] = Field(None, description="Expected market impact (low/medium/high)")
    related_indicators: List[str] = Field(default=[], description="Related economic indicators")


class FederalReserveNewsResponse(BaseModel):
    """Federal Reserve news response model."""
    announcements: List[FederalReserveNewsItem] = Field(..., description="Fed announcements")
    total_count: int = Field(..., description="Total number of announcements")
    last_updated: datetime = Field(..., description="Last update timestamp")


class PoliticsNewsItem(BaseModel):
    """Political news item model."""
    id: str = Field(..., description="News article ID")
    title: str = Field(..., description="News title")
    summary: Optional[str] = Field(None, description="News summary")
    url: Optional[str] = Field(None, description="Article URL")
    published_at: datetime = Field(..., description="Publication timestamp")
    region: str = Field(..., description="Geographic region (us, eu, china, etc.)")
    impact_level: Optional[str] = Field(None, description="Market impact level (low/medium/high)")
    affected_sectors: List[str] = Field(default=[], description="Affected sectors")
    related_symbols: List[str] = Field(default=[], description="Related stock symbols")
    sentiment_score: Optional[float] = Field(None, description="Sentiment score (-1 to 1)")


class PoliticsNewsResponse(BaseModel):
    """Political news response model."""
    news: List[PoliticsNewsItem] = Field(..., description="Political news articles")
    total_count: int = Field(..., description="Total number of articles")
    regions: List[str] = Field(..., description="Regions covered")
    last_updated: datetime = Field(..., description="Last update timestamp")
