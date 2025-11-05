"""
Watchlist management tools with Supabase integration.

Handles:
- add SYMBOL to watchlist
- remove SYMBOL from watchlist
- view/show watchlist

Stores watchlist in Supabase users.watchlist_stocks column.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


async def add_to_watchlist(user_id: str, symbols: List[str], notes: str = "", db_manager=None) -> Dict:
    """Add symbol(s) to user's watchlist in Supabase.

    Args:
        user_id: User UUID
        symbols: List of ticker symbols to add
        notes: Optional notes (currently not stored, for future use)
        db_manager: DatabaseManager instance

    Returns:
        Dict with success status and message
    """
    if not symbols:
        return {"success": False, "message": "No symbols provided", "watchlist": []}

    if not db_manager:
        from ...database import get_database
        db_manager = await get_database()

    try:
        # Get current watchlist
        current_watchlist = await db_manager.get_user_watchlist(user_id)

        # Determine which symbols to add
        symbols_upper = [s.upper() for s in symbols]
        new_symbols = [s for s in symbols_upper if s not in current_watchlist]
        already_exists = [s for s in symbols_upper if s in current_watchlist]

        if new_symbols:
            # Add new symbols to watchlist
            updated_watchlist = current_watchlist + new_symbols
            success = await db_manager.update_user_watchlist(user_id, updated_watchlist)

            if not success:
                return {
                    "success": False,
                    "message": "Failed to update watchlist in database.",
                    "watchlist": current_watchlist
                }

            logger.info(f"✅ Added {new_symbols} to watchlist for user {user_id[:8]}...")

            # Build response message
            message = f"Added {', '.join(new_symbols)} to your watchlist."
            if already_exists:
                message += f" {', '.join(already_exists)} {'is' if len(already_exists) == 1 else 'are'} already in your watchlist."

            return {
                "success": True,
                "message": message,
                "watchlist": updated_watchlist,
                "added": new_symbols,
                "already_exists": already_exists
            }
        else:
            # All symbols already exist
            message = f"{', '.join(already_exists)} {'is' if len(already_exists) == 1 else 'are'} already in your watchlist."
            return {
                "success": False,
                "message": message,
                "watchlist": current_watchlist,
                "added": [],
                "already_exists": already_exists
            }

    except Exception as e:
        logger.error(f"❌ Error adding to watchlist: {e}")
        return {
            "success": False,
            "message": f"Error adding to watchlist: {str(e)}",
            "watchlist": []
        }


async def remove_from_watchlist(user_id: str, symbols: List[str], db_manager=None) -> Dict:
    """Remove symbol(s) from user's watchlist in Supabase.

    Args:
        user_id: User UUID
        symbols: List of ticker symbols to remove
        db_manager: DatabaseManager instance

    Returns:
        Dict with success status and message
    """
    if not symbols:
        return {"success": False, "message": "No symbols provided", "watchlist": []}

    if not db_manager:
        from ...database import get_database
        db_manager = await get_database()

    try:
        # Get current watchlist
        current_watchlist = await db_manager.get_user_watchlist(user_id)

        # Determine which symbols to remove
        symbols_upper = [s.upper() for s in symbols]
        removed = [s for s in symbols_upper if s in current_watchlist]
        not_found = [s for s in symbols_upper if s not in current_watchlist]

        if removed:
            # Remove symbols from watchlist
            updated_watchlist = [s for s in current_watchlist if s not in symbols_upper]
            success = await db_manager.update_user_watchlist(user_id, updated_watchlist)

            if not success:
                return {
                    "success": False,
                    "message": "Failed to update watchlist in database.",
                    "watchlist": current_watchlist
                }

            logger.info(f"✅ Removed {removed} from watchlist for user {user_id[:8]}...")

            # Build response message
            message = f"Removed {', '.join(removed)} from your watchlist."
            if not_found:
                message += f" {', '.join(not_found)} {'was' if len(not_found) == 1 else 'were'} not in your watchlist."

            return {
                "success": True,
                "message": message,
                "watchlist": updated_watchlist,
                "removed": removed,
                "not_found": not_found
            }
        else:
            # No symbols found to remove
            message = f"{', '.join(not_found)} {'was' if len(not_found) == 1 else 'were'} not in your watchlist."
            return {
                "success": False,
                "message": message,
                "watchlist": current_watchlist,
                "removed": [],
                "not_found": not_found
            }

    except Exception as e:
        logger.error(f"❌ Error removing from watchlist: {e}")
        return {
            "success": False,
            "message": f"Error removing from watchlist: {str(e)}",
            "watchlist": []
        }


async def view_watchlist(user_id: str, db_manager=None) -> Dict:
    """View user's watchlist from Supabase.

    Args:
        user_id: User UUID
        db_manager: DatabaseManager instance

    Returns:
        Dict with watchlist and formatted message
    """
    if not db_manager:
        from ...database import get_database
        db_manager = await get_database()

    try:
        watchlist = await db_manager.get_user_watchlist(user_id)

        if not watchlist:
            return {
                "success": True,
                "message": "Your watchlist is empty. Add symbols with 'add SYMBOL to watchlist'.",
                "watchlist": []
            }

        # Format watchlist message
        message = f"Your watchlist ({len(watchlist)} {'symbol' if len(watchlist) == 1 else 'symbols'}): {', '.join(watchlist)}"

        logger.info(f"📋 Retrieved watchlist for user {user_id[:8]}... - {len(watchlist)} symbols")

        return {
            "success": True,
            "message": message,
            "watchlist": watchlist
        }

    except Exception as e:
        logger.error(f"❌ Error viewing watchlist: {e}")
        return {
            "success": False,
            "message": f"Error viewing watchlist: {str(e)}",
            "watchlist": []
        }


async def handle_watchlist_command(
    user_id: str,
    action: str,
    symbols: List[str] = None,
    notes: str = "",
    db_manager=None
) -> Dict:
    """Unified watchlist command handler with Supabase integration.

    Args:
        user_id: User UUID
        action: "add", "remove", or "view"
        symbols: List of symbols (required for add/remove)
        notes: Optional notes (for add action)
        db_manager: DatabaseManager instance

    Returns:
        Dict with command result
    """
    action = action.lower()

    if action == "add":
        return await add_to_watchlist(user_id, symbols or [], notes, db_manager)
    elif action == "remove":
        return await remove_from_watchlist(user_id, symbols or [], db_manager)
    elif action == "view":
        return await view_watchlist(user_id, db_manager)
    else:
        return {
            "success": False,
            "message": f"Unknown watchlist action: {action}. Use 'add', 'remove', or 'view'.",
            "watchlist": []
        }
