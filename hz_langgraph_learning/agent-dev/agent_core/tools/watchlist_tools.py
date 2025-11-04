"""
Watchlist management tools for explicit user commands.

Handles:
- add SYMBOL to watchlist
- remove SYMBOL from watchlist
- view/show watchlist

These are EXPLICIT commands, not automatic tracking.
"""

import logging
from typing import Dict, List
from agent_core.memory import watchlist

logger = logging.getLogger(__name__)


def add_to_watchlist(symbols: List[str], notes: str = "") -> Dict:
    """
    Add symbol(s) to watchlist.

    Args:
        symbols: List of ticker symbols to add
        notes: Optional notes about the symbols

    Returns:
        Dict with success status and message
    """
    if not symbols:
        return {"success": False, "message": "No symbols provided"}

    added = []
    already_exists = []

    for symbol in symbols:
        symbol = symbol.upper()
        if watchlist.add(symbol, notes=notes):
            added.append(symbol)
            logger.info(f"✅ Added {symbol} to watchlist")
        else:
            already_exists.append(symbol)
            logger.info(f"⚠️  {symbol} already in watchlist")

    # Build response message
    message = ""
    if added:
        message += f"Added {', '.join(added)} to your watchlist. "
    if already_exists:
        message += f"{', '.join(already_exists)} {'is' if len(already_exists) == 1 else 'are'} already in your watchlist."

    return {
        "success": len(added) > 0,
        "message": message.strip(),
        "added": added,
        "already_exists": already_exists
    }


def remove_from_watchlist(symbols: List[str]) -> Dict:
    """
    Remove symbol(s) from watchlist.

    Args:
        symbols: List of ticker symbols to remove

    Returns:
        Dict with success status and message
    """
    if not symbols:
        return {"success": False, "message": "No symbols provided"}

    removed = []
    not_found = []

    for symbol in symbols:
        symbol = symbol.upper()
        if watchlist.remove(symbol):
            removed.append(symbol)
            logger.info(f"✅ Removed {symbol} from watchlist")
        else:
            not_found.append(symbol)
            logger.info(f"⚠️  {symbol} not found in watchlist")

    # Build response message
    message = ""
    if removed:
        message += f"Removed {', '.join(removed)} from your watchlist. "
    if not_found:
        message += f"{', '.join(not_found)} {'was' if len(not_found) == 1 else 'were'} not in your watchlist."

    return {
        "success": len(removed) > 0,
        "message": message.strip(),
        "removed": removed,
        "not_found": not_found
    }


def view_watchlist() -> Dict:
    """
    View all symbols in watchlist.

    Returns:
        Dict with watchlist items and formatted message
    """
    items = watchlist.get_all()

    if not items:
        return {
            "success": True,
            "message": "Your watchlist is empty. Add symbols with 'add SYMBOL to watchlist'.",
            "watchlist": []
        }

    # Format watchlist message
    message = f"Your watchlist ({len(items)} {'symbol' if len(items) == 1 else 'symbols'}):\n"
    watchlist_data = []

    for item in items:
        message += f"- {item.symbol}"
        if item.notes:
            message += f" ({item.notes})"
        message += "\n"

        watchlist_data.append({
            "symbol": item.symbol,
            "added_at": item.added_at,
            "notes": item.notes,
            "alert_price_above": item.alert_price_above,
            "alert_price_below": item.alert_price_below
        })

    return {
        "success": True,
        "message": message.strip(),
        "watchlist": watchlist_data
    }


def handle_watchlist_command(action: str, symbols: List[str] = None, notes: str = "") -> Dict:
    """
    Unified watchlist command handler.

    Args:
        action: "add", "remove", or "view"
        symbols: List of symbols (required for add/remove)
        notes: Optional notes (for add action)

    Returns:
        Dict with command result
    """
    action = action.lower()

    if action == "add":
        return add_to_watchlist(symbols or [], notes)
    elif action == "remove":
        return remove_from_watchlist(symbols or [])
    elif action == "view":
        return view_watchlist()
    else:
        return {
            "success": False,
            "message": f"Unknown watchlist action: {action}. Use 'add', 'remove', or 'view'."
        }
