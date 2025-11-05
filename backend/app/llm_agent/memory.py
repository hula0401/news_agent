"""
Memory management for Market Assistant Agent.

Provides:
1. Watchlist: User's tracked stocks
2. Query History: Recent queries with timestamps
3. Preferences: User settings
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)

# Memory file paths
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory_data")
WATCHLIST_FILE = os.path.join(MEMORY_DIR, "watchlist.json")
QUERY_HISTORY_FILE = os.path.join(MEMORY_DIR, "query_history.json")
PREFERENCES_FILE = os.path.join(MEMORY_DIR, "preferences.json")

# Ensure memory directory exists
os.makedirs(MEMORY_DIR, exist_ok=True)


# ====== WATCHLIST MANAGEMENT ======
@dataclass
class WatchlistItem:
    """Single stock in the watchlist."""

    symbol: str
    added_at: str
    notes: str = ""
    alert_price_above: Optional[float] = None
    alert_price_below: Optional[float] = None


class Watchlist:
    """Manage user's stock watchlist."""

    def __init__(self, filepath: str = WATCHLIST_FILE):
        self.filepath = filepath
        self.items: List[WatchlistItem] = []
        self.load()

    def load(self):
        """Load watchlist from file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    self.items = [WatchlistItem(**item) for item in data]
                logger.info(f"Loaded {len(self.items)} items from watchlist")
            except Exception as e:
                logger.error(f"Error loading watchlist: {e}")
                self.items = []
        else:
            self.items = []

    def save(self):
        """Save watchlist to file."""
        try:
            with open(self.filepath, "w") as f:
                data = [asdict(item) for item in self.items]
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.items)} items to watchlist")
        except Exception as e:
            logger.error(f"Error saving watchlist: {e}")

    def add(self, symbol: str, notes: str = "", alert_above: Optional[float] = None, alert_below: Optional[float] = None) -> bool:
        """
        Add a stock to the watchlist.

        Args:
            symbol: Ticker symbol (e.g., "TSLA")
            notes: Optional notes about the stock
            alert_above: Price alert threshold (notify if price goes above)
            alert_below: Price alert threshold (notify if price goes below)

        Returns:
            True if added, False if already exists
        """
        symbol = symbol.upper()

        # Check if already exists
        if any(item.symbol == symbol for item in self.items):
            logger.warning(f"{symbol} already in watchlist")
            return False

        item = WatchlistItem(
            symbol=symbol,
            added_at=datetime.utcnow().isoformat(),
            notes=notes,
            alert_price_above=alert_above,
            alert_price_below=alert_below,
        )

        self.items.append(item)
        self.save()
        logger.info(f"Added {symbol} to watchlist")
        return True

    def remove(self, symbol: str) -> bool:
        """
        Remove a stock from the watchlist.

        Returns:
            True if removed, False if not found
        """
        symbol = symbol.upper()
        original_len = len(self.items)
        self.items = [item for item in self.items if item.symbol != symbol]

        if len(self.items) < original_len:
            self.save()
            logger.info(f"Removed {symbol} from watchlist")
            return True
        else:
            logger.warning(f"{symbol} not found in watchlist")
            return False

    def get_all(self) -> List[WatchlistItem]:
        """Get all watchlist items."""
        return self.items

    def get(self, symbol: str) -> Optional[WatchlistItem]:
        """Get a specific watchlist item."""
        symbol = symbol.upper()
        for item in self.items:
            if item.symbol == symbol:
                return item
        return None

    def update_notes(self, symbol: str, notes: str) -> bool:
        """Update notes for a watchlist item."""
        item = self.get(symbol)
        if item:
            item.notes = notes
            self.save()
            logger.info(f"Updated notes for {symbol}")
            return True
        return False

    def update_alerts(self, symbol: str, alert_above: Optional[float] = None, alert_below: Optional[float] = None) -> bool:
        """Update price alerts for a watchlist item."""
        item = self.get(symbol)
        if item:
            item.alert_price_above = alert_above
            item.alert_price_below = alert_below
            self.save()
            logger.info(f"Updated alerts for {symbol}")
            return True
        return False

    def check_alerts(self, symbol: str, current_price: float) -> List[str]:
        """
        Check if any price alerts are triggered.

        Returns:
            List of alert messages
        """
        item = self.get(symbol)
        if not item:
            return []

        alerts = []
        if item.alert_price_above and current_price >= item.alert_price_above:
            alerts.append(f"🔔 {symbol} crossed above ${item.alert_price_above} (current: ${current_price})")

        if item.alert_price_below and current_price <= item.alert_price_below:
            alerts.append(f"🔔 {symbol} dropped below ${item.alert_price_below} (current: ${current_price})")

        return alerts

    def to_dict(self) -> List[Dict]:
        """Export watchlist as dict for JSON serialization."""
        return [asdict(item) for item in self.items]


# ====== QUERY HISTORY ======
@dataclass
class QueryRecord:
    """Record of a user query."""

    query: str
    intent: str
    symbols: List[str]
    timestamp: str
    summary: str = ""
    memory_id: Optional[str] = None


class QueryHistory:
    """Manage query history."""

    def __init__(self, filepath: str = QUERY_HISTORY_FILE, max_records: int = 100):
        self.filepath = filepath
        self.max_records = max_records
        self.records: List[QueryRecord] = []
        self.load()

    def load(self):
        """Load query history from file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    content = f.read().strip()
                    if not content:  # Empty file
                        self.records = []
                        logger.info("Query history file is empty, starting fresh")
                        return
                    data = json.loads(content)
                    self.records = [QueryRecord(**record) for record in data]
                logger.info(f"Loaded {len(self.records)} query records")
            except Exception as e:
                logger.error(f"Error loading query history: {e}")
                self.records = []
        else:
            self.records = []

    def save(self):
        """Save query history to file."""
        try:
            # Keep only the most recent records
            records_to_save = self.records[-self.max_records:]
            with open(self.filepath, "w") as f:
                data = [asdict(record) for record in records_to_save]
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(records_to_save)} query records")
        except Exception as e:
            logger.error(f"Error saving query history: {e}")

    def add(self, query: str, intent: str, symbols: List[str], summary: str = "", memory_id: Optional[str] = None):
        """Add a query record."""
        record = QueryRecord(
            query=query,
            intent=intent,
            symbols=symbols,
            timestamp=datetime.utcnow().isoformat(),
            summary=summary,
            memory_id=memory_id,
        )
        self.records.append(record)
        self.save()

        # Log what was saved to memory
        logger.info(f"💾 Saved to memory:")
        logger.info(f"   Query: {query}")
        logger.info(f"   Intent: {intent}")
        logger.info(f"   Symbols: {symbols}")
        logger.info(f"   Summary: {summary[:100]}..." if len(summary) > 100 else f"   Summary: {summary}")
        logger.info(f"   Memory ID: {memory_id}")

    def get_recent(self, limit: int = 10) -> List[QueryRecord]:
        """Get recent queries."""
        return self.records[-limit:]

    def get_by_symbol(self, symbol: str, limit: int = 10) -> List[QueryRecord]:
        """Get queries related to a specific symbol."""
        symbol = symbol.upper()
        matching = [record for record in self.records if symbol in [s.upper() for s in record.symbols]]
        return matching[-limit:]


# ====== USER PREFERENCES ======
@dataclass
class UserPreferences:
    """User preferences and settings."""

    default_timeframe: str = "1d"
    enable_caching: bool = True
    timeout_seconds: float = 10.0
    max_news_items: int = 5
    preferred_sources: List[str] = field(default_factory=lambda: ["alphavantage", "polygon", "tavily"])


class PreferencesManager:
    """Manage user preferences."""

    def __init__(self, filepath: str = PREFERENCES_FILE):
        self.filepath = filepath
        self.preferences: UserPreferences = UserPreferences()
        self.load()

    def load(self):
        """Load preferences from file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    self.preferences = UserPreferences(**data)
                logger.info("Loaded user preferences")
            except Exception as e:
                logger.error(f"Error loading preferences: {e}")
                self.preferences = UserPreferences()
        else:
            self.preferences = UserPreferences()

    def save(self):
        """Save preferences to file."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(asdict(self.preferences), f, indent=2)
            logger.info("Saved user preferences")
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")

    def update(self, **kwargs):
        """Update preferences."""
        for key, value in kwargs.items():
            if hasattr(self.preferences, key):
                setattr(self.preferences, key, value)
        self.save()


# ====== GLOBAL INSTANCES ======
watchlist = Watchlist()
query_history = QueryHistory()
preferences_manager = PreferencesManager()


# ====== HELPER FUNCTIONS ======
def add_to_watchlist(symbol: str, notes: str = "", alert_above: Optional[float] = None, alert_below: Optional[float] = None) -> bool:
    """Convenience function to add to watchlist."""
    return watchlist.add(symbol, notes, alert_above, alert_below)


def remove_from_watchlist(symbol: str) -> bool:
    """Convenience function to remove from watchlist."""
    return watchlist.remove(symbol)


def get_watchlist() -> List[WatchlistItem]:
    """Convenience function to get all watchlist items."""
    return watchlist.get_all()


def save_query(query: str, intent: str, symbols: List[str], summary: str = "", memory_id: Optional[str] = None):
    """Convenience function to save query to history."""
    query_history.add(query, intent, symbols, summary, memory_id)


def get_recent_queries(limit: int = 10) -> List[QueryRecord]:
    """Convenience function to get recent queries."""
    return query_history.get_recent(limit)
