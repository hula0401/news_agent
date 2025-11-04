# One-Time Question Evaluation Data

Store datasets for one-time question-answer evaluation here.

Format: Each file should contain test cases for single queries (no multi-turn).

Example structure:
```json
{
  "test_cases": [
    {
      "query": "What's the price of TSLA?",
      "expected_intent": "price_check",
      "expected_symbols": ["TSLA"]
    }
  ]
}
```
