# Comprehensive Testing Guide

## Overview

Complete test suite covering:
- ✅ **src/** - Desktop/CLI streaming functionality
- ✅ **backend/** - WebSocket streaming functionality
- ✅ **VAD** - Voice activity detection
- ✅ **Interruption** - Voice interruption handling
- ✅ **Integration** - End-to-end tests

---

## Quick Start

### Run All Tests
```bash
uv run python tests/run_all_tests.py
```

### Run Quick Subset
```bash
uv run python tests/run_all_tests.py --quick
```

### Run Specific Test Suite
```bash
# src/ streaming tests only
uv run python tests/run_all_tests.py --src-only

# backend/ streaming tests only
uv run python tests/run_all_tests.py --backend-only

# VAD tests only
uv run python tests/run_all_tests.py --vad-only

# All streaming tests (src + backend)
uv run python tests/run_all_tests.py --streaming-only
```

---

## Test Structure

```
tests/
├── run_all_tests.py           # 🆕 Unified test runner
├── run_vad_tests.py            # VAD-specific test runner
│
├── src/                        # 🆕 src/ streaming tests
│   ├── __init__.py
│   └── test_streaming.py       # LLM + TTS streaming tests
│
├── backend/
│   └── local/
│       └── core/
│           ├── test_streaming_llm_tts.py  # Backend streaming tests
│           ├── test_vad_validation.py     # VAD validation tests
│           └── test_interruption_flow.py  # Interruption tests
│
└── integration/
    └── test_e2e_vad_interruption.py       # End-to-end tests
```

---

## src/ Streaming Tests

### Test File
`tests/src/test_streaming.py`

### Test Classes

#### 1. `TestLLMStreaming`
Tests LLM response streaming in `src/agent.py`

**Tests**:
- `test_get_response_stream_yields_chunks` - Simulated streaming
- `test_get_response_stream_direct_yields_tokens` - Direct LLM streaming
- `test_simulated_streaming_chunk_size` - Chunk size validation

**Run**:
```bash
uv run python -m pytest tests/src/test_streaming.py::TestLLMStreaming -v
```

#### 2. `TestTTSStreaming`
Tests TTS audio streaming in `src/voice_output.py`

**Tests**:
- `test_stream_tts_audio_yields_chunks` - Audio chunk generation
- `test_stream_tts_audio_custom_chunk_size` - Custom chunk sizes
- `test_say_streaming_with_interruption` - Interruption handling

**Run**:
```bash
uv run python -m pytest tests/src/test_streaming.py::TestTTSStreaming -v
```

**Note**: May skip if TTS SSL errors occur (see [TTS_SSL_FIX_GUIDE.md](TTS_SSL_FIX_GUIDE.md))

#### 3. `TestStreamingIntegration`
Tests combined LLM + TTS streaming

**Tests**:
- `test_llm_and_tts_streaming_integration` - Full pipeline
- `test_concurrent_tts_generation` - Concurrent processing

**Run**:
```bash
uv run python -m pytest tests/src/test_streaming.py::TestStreamingIntegration -v
```

#### 4. `TestStreamingPerformance`
Performance and latency tests

**Tests**:
- `test_tts_streaming_performance` - TTS speed
- `test_llm_streaming_latency` - LLM response time

**Run**:
```bash
uv run python -m pytest tests/src/test_streaming.py::TestStreamingPerformance -v -s
```

### Run All src/ Tests
```bash
uv run python -m pytest tests/src/ -v -s
```

---

## backend/ Streaming Tests

### Test File
`tests/backend/local/core/test_streaming_llm_tts.py`

### Test Classes

#### 1. `TestStreamingLLMResponse`
Tests agent wrapper streaming

**Tests**:
- `test_agent_stream_voice_response` - Agent streaming
- `test_streaming_with_real_agent` - Real agent test

#### 2. `TestConcurrentTTS`
Tests concurrent TTS generation

**Tests**:
- `test_sentence_based_tts_triggering` - Sentence detection
- `test_buffer_length_tts_triggering` - Buffer threshold
- `test_tts_streaming_chunks` - Chunk streaming

#### 3. `TestStreamingPipeline`
Tests complete pipeline

**Tests**:
- `test_full_streaming_pipeline_mock` - Mocked pipeline
- `test_streaming_pipeline_order` - Chunk ordering

#### 4. `TestWebSocketStreamingIntegration`
Tests WebSocket integration

**Tests**:
- `test_websocket_streaming_event_handler` - Event handling
- `test_streaming_interruption` - Interruption support
- `test_streaming_performance` - Performance metrics

#### 5. `TestStreamingEdgeCases`
Edge cases and error handling

**Tests**:
- `test_empty_llm_response` - Empty response handling
- `test_llm_error_during_streaming` - LLM errors
- `test_tts_error_during_streaming` - TTS errors

### Run All backend/ Streaming Tests
```bash
uv run python -m pytest tests/backend/local/core/test_streaming_llm_tts.py -v
```

**Expected**: 13/13 tests passing ✅

---

## VAD and Interruption Tests

### Use Existing Runner
```bash
uv run python tests/run_vad_tests.py
```

### Options
```bash
# Quick tests
uv run python tests/run_vad_tests.py --quick

# VAD only
uv run python tests/run_vad_tests.py --vad-only

# Interruption only
uv run python tests/run_vad_tests.py --interruption-only

# With verbose output
uv run python tests/run_vad_tests.py -v
```

---

## Test Coverage

### What's Tested

#### src/ (Desktop/CLI)
- ✅ LLM simulated streaming (chunk breaking)
- ✅ LLM direct streaming (token-by-token)
- ✅ TTS audio chunk generation
- ✅ TTS interruption handling
- ✅ LLM + TTS integration
- ✅ Performance metrics

#### backend/ (WebSocket)
- ✅ Agent wrapper streaming
- ✅ Sentence-based TTS triggering
- ✅ Buffer-based TTS triggering
- ✅ WebSocket event handling
- ✅ Streaming interruption
- ✅ Pipeline ordering
- ✅ Edge cases and errors

#### VAD & Interruption
- ✅ Audio sample validation
- ✅ Energy calculation
- ✅ WebRTC VAD validation
- ✅ Interrupt signal handling
- ✅ TTS streaming interruption
- ✅ Multiple interruptions

---

## Running Tests

### Individual Test
```bash
uv run python -m pytest tests/src/test_streaming.py::TestTTSStreaming::test_stream_tts_audio_yields_chunks -v -s
```

### Test Class
```bash
uv run python -m pytest tests/src/test_streaming.py::TestLLMStreaming -v
```

### Test File
```bash
uv run python -m pytest tests/src/test_streaming.py -v
```

### With Output
```bash
# -s shows print statements
uv run python -m pytest tests/src/ -v -s
```

### With HTML Report
```bash
uv run python tests/run_all_tests.py --html

# View report at: reports/src_streaming_tests.html
```

---

## Expected Results

### src/ Tests
```
tests/src/test_streaming.py::TestLLMStreaming::test_get_response_stream_yields_chunks PASSED
tests/src/test_streaming.py::TestLLMStreaming::test_simulated_streaming_chunk_size PASSED
tests/src/test_streaming.py::TestTTSStreaming::test_stream_tts_audio_yields_chunks PASSED
tests/src/test_streaming.py::TestStreamingIntegration::test_llm_and_tts_streaming_integration PASSED

Expected: 8-10 tests passing (some may skip if TTS SSL issues)
```

### backend/ Tests
```
tests/backend/local/core/test_streaming_llm_tts.py::TestStreamingLLMResponse PASSED
tests/backend/local/core/test_streaming_llm_tts.py::TestConcurrentTTS PASSED
tests/backend/local/core/test_streaming_llm_tts.py::TestWebSocketStreamingIntegration PASSED

Expected: 13/13 tests passing ✅
```

### VAD Tests
```
tests/backend/local/core/test_vad_validation.py PASSED
tests/backend/local/core/test_interruption_flow.py PASSED

Expected: All tests passing ✅
```

---

## Troubleshooting

### TTS SSL Errors
```
SKIPPED [1] TTS SSL error (see TTS_SSL_FIX_GUIDE.md)
```

**Solution**: See [TTS_SSL_FIX_GUIDE.md](TTS_SSL_FIX_GUIDE.md)

Quick fix:
```bash
uv pip install --upgrade certifi edge-tts
```

### LLM API Errors
```
ERROR: Error code: 401 - Invalid API key
```

**Solution**: Check `ZHIPUAI_API_KEY` in environment

```bash
# Verify API key
echo $ZHIPUAI_API_KEY

# Or check .env file
cat backend/.env | grep ZHIPUAI
```

### Import Errors
```
ModuleNotFoundError: No module named 'src'
```

**Solution**: Run tests from project root

```bash
cd /path/to/News_agent
uv run python -m pytest tests/src/ -v
```

### WebSocket State Errors
```
RuntimeError: WebSocket not in CONNECTED state
```

**Already Fixed**: Tests use proper `WebSocketState.CONNECTED`

If error persists:
```python
# Check mock setup in test
ws.client_state = WebSocketState.CONNECTED  # Not ws.client_state.name = "CONNECTED"
```

---

## CI/CD Integration

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
        pip install uv
        uv pip install -r requirements.txt
        uv pip install pytest pytest-asyncio

    - name: Run tests
      run: |
        uv run python tests/run_all_tests.py --quick

    - name: Generate HTML report
      if: always()
      run: |
        uv run python tests/run_all_tests.py --html

    - name: Upload test results
      if: always()
      uses: actions/upload-artifact@v2
      with:
        name: test-reports
        path: reports/
```

---

## Test Development

### Adding New Tests

#### For src/
Create in `tests/src/test_streaming.py`:

```python
@pytest.mark.asyncio
async def test_my_new_feature(self):
    """Test description."""
    # Your test code
    agent = NewsAgent()
    result = await agent.my_feature()
    assert result is not None
```

#### For backend/
Create in `tests/backend/local/core/test_streaming_llm_tts.py`:

```python
@pytest.mark.asyncio
async def test_my_backend_feature(self):
    """Test description."""
    handler = StreamingVoiceHandler()
    result = await handler.my_feature()
    assert result is not None
```

### Running New Tests
```bash
uv run python -m pytest tests/src/test_streaming.py::TestClass::test_my_new_feature -v -s
```

---

## Performance Benchmarks

### Expected Performance

#### src/ Streaming
```
Time to first LLM chunk: ~2000ms (simulated)
TTS generation: ~800ms
Time to first audio: ~950ms
```

#### backend/ Streaming
```
Time to first LLM chunk: ~2000ms (agent executor limitation)
TTS chunk 1: ~200ms
Time to first audio: ~200ms (to client)
```

### Measuring Performance
```bash
uv run python -m pytest tests/src/test_streaming.py::TestStreamingPerformance -v -s
```

---

## Summary

### Test Coverage Summary

| Component | Tests | Status |
|-----------|-------|--------|
| src/ LLM Streaming | 3 tests | ✅ |
| src/ TTS Streaming | 3 tests | ✅ |
| src/ Integration | 2 tests | ✅ |
| src/ Performance | 2 tests | ✅ |
| backend/ Streaming | 13 tests | ✅ |
| VAD Validation | 5+ tests | ✅ |
| Interruption Flow | 5+ tests | ✅ |
| **Total** | **30+ tests** | **✅** |

### Quick Commands Reference

```bash
# Run everything
uv run python tests/run_all_tests.py

# Run quick tests
uv run python tests/run_all_tests.py --quick

# Run src/ only
uv run python tests/run_all_tests.py --src-only

# Run backend/ only
uv run python tests/run_all_tests.py --backend-only

# Run with verbose + HTML
uv run python tests/run_all_tests.py --quick -v --html
```

---

## Related Documentation

- [SRC_STREAMING_GUIDE.md](SRC_STREAMING_GUIDE.md) - src/ streaming guide
- [STREAMING_LLM_TTS_SUMMARY.md](STREAMING_LLM_TTS_SUMMARY.md) - Backend streaming
- [TTS_STREAMING_STATUS.md](TTS_STREAMING_STATUS.md) - TTS streaming analysis
- [STREAMING_ISSUES_EXPLAINED.md](STREAMING_ISSUES_EXPLAINED.md) - Known issues
- [TTS_SSL_FIX_GUIDE.md](TTS_SSL_FIX_GUIDE.md) - SSL troubleshooting

**All tests integrated and ready to run!** 🎉
