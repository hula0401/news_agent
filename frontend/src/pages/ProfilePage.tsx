import { useState, useEffect } from "react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Slider } from "../components/ui/slider";
import { Switch } from "../components/ui/switch";
import { InterestCard } from "../components/InterestCard";
import { ArrowLeft, Plus, TrendingUp, TrendingDown, Newspaper, DollarSign, Briefcase, Globe, Heart, Cpu, Zap, Music, Book, X } from "lucide-react";
import { useProfile } from "../lib/profile-context";
import { useAuth } from "../lib/auth-context";
import { useWatchlistPrices } from "../hooks/stocks/useWatchlistPrices";
import { getStockName } from "../mocks/stock-data";
import { Skeleton } from "../components/ui/skeleton";
const API_BASE = import.meta.env.VITE_API_URL as string | undefined;
import { toast } from "sonner@2.0.3";

interface ProfilePageProps {
  onBack: () => void;
}

export function ProfilePage({ onBack }: ProfilePageProps) {
  const { profile, updateProfile, isLoading } = useProfile();
  const { user } = useAuth();
  const [newStock, setNewStock] = useState("");
  const [localInterests, setLocalInterests] = useState(profile?.interests || {});
  const [watchlistSymbols, setWatchlistSymbols] = useState<string[]>([]);
  const [localSpeechRate, setLocalSpeechRate] = useState([profile?.settings.speechRate || 1.0]);
  const [localInterruptionSensitivity, setLocalInterruptionSensitivity] = useState([profile?.settings.interruptionSensitivity || 50]);
  const [localNotifications, setLocalNotifications] = useState(profile?.notifications || {
    marketAlerts: true,
    newsDigest: true,
    watchlistUpdates: true,
    dailyBrief: false,
  });

  // Fetch watchlist symbols from API
  useEffect(() => {
    const loadWatchlist = async () => {
      if (!user?.id || !API_BASE) return;

      try {
        const res = await fetch(`${API_BASE}/api/user/preferences?user_id=${encodeURIComponent(user.id)}`);
        if (!res.ok) {
          if (res.status === 404) {
            setWatchlistSymbols([]);
            return;
          }
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        setWatchlistSymbols(data.watchlist_stocks || []);
      } catch (error) {
        console.error('Failed to load watchlist:', error);
        setWatchlistSymbols([]);
      }
    };

    loadWatchlist();
  }, [user?.id, API_BASE]);

  useEffect(() => {
    if (profile) {
      setLocalInterests(profile.interests);
      setLocalSpeechRate([profile.settings.speechRate]);
      setLocalInterruptionSensitivity([profile.settings.interruptionSensitivity]);
      setLocalNotifications(profile.notifications);
    }
  }, [profile]);

  // Fetch prices for watchlist symbols
  const { prices, loading: pricesLoading, error: pricesError, isMarketOpen } = useWatchlistPrices(watchlistSymbols);

  const interestCategories = [
    { id: "technology", icon: Cpu, title: "Technology", description: "Tech news, AI, gadgets" },
    { id: "finance", icon: DollarSign, title: "Finance", description: "Markets, crypto, economics" },
    { id: "business", icon: Briefcase, title: "Business", description: "Corporate news, startups" },
    { id: "health", icon: Heart, title: "Health", description: "Medical, wellness, fitness" },
    { id: "entertainment", icon: Zap, title: "Entertainment", description: "Movies, TV, celebrities" },
    { id: "sports", icon: TrendingUp, title: "Sports", description: "All sports coverage" },
    { id: "science", icon: Globe, title: "Science", description: "Research, discoveries" },
    { id: "politics", icon: Newspaper, title: "Politics", description: "Government, policy" },
    { id: "music", icon: Music, title: "Music", description: "Artists, albums, concerts" },
    { id: "books", icon: Book, title: "Books", description: "Literature, authors" },
  ];

  const toggleInterest = async (id: string) => {
    const updatedInterests = { ...localInterests, [id]: !localInterests[id] };
    setLocalInterests(updatedInterests);
    // Map keyed interests -> array of topics true
    const topics = Object.entries(updatedInterests)
      .filter(([, v]) => Boolean(v))
      .map(([k]) => k);
    if (!API_BASE || !user?.id) return;
    try {
      const res = await fetch(`${API_BASE}/api/user/preferences?user_id=${encodeURIComponent(user.id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferred_topics: topics })
      });
      if (!res.ok) throw new Error('save failed');
      toast.success("Interest updated");
    } catch (error) {
      toast.error("Failed to update interest");
    }
  };

  const addStock = async () => {
    if (!newStock.trim()) return;

    const symbol = newStock.toUpperCase();

    // Check if symbol already exists
    if (watchlistSymbols.includes(symbol)) {
      toast.error("Stock already in watchlist");
      return;
    }

    const updatedSymbols = [...watchlistSymbols, symbol];
    setWatchlistSymbols(updatedSymbols);
    setNewStock("");

    // Save to backend
    if (!API_BASE || !user?.id) return;

    try {
      const res = await fetch(`${API_BASE}/api/user/preferences?user_id=${encodeURIComponent(user.id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ watchlist_stocks: updatedSymbols })
      });

      if (!res.ok) throw new Error('Failed to save');
      toast.success("Stock added to watchlist");
    } catch (error) {
      toast.error("Failed to add stock");
      // Revert on error
      setWatchlistSymbols(watchlistSymbols);
    }
  };

  const removeStock = async (symbol: string) => {
    const updatedSymbols = watchlistSymbols.filter(s => s !== symbol);
    setWatchlistSymbols(updatedSymbols);

    // Save to backend
    if (!API_BASE || !user?.id) return;

    try {
      const res = await fetch(`${API_BASE}/api/user/preferences?user_id=${encodeURIComponent(user.id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ watchlist_stocks: updatedSymbols })
      });

      if (!res.ok) throw new Error('Failed to save');
      toast.success("Stock removed from watchlist");
    } catch (error) {
      toast.error("Failed to remove stock");
      // Revert on error
      setWatchlistSymbols(watchlistSymbols);
    }
  };

  const updateSettings = async () => {
    try {
      await updateProfile({
        settings: {
          speechRate: localSpeechRate[0],
          interruptionSensitivity: localInterruptionSensitivity[0],
          voiceType: 'professional'
        }
      });
      toast.success("Settings updated");
    } catch (error) {
      toast.error("Failed to update settings");
    }
  };

  const updateNotification = async (key: string, value: boolean) => {
    const updatedNotifications = { ...localNotifications, [key]: value };
    setLocalNotifications(updatedNotifications);
    try {
      await updateProfile({ notifications: updatedNotifications });
    } catch (error) {
      toast.error("Failed to update notification");
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <p>Loading profile...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={onBack}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <h2>Profile Settings</h2>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        <Tabs defaultValue="interests" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="interests">Interests</TabsTrigger>
            <TabsTrigger value="watchlist">Watchlist</TabsTrigger>
            <TabsTrigger value="voice">Voice</TabsTrigger>
            <TabsTrigger value="notifications">Notifications</TabsTrigger>
          </TabsList>

          {/* Interests Tab */}
          <TabsContent value="interests" className="space-y-6">
            <Card className="p-6">
              <h3 className="mb-2">Your Interests</h3>
              <p className="text-muted-foreground mb-6">
                Select topics you want to hear about in your daily briefings
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {interestCategories.map((category) => (
                  <InterestCard
                    key={category.id}
                    icon={category.icon}
                    title={category.title}
                    description={category.description}
                    enabled={localInterests[category.id] || false}
                    onToggle={() => toggleInterest(category.id)}
                  />
                ))}
              </div>
            </Card>
          </TabsContent>

          {/* Watchlist Tab */}
          <TabsContent value="watchlist" className="space-y-6">
            <Card className="p-6">
              <div className="flex items-center justify-between mb-2">
                <h3>Stock Watchlist</h3>
                {isMarketOpen && (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
                    Market Open
                  </span>
                )}
              </div>
              <p className="text-muted-foreground mb-6">
                Add stocks you want to track in your voice briefings
              </p>

              <div className="flex gap-2 mb-6">
                <Input
                  placeholder="Enter stock symbol (e.g., AAPL)"
                  value={newStock}
                  onChange={(e) => setNewStock(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && addStock()}
                />
                <Button onClick={addStock}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add
                </Button>
              </div>

              <div className="space-y-3">
                {pricesLoading && watchlistSymbols.length === 0 ? (
                  <div className="space-y-3">
                    {Array.from({ length: 3 }).map((_, i) => (
                      <Skeleton key={i} className="h-20 w-full" />
                    ))}
                  </div>
                ) : watchlistSymbols.length === 0 ? (
                  <div className="text-sm text-muted-foreground text-center py-8">
                    No stocks in watchlist yet. Add one above!
                  </div>
                ) : pricesError ? (
                  <div className="text-center py-8">
                    <p className="text-sm text-red-500 mb-2">
                      Unable to load stock prices
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Please check that the backend is running
                    </p>
                    <div className="mt-4 space-y-2">
                      {watchlistSymbols.map((symbol) => (
                        <Card key={symbol} className="p-3">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-sm">{symbol}</span>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeStock(symbol)}
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>
                ) : prices.length > 0 ? (
                  prices.map((stock) => {
                    const isPositive = stock.change >= 0;
                    return (
                      <Card key={stock.symbol} className="p-4">
                        <div className="flex items-center justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-mono font-bold">{stock.symbol}</span>
                              {isPositive ? (
                                <TrendingUp className="w-4 h-4 text-green-500" />
                              ) : (
                                <TrendingDown className="w-4 h-4 text-red-500" />
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground">{getStockName(stock.symbol)}</p>
                          </div>

                          <div className="text-right">
                            <div className="font-bold mb-1">${stock.price.toFixed(2)}</div>
                            <div className={`text-sm ${isPositive ? "text-green-500" : "text-red-500"}`}>
                              {isPositive ? "+" : ""}{stock.change.toFixed(2)} ({isPositive ? "+" : ""}{stock.change_percent.toFixed(2)}%)
                            </div>
                          </div>

                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => removeStock(stock.symbol)}
                            className="shrink-0"
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      </Card>
                    );
                  })
                ) : (
                  watchlistSymbols.map((symbol) => (
                    <Card key={symbol} className="p-4">
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex-1">
                          <span className="font-mono font-bold">{symbol}</span>
                          <p className="text-sm text-muted-foreground">{getStockName(symbol)}</p>
                        </div>
                        <Skeleton className="h-12 w-32" />
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeStock(symbol)}
                          className="shrink-0"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </Card>
                  ))
                )}
              </div>
            </Card>
          </TabsContent>

          {/* Voice Settings Tab */}
          <TabsContent value="voice" className="space-y-6">
            <Card className="p-6">
              <h3 className="mb-6">Voice Settings</h3>
              
              <div className="space-y-8">
                <div>
                  <div className="flex justify-between mb-3">
                    <Label>Speech Rate</Label>
                    <span className="text-sm text-muted-foreground">{localSpeechRate[0].toFixed(1)}x</span>
                  </div>
                  <Slider
                    value={localSpeechRate}
                    onValueChange={(value) => {
                      setLocalSpeechRate(value);
                      updateSettings();
                    }}
                    min={0.5}
                    max={2.0}
                    step={0.1}
                  />
                  <p className="text-sm text-muted-foreground mt-2">
                    Adjust how fast the voice agent speaks
                  </p>
                </div>

                <div>
                  <div className="flex justify-between mb-3">
                    <Label>Interruption Sensitivity</Label>
                    <span className="text-sm text-muted-foreground">{localInterruptionSensitivity[0]}%</span>
                  </div>
                  <Slider
                    value={localInterruptionSensitivity}
                    onValueChange={(value) => {
                      setLocalInterruptionSensitivity(value);
                      updateSettings();
                    }}
                    min={0}
                    max={100}
                    step={10}
                  />
                  <p className="text-sm text-muted-foreground mt-2">
                    How easily you can interrupt the agent while it's speaking
                  </p>
                </div>

                <div>
                  <Label className="mb-3 block">Voice Type</Label>
                  <div className="grid grid-cols-2 gap-3">
                    <Button variant="outline" className="justify-start">
                      Professional (Default)
                    </Button>
                    <Button variant="outline" className="justify-start">
                      Casual
                    </Button>
                    <Button variant="outline" className="justify-start">
                      Energetic
                    </Button>
                    <Button variant="outline" className="justify-start">
                      Calm
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>

          {/* Notifications Tab */}
          <TabsContent value="notifications" className="space-y-6">
            <Card className="p-6">
              <h3 className="mb-2">Notification Preferences</h3>
              <p className="text-muted-foreground mb-6">
                Choose what notifications you'd like to receive
              </p>

              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b">
                  <div>
                    <p>Market Alerts</p>
                    <p className="text-sm text-muted-foreground">
                      Significant market movements and events
                    </p>
                  </div>
                  <Switch
                    checked={localNotifications.marketAlerts}
                    onCheckedChange={(checked) => updateNotification('marketAlerts', checked)}
                  />
                </div>

                <div className="flex items-center justify-between py-3 border-b">
                  <div>
                    <p>News Digest</p>
                    <p className="text-sm text-muted-foreground">
                      Daily summary of news in your interests
                    </p>
                  </div>
                  <Switch
                    checked={localNotifications.newsDigest}
                    onCheckedChange={(checked) => updateNotification('newsDigest', checked)}
                  />
                </div>

                <div className="flex items-center justify-between py-3 border-b">
                  <div>
                    <p>Watchlist Updates</p>
                    <p className="text-sm text-muted-foreground">
                      Price alerts for your watchlist stocks
                    </p>
                  </div>
                  <Switch
                    checked={localNotifications.watchlistUpdates}
                    onCheckedChange={(checked) => updateNotification('watchlistUpdates', checked)}
                  />
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <p>Daily Brief Reminder</p>
                    <p className="text-sm text-muted-foreground">
                      Reminder to get your daily briefing
                    </p>
                  </div>
                  <Switch
                    checked={localNotifications.dailyBrief}
                    onCheckedChange={(checked) => updateNotification('dailyBrief', checked)}
                  />
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
