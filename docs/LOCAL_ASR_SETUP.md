# Local ASR Setup Guide

## Issue: SenseVoice Model Not Loading

If you see this warning when starting the backend server:

```
⚠️ FunASR not available, using fallback ASR
⚠️ SenseVoice model failed to load - using fallback transcription
```

This means the local ASR dependencies are not installed.

---

## Solution

### Option 1: Install Local ASR Dependencies (Recommended for Local Development)

Install the optional local ASR packages (~2GB):

```bash
# Install with local ASR support
uv sync --extra local-asr
```

This installs:
- `funasr>=1.0.0` - FunASR library for SenseVoice
- `torch>=2.8.0` - PyTorch for model inference
- `torchaudio>=2.8.0` - Audio processing
- `sounddevice>=0.5.2` - Audio device access
- `pygame>=2.5.2` - Audio playback

**After installation**, restart your server:
```bash
make run-server
# or
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

You should see:
```
✅ SenseVoice model loaded successfully
```

---

### Option 2: Use HuggingFace Space API (Lightweight, Cloud-Ready)

If you don't need local ASR or want to save disk space, use the HuggingFace Space API:

1. **Set environment variable**:
   ```bash
   # In env_files/supabase.env or backend/.env
   USE_LOCAL_ASR=false  # Use HF Space API instead of local model
   ```

2. **Get HuggingFace Token** (optional but recommended):
   ```bash
   # In env_files/supabase.env
   HF_TOKEN=your_huggingface_token_here
   ```

3. **Install only production dependencies**:
   ```bash
   uv sync  # No --extra flag needed
   ```

The backend will use the HuggingFace Space API for ASR, which:
- ✅ No local model download needed
- ✅ ~2GB less disk space
- ✅ Works on any platform
- ✅ Same for Render deployment
- ⚠️ Requires internet connection
- ⚠️ Slightly higher latency (~100-200ms more)

---

## Comparison

| Feature | Local ASR (`USE_LOCAL_ASR=true`) | HF Space API (`USE_LOCAL_ASR=false`) |
|---------|----------------------------------|--------------------------------------|
| **Installation** | `uv sync --extra local-asr` | `uv sync` |
| **Disk Space** | ~2GB (model + dependencies) | ~100MB (lightweight) |
| **Internet Required** | Only for first download | Yes, for every request |
| **Latency** | ~50-100ms (very fast) | ~150-300ms (good) |
| **Privacy** | 100% local processing | Sent to HF servers |
| **Deployment** | Local/on-premise only | Cloud-ready (Render, etc.) |
| **Offline Support** | ✅ Yes | ❌ No |

---

## Environment Configuration

### Local Development (with local model)

```bash
# env_files/supabase.env or backend/.env
USE_LOCAL_ASR=true
HF_TOKEN=  # Optional, not needed for local ASR
```

### Cloud Deployment (Render, Vercel, etc.)

```bash
# Environment variables in deployment platform
USE_LOCAL_ASR=false  # Use HF API
HF_TOKEN=hf_xxxxx  # Your HuggingFace token
```

---

## Verification

### Check if FunASR is Installed

```bash
uv pip list | grep funasr
# Should show: funasr  x.x.x
```

### Check if Model Loads

Start server and look for:
```bash
✅ SenseVoice model loaded successfully from models/iic/SenseVoiceSmall
```

Or check server logs:
```bash
# Should NOT see these warnings:
⚠️ FunASR not available
⚠️ SenseVoice model failed to load
```

---

## Troubleshooting

### 1. Model Download Fails

**Error**: `Failed to download SenseVoice model`

**Solution**:
```bash
# Manually download model
mkdir -p models/iic
cd models/iic
git clone https://huggingface.co/FunAudioLLM/SenseVoiceSmall
```

### 2. Torch Import Error

**Error**: `ImportError: cannot import name 'torch'`

**Solution**:
```bash
# Reinstall torch
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 3. Out of Memory

**Error**: `RuntimeError: [enforce fail at alloc_cpu.cpp:73] err == 0`

**Solution**: Local ASR requires ~4GB RAM. Use HF API instead:
```bash
USE_LOCAL_ASR=false
```

---

## Makefile Targets

```bash
# Install production dependencies only
make install

# Install with local ASR support
make install-dev  # or manually: uv sync --extra local-asr

# Run server
make run-server
```

---

## Related Documentation

- [pyproject.toml](../pyproject.toml) - Dependency configuration
- [API_DESIGN.md](docs/reference/API_DESIGN.md) - API documentation
- [TESTING.md](docs/TESTING.md) - Testing guide
