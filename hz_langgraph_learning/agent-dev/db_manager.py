"""
Database Manager for Market Assistant Agent

Manage watchlist and query history stored in JSON files.

Usage:
    python db_manager.py --list-watchlist
    python db_manager.py --list-queries --limit 10
    python db_manager.py --add-symbol AAPL --notes "Apple Inc"
    python db_manager.py --remove-symbol TSLA
    python db_manager.py --clear-history
    python db_manager.py --export watchlist.json
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import argparse

# Database file paths
DB_DIR = Path(__file__).parent / "memory_data"
WATCHLIST_FILE = DB_DIR / "watchlist.json"
QUERY_HISTORY_FILE = DB_DIR / "query_history.json"


def ensure_db_dir():
    """Ensure database directory exists."""
    DB_DIR.mkdir(exist_ok=True)
    if not WATCHLIST_FILE.exists():
        WATCHLIST_FILE.write_text("[]")
    if not QUERY_HISTORY_FILE.exists():
        QUERY_HISTORY_FILE.write_text("[]")


def load_watchlist() -> List[Dict]:
    """Load watchlist from JSON file."""
    ensure_db_dir()
    try:
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_watchlist(watchlist: List[Dict]):
    """Save watchlist to JSON file."""
    ensure_db_dir()
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)


def load_query_history() -> List[Dict]:
    """Load query history from JSON file."""
    ensure_db_dir()
    try:
        with open(QUERY_HISTORY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_query_history(history: List[Dict]):
    """Save query history to JSON file."""
    ensure_db_dir()
    with open(QUERY_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ====== WATCHLIST OPERATIONS ======


def list_watchlist():
    """List all symbols in watchlist."""
    watchlist = load_watchlist()

    if not watchlist:
        print("📭 Watchlist is empty")
        return

    print(f"\n📊 Watchlist ({len(watchlist)} symbols)")
    print("=" * 80)

    for item in watchlist:
        symbol = item["symbol"]
        notes = item.get("notes", "")
        added_at = item.get("added_at", "Unknown")
        alert_above = item.get("alert_price_above")
        alert_below = item.get("alert_price_below")

        print(f"\n🔹 {symbol}")
        print(f"   Added: {added_at}")
        if notes:
            print(f"   Notes: {notes}")
        if alert_above:
            print(f"   Alert if above: ${alert_above}")
        if alert_below:
            print(f"   Alert if below: ${alert_below}")

    print("\n" + "=" * 80)


def add_to_watchlist(
    symbol: str,
    notes: str = "",
    alert_above: Optional[float] = None,
    alert_below: Optional[float] = None,
):
    """Add symbol to watchlist."""
    watchlist = load_watchlist()

    # Check if already exists
    for item in watchlist:
        if item["symbol"].upper() == symbol.upper():
            print(f"❌ {symbol} is already in watchlist")
            return

    # Add new entry
    new_entry = {
        "symbol": symbol.upper(),
        "added_at": datetime.utcnow().isoformat(),
        "notes": notes,
        "alert_price_above": alert_above,
        "alert_price_below": alert_below,
    }

    watchlist.append(new_entry)
    save_watchlist(watchlist)
    print(f"✅ Added {symbol} to watchlist")


def remove_from_watchlist(symbol: str):
    """Remove symbol from watchlist."""
    watchlist = load_watchlist()

    initial_len = len(watchlist)
    watchlist = [item for item in watchlist if item["symbol"].upper() != symbol.upper()]

    if len(watchlist) == initial_len:
        print(f"❌ {symbol} not found in watchlist")
        return

    save_watchlist(watchlist)
    print(f"✅ Removed {symbol} from watchlist")


def update_watchlist_alerts(
    symbol: str,
    alert_above: Optional[float] = None,
    alert_below: Optional[float] = None,
):
    """Update price alerts for a symbol."""
    watchlist = load_watchlist()

    for item in watchlist:
        if item["symbol"].upper() == symbol.upper():
            if alert_above is not None:
                item["alert_price_above"] = alert_above
            if alert_below is not None:
                item["alert_price_below"] = alert_below
            save_watchlist(watchlist)
            print(f"✅ Updated alerts for {symbol}")
            return

    print(f"❌ {symbol} not found in watchlist")


def clear_watchlist():
    """Clear all symbols from watchlist."""
    save_watchlist([])
    print("✅ Watchlist cleared")


# ====== QUERY HISTORY OPERATIONS ======


def list_query_history(limit: int = 10):
    """List recent query history."""
    history = load_query_history()

    if not history:
        print("📭 Query history is empty")
        return

    # Get most recent queries
    recent = history[-limit:][::-1]  # Reverse to show newest first

    print(f"\n📜 Query History (showing {len(recent)} of {len(history)} queries)")
    print("=" * 80)

    for i, query in enumerate(recent, 1):
        timestamp = query.get("timestamp", "Unknown")
        query_text = query.get("query", "")
        intent = query.get("intent", "unknown")
        symbols = query.get("symbols", [])
        memory_id = query.get("memory_id", "")

        print(f"\n{i}. [{timestamp}]")
        print(f"   Query: {query_text}")
        print(f"   Intent: {intent}")
        if symbols:
            print(f"   Symbols: {', '.join(symbols)}")
        print(f"   Memory ID: {memory_id}")

    print("\n" + "=" * 80)


def search_query_history(keyword: str):
    """Search query history by keyword."""
    history = load_query_history()

    matches = [
        q for q in history
        if keyword.lower() in q.get("query", "").lower()
        or keyword.upper() in [s.upper() for s in q.get("symbols", [])]
    ]

    if not matches:
        print(f"No queries found matching '{keyword}'")
        return

    print(f"\n🔍 Found {len(matches)} queries matching '{keyword}'")
    print("=" * 80)

    for i, query in enumerate(matches, 1):
        print(f"\n{i}. {query.get('query', '')}")
        print(f"   Time: {query.get('timestamp', 'Unknown')}")
        print(f"   Symbols: {', '.join(query.get('symbols', []))}")

    print("\n" + "=" * 80)


def clear_query_history():
    """Clear all query history."""
    save_query_history([])
    print("✅ Query history cleared")


# ====== EXPORT/IMPORT ======


def export_database(output_file: str):
    """Export entire database to JSON file."""
    data = {
        "watchlist": load_watchlist(),
        "query_history": load_query_history(),
        "exported_at": datetime.utcnow().isoformat(),
    }

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Database exported to {output_file}")


def import_database(input_file: str):
    """Import database from JSON file."""
    with open(input_file, "r") as f:
        data = json.load(f)

    if "watchlist" in data:
        save_watchlist(data["watchlist"])
        print(f"✅ Imported {len(data['watchlist'])} watchlist items")

    if "query_history" in data:
        save_query_history(data["query_history"])
        print(f"✅ Imported {len(data['query_history'])} query history items")


def show_stats():
    """Show database statistics."""
    watchlist = load_watchlist()
    history = load_query_history()

    print("\n📊 Database Statistics")
    print("=" * 80)
    print(f"Watchlist symbols: {len(watchlist)}")
    print(f"Query history entries: {len(history)}")

    if watchlist:
        alerts_set = sum(1 for item in watchlist if item.get("alert_price_above") or item.get("alert_price_below"))
        print(f"Symbols with alerts: {alerts_set}")

    if history:
        recent_date = history[-1].get("timestamp", "Unknown")
        print(f"Most recent query: {recent_date}")

        # Count by intent
        from collections import Counter
        intent_counts = Counter(q.get("intent", "unknown") for q in history)
        print("\nQueries by intent:")
        for intent, count in intent_counts.most_common():
            print(f"  - {intent}: {count}")

    print("=" * 80)


# ====== CLI ======


def main():
    parser = argparse.ArgumentParser(description="Market Agent Database Manager")

    # Watchlist operations
    parser.add_argument("--list-watchlist", action="store_true", help="List all watchlist symbols")
    parser.add_argument("--add-symbol", type=str, help="Add symbol to watchlist")
    parser.add_argument("--notes", type=str, default="", help="Notes for the symbol")
    parser.add_argument("--alert-above", type=float, help="Price alert threshold (above)")
    parser.add_argument("--alert-below", type=float, help="Price alert threshold (below)")
    parser.add_argument("--remove-symbol", type=str, help="Remove symbol from watchlist")
    parser.add_argument("--update-alerts", type=str, help="Update alerts for symbol")
    parser.add_argument("--clear-watchlist", action="store_true", help="Clear all watchlist symbols")

    # Query history operations
    parser.add_argument("--list-queries", action="store_true", help="List query history")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of queries to show")
    parser.add_argument("--search", type=str, help="Search query history by keyword")
    parser.add_argument("--clear-history", action="store_true", help="Clear query history")

    # Export/Import
    parser.add_argument("--export", type=str, help="Export database to file")
    parser.add_argument("--import-db", type=str, help="Import database from file")

    # Stats
    parser.add_argument("--stats", action="store_true", help="Show database statistics")

    args = parser.parse_args()

    # Execute commands
    if args.list_watchlist:
        list_watchlist()
    elif args.add_symbol:
        add_to_watchlist(args.add_symbol, args.notes, args.alert_above, args.alert_below)
    elif args.remove_symbol:
        remove_from_watchlist(args.remove_symbol)
    elif args.update_alerts:
        update_watchlist_alerts(args.update_alerts, args.alert_above, args.alert_below)
    elif args.clear_watchlist:
        clear_watchlist()
    elif args.list_queries:
        list_query_history(args.limit)
    elif args.search:
        search_query_history(args.search)
    elif args.clear_history:
        clear_query_history()
    elif args.export:
        export_database(args.export)
    elif args.import_db:
        import_database(args.import_db)
    elif args.stats:
        show_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
