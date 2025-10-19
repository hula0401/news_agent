'use client'

import { useEffect, useState } from "react";
import { Card } from "./ui/card";
import { RefreshCw, TrendingUp, TrendingDown } from "lucide-react";
import { Button } from "./ui/button";
import { Skeleton } from "./ui/skeleton";
import { useWatchlistPrices } from "../hooks/stocks/useWatchlistPrices";
import { getStockName } from "../mocks/stock-data";

export function WatchlistCard() {
  const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)
    || (import.meta.env.NEXT_PUBLIC_API_URL as string | undefined)
    || 'http://localhost:8000';
  const DEMO_USER_ID = (import.meta.env.VITE_DEMO_USER_ID as string | undefined) || '03f6b167-0c4d-4983-a380-54b8eb42f830';

  const [symbols, setSymbols] = useState<string[]>([]);
  const [symbolsLoading, setSymbolsLoading] = useState(true);
  const [symbolsError, setSymbolsError] = useState<string | null>(null);

  // Fetch watchlist symbols from /api/user/preferences endpoint
  useEffect(() => {
    const load = async () => {
      // Fetch from /api/user/preferences endpoint (per API_DESIGN.md)
      // IMPORTANT: Don't use profile context - fetch directly from API
      const userId = DEMO_USER_ID || "demo-user-id";
      try {
        const res = await fetch(`${API_BASE}/api/user/preferences?user_id=${encodeURIComponent(userId)}`);
        if (!res.ok) {
          // If 404, user doesn't exist - don't show default symbols
          if (res.status === 404) {
            setSymbols([]);
            setSymbolsLoading(false);
            return;
          }
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        // Extract watchlist from preferences
        const watchlistSymbols = data.watchlist_stocks || [];
        setSymbols(watchlistSymbols);
      } catch (e: any) {
        setSymbolsError(e?.message || "Failed to load watchlist");
        // Don't set default symbols - hide if no data
        setSymbols([]);
      } finally {
        setSymbolsLoading(false);
      }
    };

    load();
  }, [API_BASE, DEMO_USER_ID]);

  // Fetch prices for watchlist symbols
  const { prices, loading: pricesLoading, error: pricesError, refetch, isMarketOpen } = useWatchlistPrices(symbols);

  const loading = symbolsLoading || pricesLoading;
  const error = symbolsError || pricesError;

  // Hide card if no symbols (don't show empty state)
  if (!loading && symbols.length === 0) {
    return null;
  }

  return (
    <Card className="p-6 border-0 shadow-lg shadow-blue-100/50 bg-white/80 backdrop-blur">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900">Watchlist</h3>
          {isMarketOpen && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
              Market Open
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={refetch}
          disabled={loading}
          className="h-8 hover:bg-blue-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {loading && symbols.length === 0 ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : error && symbols.length === 0 ? (
        <div className="text-sm text-red-500">{error.message || String(error)}</div>
      ) : symbols.length === 0 ? (
        <div className="text-sm text-muted-foreground">No symbols yet.</div>
      ) : (
        <div className="space-y-3">
          {prices.length > 0 ? (
            prices.map((stock) => {
              const isPositive = stock.change >= 0;
              return (
                <div key={stock.symbol} className="flex items-center justify-between p-3 bg-gradient-to-r from-gray-50 to-white rounded-xl hover:shadow-md transition-all border border-gray-100">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-gray-900">{stock.symbol}</span>
                      {isPositive ? (
                        <TrendingUp className="w-4 h-4 text-green-500" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-500" />
                      )}
                    </div>
                    <p className="text-xs text-gray-500">{getStockName(stock.symbol)}</p>
                  </div>

                  <div className="text-right">
                    <div className="font-bold text-gray-900">${stock.price.toFixed(2)}</div>
                    <div className={`text-xs font-semibold ${isPositive ? "text-green-600" : "text-red-600"}`}>
                      {isPositive ? "+" : ""}{stock.change.toFixed(2)} ({isPositive ? "+" : ""}{stock.change_percent.toFixed(2)}%)
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            symbols.map((symbol) => (
              <div key={symbol} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
                <span className="font-mono text-sm font-semibold">{symbol}</span>
                <Skeleton className="h-8 w-24 rounded-lg" />
              </div>
            ))
          )}
        </div>
      )}
    </Card>
  );
}


