
# LangGraph Agent Backend Tests

Comprehensive test suite for the LangGraph agent integration with backend.

## ⚠️ CRITICAL: Agent Wrapper Usage

**ALWAYS use `LangGraphAgentWrapper` for testing, NEVER use `src/agent.py` or call `graph.ainvoke()` directly.**

### ✅ Correct Pattern

```python
from app.core.agent_wrapper_langgraph import LangGraphAgentWrapper

@pytest.fixture
async def agent_wrapper(self):
    """Create LangGraph agent wrapper with mocked DB."""
    mock_db = AsyncMock()
    mock_db.get_user_notes = AsyncMock(return_value={})
    mock_db.upsert_user_notes = AsyncMock(return_value=True)
    mock_db.get_user_watchlist = AsyncMock(return_value=[])
    mock_db.update_user_watchlist = AsyncMock(return_value=True)

    wrapper = LangGraphAgentWrapper()
    wrapper.db = mock_db
    wrapper.cache = AsyncMock()
    await wrapper.initialize()
    return wrapper

@pytest.mark.asyncio
async def test_query(self, agent_wrapper):
    """Test agent query processing."""
    result = await agent_wrapper.process_text_command(
        user_id="test_user_123",
        query="What's the price of META?"
    )

    assert result["intent"] == "price_check"
    assert "META" in result["symbols"]
```

### ❌ Wrong Pattern (DO NOT USE)

```python
# ❌ WRONG - bypasses agent wrapper
from app.llm_agent.graph import create_market_agent_graph
graph = create_market_agent_graph()
result = await graph.ainvoke(MarketState(query=query))

# ❌ WRONG - uses old agent
from src.agent import NewsAgent
agent = NewsAgent()
```

---

## Test Structure

```
tests/backend/llm_agent/
├── unit/                          # Unit tests (fast, isolated)
│   ├── test_logger.py            # ✅ Logging system tests
│   ├── test_memory_supabase.py   # ✅ Memory with mocked DB
│   ├── test_watchlist_tools.py   # Watchlist tools tests
│   ├── test_state.py              # State management tests
│   └── test_prompts.py            # Prompt generation tests
├── integration/                   # Integration tests (API/DB required)
│   ├── test_agent_wrapper.py     # Agent wrapper integration
│   ├── test_intent_analyzer.py   # Intent analysis with real LLM
│   ├── test_tool_execution.py    # Tool execution tests
│   ├── test_memory_persistence.py # Memory database integration
│   ├── test_watchlist_db.py      # Watchlist database integration
│   └── test_graph_execution.py   # Full graph execution
├── e2e/                           # End-to-end tests (full pipeline)
│   ├── test_full_pipeline.py     # ASR → Agent → TTS
│   ├── test_multi_intent.py      # Multi-intent queries
│   ├── test_session_lifecycle.py  # Session start to end
│   └── test_error_recovery.py     # Error handling and recovery
├── conftest.py                    # Shared fixtures
├── pytest.ini                     # Pytest configuration
└── README.md                      # This file
```

---

## Quick Start

### Run All Tests
```bash
cd tests/backend/llm_agent
pytest
```

### Run Specific Test Categories
```bash
# Unit tests only (fast)
pytest unit/ -v

# Integration tests (requires API keys)
pytest integration/ -v

# E2E tests (full pipeline)
pytest e2e/ -v
```

### Run by Marker
```bash
# Fast tests only
pytest -m "unit"

# Tests requiring APIs
pytest -m "requires_api"

# Skip slow tests
pytest -m "not slow"
```

---

## Test Categories

### Unit Tests (unit/)
**Purpose**: Test individual components in isolation
**Speed**: Fast (<100ms per test)
**Dependencies**: None (mocked)
**Coverage**: Logger, Memory, State, Tools

**Markers**: `@pytest.mark.unit`

**Example**:
```python
@pytest.mark.unit
def test_logger_initialization(logger, temp_log_dir):
    """Test logger initializes correctly."""
    assert logger.log_dir == Path(temp_log_dir)
    assert logger.session_logger is not None
```

**What We Test**:
- ✅ Logger creates correct file structure
- ✅ Logger writes valid JSONL entries
- ✅ Memory loads and saves to mocked DB
- ✅ Memory tracks sessions correctly
- ✅ Watchlist tools format responses correctly
- ✅ State transitions are valid
- ✅ Prompts generate correct format

---

### Integration Tests (integration/)
**Purpose**: Test components working together
**Speed**: Medium (1-5s per test)
**Dependencies**: Real APIs (LLM, market data), Mocked DB
**Coverage**: Agent wrapper, Graph execution, Database integration

**Markers**: `@pytest.mark.integration`, `@pytest.mark.requires_api`

**Example**:
```python
@pytest.mark.integration
@pytest.mark.requires_api
async def test_intent_analyzer_with_real_llm():
    """Test intent analysis with actual LLM."""
    query = "What's the price of META?"
    result = await run_intent_analyzer(query)
    assert result.intent == "price_check"
    assert "META" in result.symbols
```

**What We Test**:
- Agent wrapper processes queries correctly
- Intent analyzer works with real LLM
- Tools execute and return data
- Memory persists to database
- Watchlist updates database
- Graph executes all nodes
- Multi-intent parallelization works

---

### E2E Tests (e2e/)
**Purpose**: Test complete user workflows
**Speed**: Slow (5-30s per test)
**Dependencies**: All (ASR, Agent, TTS, DB, APIs)
**Coverage**: Full pipeline, Session lifecycle, Error recovery

**Markers**: `@pytest.mark.e2e`, `@pytest.mark.slow`

**Example**:
```python
@pytest.mark.e2e
@pytest.mark.slow
async def test_full_voice_pipeline():
    """Test complete voice command pipeline."""
    # Mock audio input
    audio_data = load_test_audio("what_is_meta_price.wav")

    # Process through pipeline
    result = await process_voice_command(audio_data, user_id="test_user")

    # Verify complete workflow
    assert result['transcription'] == "What is the price of META?"
    assert result['intent'] == "price_check"
    assert result['response'] is not None
    assert result['audio_output'] is not None
```

**What We Test**:
- ASR → Agent → TTS full pipeline
- Multi-intent queries with parallelization
- Session start, queries, finalization
- Memory persistence across sessions
- Watchlist CRUD operations
- Error handling and recovery
- Logging captures all events

---

## Configuration

### pytest.ini
```ini
[pytest]
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (may require database/API)
    e2e: End-to-end tests (full pipeline)
    slow: Slow tests (>5 seconds)
    requires_api: Requires external API
    requires_db: Requires database connection
    skip_ci: Skip in CI environment
```

### Environment Variables
```bash
# Required for integration tests
export ZHIPUAI_API_KEY=your_key
export TAVILY_API_KEY=your_key

# Required for database tests
export SUPABASE_URL=your_url
export SUPABASE_KEY=your_key

# Optional (will use mocks if not set)
export TESTING=true
```

---

## Fixtures

### Database Fixtures
- `mock_db`: Mocked database manager
- `mock_cache`: Mocked cache manager

### Logging Fixtures
- `temp_log_dir`: Temporary log directory
- `mock_logger`: Mocked agent logger

### LLM Fixtures
- `mock_llm`: Mocked LLM for intent analysis
- `mock_llm_response_generator`: Mocked LLM for responses

### Memory Fixtures
- `mock_memory`: Mocked long-term memory instance

### Agent Fixtures
- `mock_market_state`: Mocked MarketState
- `mock_agent_wrapper`: Mocked agent wrapper

### Test Data Fixtures
- `test_user_id`: Test user ID
- `test_session_id`: Test session ID
- `sample_queries`: Sample test queries
- `sample_intents`: Sample intent objects

See [conftest.py](conftest.py) for all available fixtures.

---

## CI/CD Integration (Render Deploy)

### Render-Ready Configuration

Tests are configured to run in Render's CI environment:

**1. Automatic Skipping**:
- Tests marked with `@pytest.mark.requires_api` skip if `CI=true`
- Tests marked with `@pytest.mark.slow` skip unless `--runslow` flag
- Tests marked with `@pytest.mark.skip_ci` always skip in CI

**2. Mock API Keys**:
- conftest.py auto-generates mock API keys if not set
- No real API calls in CI (all mocked)

**3. Fast Test Suite**:
```bash
# Run only fast, CI-safe tests
pytest -m "unit and not skip_ci" --tb=short
```

### Render Build Script
```bash
# In render.yaml or build script
pip install -r requirements-test.txt
pytest tests/backend/llm_agent/unit/ -v --tb=short
```

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements-test.txt
      - name: Run unit tests
        run: pytest tests/backend/llm_agent/unit/ -v
      - name: Run integration tests (if API keys available)
        if: ${{ secrets.ZHIPUAI_API_KEY }}
        env:
          ZHIPUAI_API_KEY: ${{ secrets.ZHIPUAI_API_KEY }}
        run: pytest tests/backend/llm_agent/integration/ -v
```

---

## Test Coverage

### Current Coverage

| Module | Coverage | Tests |
|--------|----------|-------|
| logger.py | ✅ 95% | 25 tests |
| long_term_memory_supabase.py | ✅ 90% | 20 tests |
| watchlist_tools_supabase.py | ⏳ 80% | 15 tests (TODO) |
| agent_wrapper_langgraph.py | ⏳ 70% | 12 tests (TODO) |
| nodes.py | ⏳ 60% | 10 tests (TODO) |
| graph.py | ⏳ 50% | 8 tests (TODO) |

### Generate Coverage Report
```bash
# Install coverage tools
pip install pytest-cov

# Run with coverage
pytest --cov=backend/app/llm_agent --cov-report=html

# View report
open htmlcov/index.html
```

---

## Writing New Tests

### Unit Test Template
```python
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend'))

from app.llm_agent.your_module import YourClass


class TestYourClass:
    """Test suite for YourClass."""

    @pytest.fixture
    def instance(self):
        """Create instance for testing."""
        return YourClass()

    @pytest.mark.unit
    def test_basic_functionality(self, instance):
        """Test basic functionality."""
        result = instance.method()
        assert result is not None

    @pytest.mark.unit
    async def test_async_method(self, instance):
        """Test async method."""
        result = await instance.async_method()
        assert result is not None
```

### Integration Test Template
```python
import pytest

@pytest.mark.integration
@pytest.mark.requires_api
async def test_integration_feature(mock_db):
    """Test feature with real API."""
    # Setup
    agent = await create_agent(db=mock_db)

    # Execute
    result = await agent.process("test query")

    # Verify
    assert result is not None
    assert result['intent'] is not None
```

### E2E Test Template
```python
import pytest

@pytest.mark.e2e
@pytest.mark.slow
async def test_end_to_end_workflow(test_user_id, test_session_id):
    """Test complete workflow."""
    # Start session
    await start_session(test_user_id, test_session_id)

    # Process queries
    result1 = await process_query("Query 1")
    result2 = await process_query("Query 2")

    # Finalize
    await finalize_session(test_user_id)

    # Verify results
    assert result1 is not None
    assert result2 is not None
```

---

## Debugging Tests

### Run Single Test
```bash
pytest tests/backend/llm_agent/unit/test_logger.py::TestAgentLogger::test_start_session -v -s
```

### Enable Logging
```bash
pytest --log-cli-level=DEBUG -v -s
```

### Drop into Debugger on Failure
```bash
pytest --pdb
```

### Print Captured Output
```bash
pytest -v -s  # -s disables output capturing
```

---

## Common Issues

### Issue: Import Errors
**Solution**: Ensure backend is in Python path
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend'))
```

### Issue: Async Tests Fail
**Solution**: Use `@pytest.mark.asyncio` or set `asyncio_mode = auto` in pytest.ini

### Issue: Fixtures Not Found
**Solution**: Check `conftest.py` is in correct location and fixtures are defined

### Issue: Database Connection Errors
**Solution**: Use mocked database for unit/integration tests
```python
@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.get_user_notes = AsyncMock(return_value={})
    return db
```

---

## Performance Benchmarks

### Expected Test Times

| Category | Count | Time | Per Test |
|----------|-------|------|----------|
| Unit | 60 tests | ~6s | 100ms |
| Integration | 30 tests | ~90s | 3s |
| E2E | 10 tests | ~180s | 18s |
| **Total** | **100** | **~5min** | **3s avg** |

### CI/CD Times
- **Unit tests only**: ~10s
- **Unit + Integration**: ~2min
- **Full suite**: ~5min

---

## Continuous Improvement

### TODO
- [ ] Add more integration tests for nodes.py
- [ ] Add E2E tests for error recovery
- [ ] Add performance/load tests
- [ ] Add security tests
- [ ] Increase coverage to 90%+
- [ ] Add mutation testing
- [ ] Add property-based testing (Hypothesis)

### Contributing
1. Write tests for new features
2. Maintain >80% coverage
3. Ensure all tests pass before PR
4. Add appropriate markers
5. Update this README

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Last Updated**: 2025-01-04
**Maintainer**: Backend Team
**Status**: ✅ Ready for Use (Unit Tests), ⏳ In Progress (Integration/E2E)
