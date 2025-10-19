# Quick Reference Card

## 🚀 One-Line Commands

```bash
# Demo streaming
uv run python -m src.main_streaming --demo

# Run all tests
uv run python tests/run_all_tests.py --quick

# Start backend server
make run-server

# Fix TTS SSL errors
uv pip install --upgrade certifi edge-tts
```

---

## 📊 TTS Streaming Status

| Component | Generation | Playback | Overall |
|-----------|-----------|----------|---------|
| **backend/** | ✅ YES (4KB chunks) | ✅ YES (progressive) | ✅ FULL |
| **src/** | ✅ YES (4KB chunks) | ❌ NO (complete file) | ⚠️ PARTIAL |

**Performance**:
- backend/: ~700ms to first audio (79% faster) ⚡
- src/: ~2950ms to first audio

---

## 🔍 LLM Streaming Status

**Current**: ⚠️ **Simulated** (breaks complete response into chunks)

**Why**: LangChain AgentExecutor limitation with tools

**Options**:
1. `get_response_stream()` - Simulated (keeps agent tools) ✅
2. `get_response_stream_direct()` - True streaming (no tools) ⚠️

**Future**: Migrate to LangGraph for true streaming + tools

---

## 📁 Key Files

### Implementation:
- `src/agent.py:314-420` - LLM streaming
- `src/voice_output.py:254-358` - TTS streaming
- `src/main_streaming.py` - Demo app
- `backend/app/core/streaming_handler.py:406-494` - Pipeline
- `backend/app/core/websocket_manager.py:611-787` - WebSocket

### Tests:
- `tests/src/test_streaming.py` - src/ tests (10 tests)
- `tests/backend/local/core/test_streaming_llm_tts.py` - backend/ tests (13 tests)
- `tests/run_all_tests.py` - Unified runner

### Documentation:
- `COMPLETE_IMPLEMENTATION_SUMMARY.md` - **START HERE**
- `TESTING_GUIDE.md` - Testing
- `SRC_STREAMING_GUIDE.md` - src/ usage
- `TTS_STREAMING_STATUS.md` - TTS analysis
- `STREAMING_ISSUES_EXPLAINED.md` - Known issues
- `TTS_SSL_FIX_GUIDE.md` - Troubleshooting
- `GLM_MODEL_FIX.md` - Model config

---

## ⚙️ Configuration

### GLM Model
```python
model = "GLM-4-Flash"  # ✅ Correct
api_base = "https://open.bigmodel.cn/api/paas/v4/"
```

### TTS Settings
```python
chunk_size = 4096       # Audio chunk size
voice = "en-US-JennyNeural"  # Voice
rate = "+0%"            # Speech rate
```

### Streaming
```python
sentence_endings = [".", "!", "?", "\n"]
buffer_threshold = 100  # Characters before TTS
```

---

## 🧪 Test Commands

```bash
# All tests
uv run python tests/run_all_tests.py

# Quick tests only
uv run python tests/run_all_tests.py --quick

# src/ tests only
uv run python tests/run_all_tests.py --src-only

# backend/ tests only
uv run python tests/run_all_tests.py --backend-only

# With HTML report
uv run python tests/run_all_tests.py --html

# Specific test
uv run python -m pytest tests/src/test_streaming.py::TestTTSStreaming -v
```

---

## 🐛 Common Issues

### TTS SSL Error
```
SSLCertVerificationError: certificate has expired
```
**Fix**: `uv pip install --upgrade certifi edge-tts`

### GLM Model Error (1211)
```
模型不存在，请检查模型代码
```
**Fix**: Use `GLM-4-Flash` (not `glm-4-flashx`)

### Audio Buffer Overflow
```
ERROR: Audio buffer overflow
```
**Status**: Normal (occasional), only investigate if frequent

### Import Error
```
ModuleNotFoundError: No module named 'src'
```
**Fix**: Run from project root: `cd News_agent/`

---

## 📊 Performance

### Time-to-First-Audio

**Before**: 3300ms (sequential)
**After (backend/)**: 700ms (79% faster) ⚡
**After (src/)**: 2950ms (better UX)

---

## ✅ Test Status

| Category | Count | Status |
|----------|-------|--------|
| src/ Tests | 10 | ✅ |
| backend/ Tests | 13 | ✅ |
| VAD Tests | 5+ | ✅ |
| **Total** | **30+** | **✅** |

---

## 🎯 Quick Usage

### src/ Desktop App
```python
from src.agent import NewsAgent
from src.voice_output import stream_tts_audio
import asyncio

agent = NewsAgent()

# LLM streaming
async for chunk in agent.get_response_stream("Hello"):
    print(chunk, end='')

# TTS streaming
async for audio in stream_tts_audio("Hello"):
    # Process 4KB chunk
    pass
```

### backend/ WebSocket
```python
from backend.app.core.streaming_handler import StreamingVoiceHandler

handler = StreamingVoiceHandler()

async for chunk in handler.process_voice_command_streaming(
    session_id, audio_bytes, "webm"
):
    print(f"{chunk['type']}: {chunk.get('text', chunk.get('data', ''))}")
```

---

## 📖 Learn More

**Full details**: [COMPLETE_IMPLEMENTATION_SUMMARY.md](COMPLETE_IMPLEMENTATION_SUMMARY.md)

**Need help?**: Check the documentation guides above!
