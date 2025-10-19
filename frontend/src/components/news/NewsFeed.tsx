/**
 * NewsFeed Component
 * Displays a list of news articles
 */

import { Newspaper, RefreshCw } from "lucide-react";
import { NewsCard } from "./NewsCard";
import { Button } from "../ui/button";
import { Skeleton } from "../ui/skeleton";
import type { StockNewsItem, EconomicNewsItem } from "../../mocks/news-data";

type NewsItem = StockNewsItem | EconomicNewsItem;

interface NewsFeedProps {
  news: NewsItem[];
  loading?: boolean;
  error?: Error | null;
  title?: string;
  onRefresh?: () => void;
  showImpact?: boolean;
  emptyMessage?: string;
  titleOnly?: boolean; // Display news cards in title-only mode (for breaking news)
}

export function NewsFeed({
  news,
  loading = false,
  error = null,
  title = "News Feed",
  onRefresh,
  showImpact = false,
  emptyMessage = "No news available",
  titleOnly = false,
}: NewsFeedProps) {
  // Hide component if no news and not loading (don't show empty state)
  if (!loading && !error && news.length === 0) {
    return null;
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between mb-4">
          <h3 className="flex items-center gap-2">
            <Newspaper className="w-5 h-5" />
            {title}
          </h3>
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between mb-4">
          <h3 className="flex items-center gap-2">
            <Newspaper className="w-5 h-5" />
            {title}
          </h3>
        </div>
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">
            Failed to load news: {error.message}
          </p>
          {onRefresh && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              className="mt-2"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="flex items-center gap-2">
          <Newspaper className="w-5 h-5" />
          {title}
          <span className="text-sm text-muted-foreground">({news.length})</span>
        </h3>
        {onRefresh && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            className="h-8"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        )}
      </div>

      {/* News List */}
      {news.length === 0 ? (
        <div className="p-8 text-center text-muted-foreground">
          <Newspaper className="w-12 h-12 mx-auto mb-2 opacity-20" />
          <p>{emptyMessage}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {news.map((item) => (
            <NewsCard
              key={item.id}
              news={item}
              showImpact={showImpact}
              titleOnly={titleOnly}
              onClick={() => window.open(item.url, '_blank')}
            />
          ))}
        </div>
      )}
    </div>
  );
}
