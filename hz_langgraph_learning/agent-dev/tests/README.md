# Tests

## Directory Structure

```
tests/
├── integration/        # Integration tests (end-to-end feature tests)
│   ├── test_checklist_parallel.py     # Multi-symbol parallel query execution
│   ├── test_memory_watchlist.py        # Long-term memory + watchlist features
│   ├── test_watchlist_quick.py         # Quick watchlist functionality test
│   └── test_tsla_multi_intent.py       # Multi-intent query handling
└── unit/               # Unit tests (individual component tests)
    └── (empty - add unit tests here)
```

## Running Tests

### All Integration Tests:
```bash
# Run all integration tests
uv run python -m pytest tests/integration/ -v

# Run specific test
uv run python tests/integration/test_checklist_parallel.py
```

### Individual Tests:

**Checklist & Parallel Execution:**
```bash
uv run python tests/integration/test_checklist_parallel.py
```
Tests:
- Multi-symbol P/E queries (META + NVDA)
- Parallel checklist execution
- Result validation

**Memory & Watchlist:**
```bash
uv run python tests/integration/test_memory_watchlist.py
```
Tests:
- Watchlist add/remove/view
- Long-term memory tracking
- User profile management

**Quick Tests:**
```bash
# Quick watchlist test
uv run python tests/integration/test_watchlist_quick.py

# Multi-intent test
uv run python tests/integration/test_tsla_multi_intent.py
```

## Test Coverage

### Integration Tests:

1. **test_checklist_parallel.py**
   - ✅ Multi-symbol queries create checklist
   - ✅ Parallel execution of research queries
   - ✅ Each symbol gets >= 5 results
   - ✅ P/E ratio extraction from web

2. **test_memory_watchlist.py**
   - ✅ Add symbols to watchlist
   - ✅ Remove symbols from watchlist
   - ✅ View watchlist
   - ✅ Long-term memory updates
   - ✅ Category-based memory structure

3. **test_tsla_multi_intent.py**
   - ✅ Multiple intents in single query
   - ✅ Intent detection accuracy
   - ✅ Response quality

## Expected Results

All tests should pass with:
- ✅ GREEN checkmarks for each test
- ✅ "TEST: PASSED" message at the end
- ⏱️ Execution time < 60s per test

## Adding New Tests

### Integration Test Template:
```python
"""Test description."""
import asyncio
from agent_core.graph import run_market_agent

async def test_feature():
    \"\"\"Test specific feature.\"\"\"
    result = await run_market_agent("your query", output_mode="text")

    # Assertions
    assert result.intent == "expected_intent"
    assert len(result.symbols) > 0
    assert "expected_text" in result.summary

    print("✅ TEST PASSED")

if __name__ == "__main__":
    asyncio.run(test_feature())
```

### Unit Test Template:
```python
"""Unit test for specific component."""
import pytest
from agent_core.nodes import node_intent_analyzer
from agent_core.state import MarketState

def test_component():
    \"\"\"Test component behavior.\"\"\"
    state = MarketState(query="test query")
    result = node_intent_analyzer(state)

    assert result.intent == "expected"
    assert len(result.symbols) > 0
```

## Test Categories

- **Integration**: Full agent workflow tests
- **Unit**: Individual component tests
- **Performance**: Speed and efficiency tests
- **Regression**: Prevent bug reintroduction

## Continuous Integration

Tests run automatically on:
- Pre-commit hooks (optional)
- Pull request creation
- Main branch merge

## Debugging Failed Tests

1. Run with `--debug` flag:
   ```bash
   uv run python tests/integration/test_name.py --debug
   ```

2. Check logs:
   ```bash
   tail -f logs/chat_debug.log
   ```

3. Add breakpoints:
   ```python
   import pdb; pdb.set_trace()
   ```

## Performance Benchmarks

- **Intent Detection**: < 2s
- **Checklist Generation**: < 1s
- **Research Query**: < 30s
- **Full Agent Run**: < 60s

## Known Issues

None currently. All tests passing! ✅
