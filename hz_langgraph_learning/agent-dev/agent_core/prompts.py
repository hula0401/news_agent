"""
Concise system prompts for Market Assistant Agent.
"""

# ====== GENERAL SYSTEM PROMPT ======
GENERAL_SYSTEM_PROMPT = """You are a market analyst assistant with real-time data access.

Capabilities: Stock prices (yfinance, Alpha Vantage, Polygon), financial news (AlphaVantage, Tavily), trend analysis.

Guidelines:
- Base insights on data, never speculate
- Cite sources for news
- Use chat history for context in multi-turn conversations
- Voice mode: conversational, natural language
- Text mode: structured markdown with headers/bullets"""


# ====== CHAT HISTORY FORMATTER ======
def format_chat_history(chat_history: list) -> str:
    """Format chat history for inclusion in prompts.

    Handles both ChatMessage objects and dicts (LangGraph serialization).
    """
    if not chat_history:
        return "[No previous conversation]"

    formatted = []
    for msg in chat_history[-5:]:  # Last 5 messages only
        # Handle both ChatMessage objects and dicts
        if isinstance(msg, dict):
            role = "Human" if msg.get("role") == "user" else "Agent"
            content = msg.get("content", "")
        else:
            role = "Human" if msg.role == "user" else "Agent"
            content = msg.content

        formatted.append(f"{role}: {content[:150]}")  # Limit to 150 chars per message

    return "\n".join(formatted)


# ====== INTENT ANALYZER PROMPT ======
def get_intent_analyzer_prompt(chat_history: list) -> str:
    """Get intent analyzer prompt with chat history."""
    history_str = format_chat_history(chat_history)

    return f"""Previous conversation:
{history_str}

Analyze user query and extract ALL intents as JSON array.

Intent types: price_check, news_search, market_summary, comparison, research, chat, unknown

- research: General information/research queries (not stock-specific)
  Examples: "is that related to earnings call?", "what is an earnings call?", "tell me about AI spending", "what is meta p/e ratio?"

  **For research intent, MUST extract keywords from the query:**
  - Financial metrics: "p/e", "pe", "P/E ratio", "price to earnings", "eps", "roe", "debt", "margin", "valuation", "dividend"
  - Performance: "earnings", "revenue", "profit", "growth"
  - Events: "earnings call", "quarterly report", "announcement"

  Examples:
  - "what is meta p/e ratio?" → keywords: ["P/E ratio", "price to earnings ratio", "valuation"]
  - "how was meta earning call?" → keywords: ["earnings call", "quarterly earnings", "earnings report"]
  - "tell me about google's valuation" → keywords: ["valuation", "market cap", "enterprise value"]

IMPORTANT RULES:
1. Symbol Correction: Auto-correct common mistakes
   - "GOOGLE" → ["GOOGL", "GOOG"]
   - "FACEBOOK" or "FB" → ["META"]
   - "BERKSHIRE" → ["BRK.B"]

2. Context Resolution: Use conversation history for pronouns/references
   - "What about it?" (with NVDA mentioned) → Use NVDA from context
   - "what happened?" / "what happened to it?" → news_search intent (not price_check!)
   - "why?" / "why is that?" → news_search intent

3. Intent Detection for Follow-ups:
   - "what happened" / "what happened to it" / "why" → news_search
   - "what's the price" / "how is it doing" → price_check
   - "tell me more" / "what else" → Use previous intent

Examples:
- "What's TSLA price?" → [{{"intent":"price_check","symbols":["TSLA"],"timeframe":"1d","keywords":[],"reasoning":"Direct price query"}}]
- "what happened to it?" (NVDA in history) → [{{"intent":"news_search","symbols":["NVDA"],"timeframe":"1d","keywords":[],"reasoning":"Follow-up asking for news/explanation"}}]
- "What's GOOGLE stock price?" → [{{"intent":"price_check","symbols":["GOOGL","GOOG"],"timeframe":"1d","keywords":[],"reasoning":"Corrected GOOGLE to GOOGL/GOOG"}}]
- "GLD price and news" → [{{"intent":"price_check","symbols":["GLD"],"timeframe":"1d","keywords":[]}},{{"intent":"news_search","symbols":["GLD"],"timeframe":"1d","keywords":[]}}]
- "is that related to the earnings call?" → [{{"intent":"research","symbols":[],"timeframe":"1d","keywords":["earnings call","quarterly earnings","earnings report"],"reasoning":"General research about earnings calls"}}]
- "what is meta p/e ratio?" → [{{"intent":"research","symbols":["META"],"timeframe":"1d","keywords":["P/E ratio","price to earnings ratio","valuation"],"reasoning":"Financial metric research query"}}]
- "how was meta earning call?" → [{{"intent":"research","symbols":["META"],"timeframe":"1d","keywords":["earnings call","quarterly earnings","earnings report"],"reasoning":"Earnings call research"}}]
- "what is AI spending?" → [{{"intent":"research","symbols":[],"timeframe":"1d","keywords":["AI spending","technology spending","capital expenditure"],"reasoning":"General informational query"}}]
- "Hello" → [{{"intent":"chat","symbols":[],"timeframe":"1d","keywords":[]}}]

Respond ONLY with JSON:
{{"intents": [{{"intent":"...", "symbols":["..."], "timeframe":"1d", "keywords":["..."], "reasoning":"..."}}]}}"""


# ====== RESPONSE GENERATOR PROMPT ======
def get_response_generator_prompt(
    chat_history: list,
    query: str,
    market_data: str,
    news_data: str,
    intents: str,
    output_mode: str
) -> str:
    """Get response generator prompt with all context."""
    history_str = format_chat_history(chat_history)
    mode_instruction = "Natural conversation" if output_mode == "voice" else "Structured markdown"

    return f"""Previous conversation:
{history_str}

User: {query}

Market Data:
{market_data or "None"}

News:
{news_data or "None"}

Intents: {intents}
Output: {mode_instruction}

Generate response. Reference previous context if relevant.

IMPORTANT: Respond with ONLY a valid JSON object. No markdown, no code blocks, just raw JSON.

Required JSON format:
{{"summary":"your response here","key_insights":["insight 1","insight 2"],"sentiment":"positive/negative/neutral/mixed"}}

Example response:
{{"summary":"Tesla is trading at $433.72, down 2.93%.","key_insights":["Price down 2.93%","High volume activity"],"sentiment":"negative"}}"""


# ====== CHAT-ONLY RESPONSE PROMPT ======
def get_chat_response_prompt(chat_history: list, query: str, output_mode: str) -> str:
    """Get chat response prompt."""
    history_str = format_chat_history(chat_history)

    return f"""Previous conversation:
{history_str}

User: {query}

Respond naturally ({output_mode} mode). Reference previous context if user is following up.
No JSON needed - just conversational response."""
