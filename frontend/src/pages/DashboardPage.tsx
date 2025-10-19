import React, { useState } from "react";
import { ContinuousVoiceInterface } from "../components/ContinuousVoiceInterface";
import { QuickCommands } from "../components/QuickCommands";
import { StatusIndicators } from "../components/StatusIndicators";
import { Card } from "../components/ui/card";
import { WatchlistCard } from "../components/WatchlistCard";
import { NewsFeed } from "../components/news/NewsFeed";
import { WatchlistNews } from "../components/stocks/WatchlistNews";
import { Button } from "../components/ui/button";
import { LogViewer } from "../components/LogViewer";
import { User, History, Settings, LogOut, Volume2 } from "lucide-react";
import { useAuth } from "../lib/auth-context";
import { useGeneralNews } from "../hooks/stocks/useGeneralNews";
import { toast } from "../utils/toast-logger";
import { logger } from "../utils/logger";
import { cn } from "../components/ui/utils";

type VoiceState = "idle" | "listening" | "speaking" | "connecting";

interface DashboardPageProps {
  onNavigate: (page: "dashboard" | "profile" | "history") => void;
}

export function DashboardPage({ onNavigate }: DashboardPageProps) {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [isConnected, setIsConnected] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<Array<{
    id: string;
    type: 'user' | 'agent';
    text: string;
    timestamp: Date;
  }>>([]);
  const [watchlistSymbols, setWatchlistSymbols] = useState<string[]>([]); // Get from user preferences

  const { user, logout } = useAuth();

  // Fetch general news (top 3)
  const { news: generalNews, loading: newsLoading, error: newsError, refetch: refetchNews } = useGeneralNews(3);

  // Fetch watchlist symbols from user preferences
  React.useEffect(() => {
    const fetchWatchlist = async () => {
      if (!user?.id) return;

      const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)
        || (import.meta.env.NEXT_PUBLIC_API_URL as string | undefined)
        || 'http://localhost:8000';

      try {
        const res = await fetch(`${API_BASE}/api/user/preferences?user_id=${encodeURIComponent(user.id)}`);
        if (res.ok) {
          const data = await res.json();
          setWatchlistSymbols(data.watchlist_stocks || []);
        } else {
          // User doesn't exist or error - no watchlist
          setWatchlistSymbols([]);
        }
      } catch (error) {
        logger.error('dashboard', 'Failed to fetch watchlist', error);
        setWatchlistSymbols([]);
      }
    };

    fetchWatchlist();
  }, [user?.id]);

  // Create refs to pass to ContinuousVoiceInterface
  const handleConnectionChange = (connected: boolean) => {
    setIsConnected(connected);
    logger.info('dashboard', `Connection status changed: ${connected ? 'connected' : 'disconnected'}`);
  };

  const handleVoiceStateChange = (state: VoiceState) => {
    setVoiceState(state);
    logger.info('dashboard', `Voice state changed: ${state}`);
  };

  // Log state changes
  React.useEffect(() => {
    logger.info('state', `Voice state changed: ${voiceState}`);
  }, [voiceState]);

  React.useEffect(() => {
    logger.info('state', `Connection state changed: ${isConnected ? 'connected' : 'disconnected'}`);
  }, [isConnected]);

  const generateUUID = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  };

  const handleTranscription = (text: string) => {
    const newEntry = {
      id: Date.now().toString(),
      type: 'user' as const,
      text,
      timestamp: new Date()
    };
    setConversationHistory(prev => [...prev, newEntry]);
  };

  const handleResponse = (text: string) => {
    const newEntry = {
      id: Date.now().toString(),
      type: 'agent' as const,
      text,
      timestamp: new Date()
    };
    setConversationHistory(prev => [...prev, newEntry]);
  };

  const handleError = (error: string) => {
    toast.error(error);
  };

  const handleQuickCommand = (command: string) => {
    logger.info('ui', `Quick command clicked: ${command}`);
    // Quick commands will be handled by the continuous voice interface
    toast.info(`Quick command: ${command}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
                <Volume2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                  Voice Agent
                </h2>
                <p className="text-xs text-gray-500">AI-Powered Assistant</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
                   <Button
                     variant="ghost"
                     size="icon"
                     onClick={() => {
                       logger.info('ui', 'Profile button clicked');
                       onNavigate("profile");
                     }}
                     className="hover:bg-blue-50"
                   >
                     <User className="w-5 h-5" />
                   </Button>
                   <Button
                     variant="ghost"
                     size="icon"
                     onClick={() => {
                       logger.info('ui', 'Conversation history button clicked');
                       onNavigate("history");
                     }}
                     className="hover:bg-blue-50"
                   >
                     <History className="w-5 h-5" />
                   </Button>
                   <Button
                     variant="ghost"
                     size="icon"
                     onClick={() => {
                       logger.info('ui', 'Logout button clicked');
                       logout();
                     }}
                     className="hover:bg-red-50 hover:text-red-600"
                   >
                     <LogOut className="w-5 h-5" />
                   </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Status & News */}
          <div className="space-y-6">
            <Card className="p-6 border-0 shadow-lg shadow-blue-100/50 bg-white/80 backdrop-blur">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">Connection Status</h3>
                <div className={cn(
                  "w-2 h-2 rounded-full animate-pulse",
                  isConnected ? "bg-green-500" : "bg-gray-300"
                )} />
              </div>
              <StatusIndicators
                isConnected={isConnected}
                isListening={voiceState === "listening"}
                isSpeaking={voiceState === "speaking"}
              />
            </Card>

            {/* General News Feed */}
            <Card className="p-6 border-0 shadow-lg shadow-blue-100/50 bg-white/80 backdrop-blur">
              <NewsFeed
                news={generalNews}
                loading={newsLoading}
                error={newsError}
                title="Top News"
                onRefresh={refetchNews}
                showImpact={true}
                emptyMessage="No economic news available"
              />
            </Card>
          </div>

          {/* Center Column - Voice Interface */}
          <div className="flex flex-col items-center justify-center gap-8">
            <div className="text-center">
              <h1 className="mb-2 text-3xl font-bold bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-900 bg-clip-text text-transparent">
                Hey, {user?.name}!
              </h1>
              <p className="text-gray-600">
                Start a continuous conversation with your voice agent
              </p>
            </div>

            <ContinuousVoiceInterface
              userId={user?.id || generateUUID()}
              onTranscription={handleTranscription}
              onResponse={handleResponse}
              onError={handleError}
              onConnectionChange={handleConnectionChange}
              onVoiceStateChange={handleVoiceStateChange}
            />

            {/* Conversation History */}
            {conversationHistory.length > 0 && (
              <Card className="w-full max-w-md p-4 border-0 shadow-lg shadow-blue-100/50 bg-white/80 backdrop-blur">
                <h3 className="mb-3 text-sm font-semibold text-gray-900">Recent Conversation</h3>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {conversationHistory.slice(-5).map((entry) => (
                    <div key={entry.id} className="text-xs p-2 rounded-lg hover:bg-gray-50 transition-colors">
                      <span className={cn(
                        "font-semibold px-2 py-1 rounded text-xs",
                        entry.type === 'user'
                          ? "bg-blue-100 text-blue-700"
                          : "bg-green-100 text-green-700"
                      )}>
                        {entry.type === 'user' ? 'You' : 'Agent'}
                      </span>
                      <span className="ml-2 text-gray-700">{entry.text}</span>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* Right Column - Quick Commands, News & Watchlist */}
          <div className="space-y-6">
            <Card className="p-6 border-0 shadow-lg shadow-blue-100/50 bg-white/80 backdrop-blur">
              <h3 className="mb-4 font-semibold text-gray-900">Quick Commands</h3>
              <QuickCommands onCommand={handleQuickCommand} />
            </Card>

            <WatchlistCard />
          </div>
        </div>

        {/* Full Width Section - Watchlist Stock News */}
        {watchlistSymbols.length > 0 && (
          <div className="mt-6">
            <WatchlistNews
              symbols={watchlistSymbols}
              newsPerStock={5}
            />
          </div>
        )}
      </main>

      {/* Log Viewer (bottom right corner) */}
      <LogViewer />
    </div>
  );
}
