/**
 * WatchlistNews Component
 * Shows latest news for watchlist stocks
 */

import { useState, useEffect } from "react";
import { Card } from "../ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Skeleton } from "../ui/skeleton";
import { useStockNews } from "../../hooks/stocks/useStockNews";
import { NewsCard } from "../news/NewsCard";
import { Newspaper } from "lucide-react";

interface WatchlistNewsProps {
  symbols: string[];
  newsPerStock?: number;
}

export function WatchlistNews({ symbols, newsPerStock = 5 }: WatchlistNewsProps) {
  const [activeSymbol, setActiveSymbol] = useState<string>(symbols[0] || '');

  // Update active symbol when symbols change
  useEffect(() => {
    if (symbols.length > 0 && !symbols.includes(activeSymbol)) {
      setActiveSymbol(symbols[0]);
    }
  }, [symbols, activeSymbol]);

  const { news, loading, error, refetch } = useStockNews(activeSymbol, newsPerStock);

  // Hide component if no symbols (don't show empty state)
  if (symbols.length === 0) {
    return null;
  }

  return (
    <Card className="p-6">
      <h3 className="mb-4 flex items-center gap-2">
        <Newspaper className="w-5 h-5" />
        Watchlist News
      </h3>

      <Tabs value={activeSymbol} onValueChange={setActiveSymbol}>
        <TabsList className="w-full justify-start overflow-x-auto">
          {symbols.slice(0, 5).map((symbol) => (
            <TabsTrigger key={symbol} value={symbol} className="font-mono text-xs">
              {symbol}
            </TabsTrigger>
          ))}
        </TabsList>

        {symbols.map((symbol) => (
          <TabsContent key={symbol} value={symbol} className="mt-4">
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-24 w-full" />
                ))}
              </div>
            ) : error ? (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
                Failed to load news for {symbol}
              </div>
            ) : news.length === 0 ? (
              null  // Hide empty state - don't show "No news available"
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {news.slice(0, 5).map((item) => (
                  <NewsCard
                    key={item.id}
                    news={item}
                    onClick={() => window.open(item.url, '_blank')}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </Card>
  );
}
