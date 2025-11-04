# Conversation Evaluation Data

Store datasets for multi-turn conversation evaluation here.

Format: Each file should contain conversation sequences.

Example structure:
```json
{
  "conversations": [
    {
      "conversation_id": "conv_001",
      "turns": [
        {
          "user": "What's TSLA price?",
          "expected_intent": "price_check"
        },
        {
          "user": "Tell me news about it",
          "expected_intent": "news_search",
          "context_required": true
        }
      ]
    }
  ]
}
```
