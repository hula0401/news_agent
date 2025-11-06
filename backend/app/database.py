"""Database connection and management for Supabase."""
import asyncio
from typing import Optional, Dict, Any, List
from supabase import create_client
from .config import get_settings

settings = get_settings()

class DatabaseManager:
    """Supabase database manager."""
    
    def __init__(self):
        self.client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Supabase client."""
        if self._initialized:
            return

        try:
            # Use service_role key for backend operations (bypasses RLS)
            # This is required for operations like updating user_notes with RLS enabled
            key = settings.supabase_service_key or settings.supabase_key
            self.client = create_client(
                settings.supabase_url,
                key
            )
            self._initialized = True
            print("✅ Supabase client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            if not self.client:
                await self.initialize()
            
            # Simple query to test connection
            result = self.client.table('users').select('id').limit(1).execute()
            return True
        except Exception as e:
            print(f"❌ Database health check failed: {e}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            result = self.client.table('users').select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error getting user {user_id}: {e}")
            return None
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new user."""
        try:
            result = self.client.table('users').insert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return None
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences stored directly on users table.

        Only columns that exist on users are updated (preferred_topics, watchlist_stocks).
        """
        try:
            update_payload: Dict[str, Any] = {}
            if 'preferred_topics' in preferences:
                update_payload['preferred_topics'] = preferences['preferred_topics']
            if 'watchlist_stocks' in preferences:
                update_payload['watchlist_stocks'] = preferences['watchlist_stocks']
            if not update_payload:
                return True
            result = (
                self.client
                .table('users')
                .update(update_payload)
                .eq('id', user_id)
                .execute()
            )
            return result.data is not None
        except Exception as e:
            print(f"❌ Error updating user preferences: {e}")
            return False
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences stored on users table."""
        try:
            # Wrap synchronous Supabase call in asyncio.to_thread
            def _fetch():
                return (
                    self.client
                    .table('users')
                    .select('preferred_topics, watchlist_stocks')
                    .eq('id', user_id)
                    .execute()
                )
            
            result = await asyncio.to_thread(_fetch)
            
            if result.data:
                row = result.data[0]
                return {
                    'preferred_topics': row.get('preferred_topics') or [],
                    'watchlist_stocks': row.get('watchlist_stocks') or [],
                }
            return None
        except Exception as e:
            print(f"❌ Error getting user preferences: {e}")
            return None
    
    async def create_conversation_session(self, user_id: str, session_id: str = None) -> Optional[Dict[str, Any]]:
        """Create new conversation session with required session_id."""
        import uuid
        from datetime import datetime

        try:
            if not session_id:
                session_id = str(uuid.uuid4())

            session_data = {
                'session_id': session_id,  # REQUIRED field
                'user_id': user_id,
                'session_start': datetime.utcnow().isoformat(),
                'started_at': datetime.utcnow().isoformat(),
                'is_active': True,
                'metadata': {}
            }
            result = self.client.table('conversation_sessions').insert(session_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error creating conversation session: {e}")
            return None
    
    async def add_conversation_message(self, session_id: str, user_id: str,
                                       role: str, content: str,
                                       metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Add message to conversation using 'role' column (user|agent|system)."""
        try:
            message_data = {
                'session_id': session_id,
                'user_id': user_id,
                'role': role,
                'content': content,
                'metadata': metadata or {}
            }
            result = self.client.table('conversation_messages').insert(message_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error adding conversation message: {e}")
            return None
    
    async def get_conversation_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation messages for a session."""
        try:
            result = self.client.table('conversation_messages').select('*').eq('session_id', session_id).order('created_at', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"❌ Error getting conversation messages: {e}")
            return []
    
    async def get_latest_news(self, topics: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get latest news articles."""
        try:
            query = self.client.table('news_articles').select('*, news_sources(*)').order('published_at', desc=True).limit(limit)
            
            if topics:
                query = query.overlaps('topics', topics)
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            print(f"❌ Error getting latest news: {e}")
            return []
    
    async def search_news(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search news articles."""
        try:
            result = self.client.table('news_articles').select('*, news_sources(*)').text_search('title,summary', query).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"❌ Error searching news: {e}")
            return []
    
    async def get_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get stock data for symbol."""
        try:
            result = self.client.table('stock_data').select('*').eq('symbol', symbol.upper()).order('last_updated', desc=True).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error getting stock data for {symbol}: {e}")
            return None
    
    async def track_user_interaction(self, user_id: str, interaction_type: str,
                                   target_content: str = None, success: bool = True,
                                   response_time_ms: int = None) -> bool:
        """Track user interaction for analytics."""
        try:
            interaction_data = {
                'user_id': user_id,
                'interaction_type': interaction_type,
                'target_content': target_content,
                'success': success,
                'response_time_ms': response_time_ms
            }
            result = self.client.table('user_interactions').insert(interaction_data).execute()
            return bool(result.data)
        except Exception as e:
            print(f"❌ Error tracking user interaction: {e}")
            return False

    async def get_voice_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get voice settings for a user."""
        try:
            def _fetch():
                return (
                    self.client
                    .table('voice_settings')
                    .select('*')
                    .eq('user_id', user_id)
                    .execute()
                )

            result = await asyncio.to_thread(_fetch)

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            print(f"❌ Error getting voice settings: {e}")
            return None

    async def save_voice_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """Save or update voice settings for a user."""
        try:
            def _upsert():
                return (
                    self.client
                    .table('voice_settings')
                    .upsert(settings, on_conflict='user_id')
                    .execute()
                )

            result = await asyncio.to_thread(_upsert)
            return bool(result.data)
        except Exception as e:
            print(f"❌ Error saving voice settings: {e}")
            return False

    # ====== USER NOTES METHODS (Long-Term Memory) ======

    async def get_user_notes(self, user_id: str) -> Optional[Dict[str, str]]:
        """Get user's long-term memory key notes.

        Args:
            user_id: User UUID

        Returns:
            Dict with category-based notes like:
            {
                "stocks": "Seeking opportunities in technology and AI",
                "investment": "Researching nuclear energy private companies"
            }
        """
        try:
            def _fetch():
                return (
                    self.client
                    .table('user_notes')
                    .select('key_notes')
                    .eq('user_id', user_id)
                    .execute()
                )

            result = await asyncio.to_thread(_fetch)

            if result.data and len(result.data) > 0:
                return result.data[0].get('key_notes', {})
            return {}
        except Exception as e:
            print(f"❌ Error getting user notes for {user_id}: {e}")
            return {}

    async def upsert_user_notes(self, user_id: str, key_notes: Dict[str, str]) -> bool:
        """Create or update user's long-term memory key notes.

        Args:
            user_id: User UUID
            key_notes: Category-based notes dict

        Returns:
            True if successful, False otherwise

        Note:
            Requires unique constraint on user_id column.
            Run: ALTER TABLE user_notes ADD CONSTRAINT user_notes_user_id_unique UNIQUE (user_id);
        """
        try:
            from datetime import datetime

            def _upsert():
                return (
                    self.client
                    .table('user_notes')
                    .upsert({
                        'user_id': user_id,
                        'key_notes': key_notes,
                        'updated_time': datetime.utcnow().isoformat()
                    }, on_conflict='user_id')
                    .execute()
                )

            result = await asyncio.to_thread(_upsert)
            return bool(result.data)
        except Exception as e:
            print(f"❌ Error upserting user notes for {user_id}: {e}")
            return False

    # ====== WATCHLIST METHODS ======

    async def get_user_watchlist(self, user_id: str) -> List[str]:
        """Get user's watchlist stocks.

        Args:
            user_id: User UUID

        Returns:
            List of stock symbols like ["AAPL", "GOOGL", "META"]
        """
        try:
            def _fetch():
                return (
                    self.client
                    .table('users')
                    .select('watchlist_stocks')
                    .eq('id', user_id)
                    .execute()
                )

            result = await asyncio.to_thread(_fetch)

            if result.data and len(result.data) > 0:
                return result.data[0].get('watchlist_stocks', [])
            return []
        except Exception as e:
            print(f"❌ Error getting watchlist for {user_id}: {e}")
            return []

    async def update_user_watchlist(self, user_id: str, watchlist: List[str]) -> bool:
        """Update user's watchlist stocks.

        Args:
            user_id: User UUID
            watchlist: List of stock symbols

        Returns:
            True if successful, False otherwise
        """
        try:
            def _update():
                return (
                    self.client
                    .table('users')
                    .update({'watchlist_stocks': watchlist})
                    .eq('id', user_id)
                    .execute()
                )

            result = await asyncio.to_thread(_update)
            return bool(result.data)
        except Exception as e:
            print(f"❌ Error updating watchlist for {user_id}: {e}")
            return False

    async def delete_voice_settings(self, user_id: str) -> bool:
        """Delete voice settings for a user (reset to defaults)."""
        try:
            def _delete():
                return (
                    self.client
                    .table('voice_settings')
                    .delete()
                    .eq('user_id', user_id)
                    .execute()
                )

            result = await asyncio.to_thread(_delete)
            return True
        except Exception as e:
            print(f"❌ Error deleting voice settings: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


async def get_database() -> DatabaseManager:
    """Get database manager instance."""
    if not db_manager._initialized:
        await db_manager.initialize()
    return db_manager
