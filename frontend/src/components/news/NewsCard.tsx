/**
 * NewsCard Component
 * Displays a single news article with metadata
 */

import { ExternalLink, TrendingUp, TrendingDown, AlertCircle } from "lucide-react";
import { Card } from "../ui/card";
import { Badge } from "../ui/badge";
import type { StockNewsItem, EconomicNewsItem } from "../../mocks/news-data";
import { formatTimeAgo } from "../../mocks/news-data";

type NewsItem = StockNewsItem | EconomicNewsItem;

interface NewsCardProps {
  news: NewsItem;
  onClick?: () => void;
  showImpact?: boolean; // Show impact level for economic news
  titleOnly?: boolean; // Show only title for breaking news
}

export function NewsCard({ news, onClick, showImpact = false, titleOnly = false }: NewsCardProps) {
  // Determine sentiment color
  const getSentimentColor = (score: number): string => {
    if (score > 0.3) return "text-green-600";
    if (score < -0.3) return "text-red-600";
    return "text-gray-600";
  };

  // Determine sentiment icon
  const getSentimentIcon = (score: number) => {
    if (score > 0.3) return <TrendingUp className="w-4 h-4" />;
    if (score < -0.3) return <TrendingDown className="w-4 h-4" />;
    return null;
  };

  // Get impact badge color
  const getImpactColor = (level: string): string => {
    switch (level) {
      case 'high': return 'bg-red-100 text-red-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const economicNews = 'category' in news ? news as EconomicNewsItem : null;
  const timeAgo = formatTimeAgo(news.published_at);

  // Title-only mode for breaking news (simplified 2-line format)
  if (titleOnly) {
    return (
      <Card
        className="p-3 hover:shadow-md transition-shadow cursor-pointer border-l-4 border-red-500"
        onClick={onClick}
      >
        {/* Line 1: Breaking badge + Title + Source */}
        <div className="flex items-start gap-2 mb-1">
          <Badge className="bg-red-500 text-white text-xs shrink-0">
            <AlertCircle className="w-3 h-3 mr-1" />
            BREAKING
          </Badge>
          <h3 className="font-semibold text-sm leading-tight flex-1">
            {news.title} <span className="text-gray-500 font-normal">({news.source.name})</span>
          </h3>
          <a
            href={news.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-blue-600 hover:text-blue-800 shrink-0"
          >
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>

        {/* Line 2: Related symbols + Time */}
        <div className="flex items-center gap-2 text-xs text-gray-500 ml-16">
          {economicNews?.related_symbols && economicNews.related_symbols.length > 0 && (
            <span>
              Related: {economicNews.related_symbols.slice(0, 3).join(', ')}
            </span>
          )}
          <span>•</span>
          <span>{timeAgo}</span>
        </div>
      </Card>
    );
  }

  // Full display mode (simplified 2-line format)
  return (
    <Card
      className="p-3 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      {/* Line 1: Title + Source */}
      <div className="flex items-start gap-2 mb-1">
        <div className="flex items-center gap-2 flex-1">
          {/* Show BREAKING badge OR impact badge, not both */}
          {news.is_breaking ? (
            <Badge className="bg-red-500 text-white text-xs shrink-0">
              <AlertCircle className="w-3 h-3 mr-1" />
              BREAKING
            </Badge>
          ) : economicNews && showImpact ? (
            <Badge className={`text-xs shrink-0 ${getImpactColor(economicNews.impact_level)}`}>
              {economicNews.impact_level.toUpperCase()}
            </Badge>
          ) : null}
          <h3 className="font-semibold text-sm leading-tight flex-1">
            {news.title} <span className="text-gray-500 font-normal">({news.source.name})</span>
          </h3>
        </div>
        <a
          href={news.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-blue-600 hover:text-blue-800 shrink-0"
        >
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {/* Line 2: Related symbols + Time */}
      <div className="flex items-center gap-2 text-xs text-gray-500 ml-0">
        {economicNews?.related_symbols && economicNews.related_symbols.length > 0 && (
          <>
            <span>
              Related: {economicNews.related_symbols.slice(0, 3).join(', ')}
            </span>
            <span>•</span>
          </>
        )}
        <span>{timeAgo}</span>
      </div>
    </Card>
  );
}
