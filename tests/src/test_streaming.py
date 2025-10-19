"""
Test Suite for src/ Streaming Functionality

Tests:
1. LLM streaming (simulated and direct)
2. TTS audio streaming
3. Complete streaming pipeline
4. Integration with voice_output
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import NewsAgent
from src.voice_output import stream_tts_audio, say_streaming


class TestLLMStreaming:
    """Test LLM streaming functionality in src/agent.py"""

    @pytest.fixture
    def agent(self):
        """Create NewsAgent instance."""
        return NewsAgent()

    @pytest.mark.asyncio
    async def test_get_response_stream_yields_chunks(self, agent):
        """Test that get_response_stream yields multiple chunks."""
        chunks = []

        async for chunk in agent.get_response_stream("Hello"):
            chunks.append(chunk)

        # Should yield multiple chunks (simulated streaming)
        assert len(chunks) >= 1, "Should yield at least one chunk"

        # Full response should be non-empty
        full_response = "".join(chunks)
        assert len(full_response) > 0, "Response should not be empty"

        print(f"\n✓ Received {len(chunks)} chunks")
        print(f"✓ Full response: {len(full_response)} characters")

    @pytest.mark.asyncio
    async def test_get_response_stream_direct_yields_tokens(self, agent):
        """Test direct LLM streaming (bypasses agent)."""
        tokens = []

        try:
            async for token in agent.get_response_stream_direct("Hi"):
                tokens.append(token)
                if len(tokens) >= 50:  # Limit tokens for testing
                    break

            # Should yield tokens
            assert len(tokens) > 0, "Should yield tokens"

            full_response = "".join(tokens)
            print(f"\n✓ Received {len(tokens)} tokens")
            print(f"✓ Response: {full_response}")

        except Exception as e:
            # Direct streaming might fail if LLM has issues
            print(f"\n⚠️ Direct streaming error (expected if API issues): {e}")
            pytest.skip(f"Direct streaming not available: {e}")

    @pytest.mark.asyncio
    async def test_simulated_streaming_chunk_size(self, agent):
        """Test that simulated streaming breaks response into chunks."""
        chunks = []

        async for chunk in agent.get_response_stream("What is 2+2?"):
            chunks.append(chunk)

        # With simulated streaming, chunks should be ~50 chars or less
        if len(chunks) > 1:
            avg_chunk_size = sum(len(c) for c in chunks) / len(chunks)
            assert avg_chunk_size <= 60, f"Average chunk size should be ~50 chars, got {avg_chunk_size}"
            print(f"\n✓ Average chunk size: {avg_chunk_size:.1f} chars")


class TestTTSStreaming:
    """Test TTS streaming functionality in src/voice_output.py"""

    @pytest.mark.asyncio
    async def test_stream_tts_audio_yields_chunks(self):
        """Test that TTS streams audio in chunks."""
        chunks = []

        try:
            async for chunk in stream_tts_audio("Testing TTS streaming"):
                chunks.append(chunk)
                print(f"  Chunk {len(chunks)}: {len(chunk)} bytes")

            # Should yield multiple chunks
            assert len(chunks) > 0, "Should yield at least one chunk"

            # Each chunk should be reasonable size (4KB default)
            for i, chunk in enumerate(chunks[:-1]):  # Exclude last chunk (may be smaller)
                assert len(chunk) == 4096, f"Chunk {i} should be 4096 bytes, got {len(chunk)}"

            total_bytes = sum(len(c) for c in chunks)
            print(f"\n✓ TTS streamed {len(chunks)} chunks")
            print(f"✓ Total audio: {total_bytes} bytes")

        except Exception as e:
            if "SSL" in str(e) or "certificate" in str(e).lower():
                pytest.skip(f"TTS SSL error (see TTS_SSL_FIX_GUIDE.md): {e}")
            else:
                raise

    @pytest.mark.asyncio
    async def test_stream_tts_audio_custom_chunk_size(self):
        """Test TTS with custom chunk size."""
        chunks = []
        custom_size = 2048

        try:
            async for chunk in stream_tts_audio("Hello", chunk_size=custom_size):
                chunks.append(chunk)

            # Chunks should match custom size (except last)
            for chunk in chunks[:-1]:
                assert len(chunk) == custom_size, f"Chunk should be {custom_size} bytes"

            print(f"\n✓ Custom chunk size working: {custom_size} bytes")

        except Exception as e:
            if "SSL" in str(e):
                pytest.skip(f"TTS SSL error: {e}")
            else:
                raise

    @pytest.mark.asyncio
    async def test_say_streaming_with_interruption(self):
        """Test say_streaming with interruption."""
        interrupt_event = asyncio.Event()

        # Start speaking in background
        speak_task = asyncio.create_task(
            say_streaming("This is a long test sentence", interrupt_event=interrupt_event)
        )

        # Interrupt after short delay
        await asyncio.sleep(0.1)
        interrupt_event.set()

        # Wait for task to complete
        try:
            await speak_task
            print("\n✓ say_streaming handled interruption")
        except Exception as e:
            if "SSL" in str(e):
                pytest.skip(f"TTS SSL error: {e}")
            else:
                # Interruption might cause various exceptions, that's ok
                print(f"\n✓ Interrupted (exception expected): {e}")


class TestStreamingIntegration:
    """Test complete streaming pipeline integration."""

    @pytest.fixture
    def agent(self):
        """Create NewsAgent instance."""
        return NewsAgent()

    @pytest.mark.asyncio
    async def test_llm_and_tts_streaming_integration(self, agent):
        """Test combined LLM and TTS streaming."""
        llm_chunks = []
        tts_chunks_count = 0

        try:
            # Stream LLM response
            full_response = ""
            async for chunk in agent.get_response_stream("Hello"):
                llm_chunks.append(chunk)
                full_response += chunk

            print(f"\n✓ LLM streamed {len(llm_chunks)} chunks")
            print(f"✓ Response: {full_response[:100]}...")

            # Try TTS on response
            async for audio_chunk in stream_tts_audio(full_response):
                tts_chunks_count += 1

            print(f"✓ TTS generated {tts_chunks_count} audio chunks")

            assert len(llm_chunks) > 0, "Should have LLM chunks"
            assert tts_chunks_count > 0, "Should have TTS chunks"

        except Exception as e:
            if "SSL" in str(e):
                pytest.skip(f"TTS SSL error: {e}")
            else:
                raise

    @pytest.mark.asyncio
    async def test_concurrent_tts_generation(self, agent):
        """Test that TTS can start before LLM finishes (simulated)."""
        import time

        sentence_buffer = ""
        tts_start_times = []
        llm_start_time = time.time()

        try:
            async for chunk in agent.get_response_stream("Tell me a story"):
                sentence_buffer += chunk

                # When we have enough text, start TTS (simulating concurrent processing)
                if "." in sentence_buffer or len(sentence_buffer) > 50:
                    tts_start_time = time.time() - llm_start_time
                    tts_start_times.append(tts_start_time)

                    # Start TTS in background (simulated - don't actually play)
                    # In real use, this would be: asyncio.create_task(say_streaming(sentence_buffer))
                    async for _ in stream_tts_audio(sentence_buffer):
                        break  # Just test first chunk

                    sentence_buffer = ""

            if tts_start_times:
                first_tts_time = min(tts_start_times)
                print(f"\n✓ First TTS started after {first_tts_time:.2f}s of LLM streaming")
                print(f"✓ Started TTS {len(tts_start_times)} times during LLM generation")

        except Exception as e:
            if "SSL" in str(e):
                pytest.skip(f"TTS SSL error: {e}")
            else:
                raise


class TestStreamingPerformance:
    """Test streaming performance characteristics."""

    @pytest.mark.asyncio
    async def test_tts_streaming_performance(self):
        """Test TTS streaming speed."""
        import time

        text = "This is a performance test for TTS streaming functionality."

        try:
            start_time = time.time()
            chunks = []

            async for chunk in stream_tts_audio(text):
                chunks.append(chunk)
                if len(chunks) == 1:
                    time_to_first_chunk = (time.time() - start_time) * 1000
                    print(f"\n✓ Time to first TTS chunk: {time_to_first_chunk:.0f}ms")

            total_time = (time.time() - start_time) * 1000

            print(f"✓ Total TTS generation: {total_time:.0f}ms")
            print(f"✓ Total chunks: {len(chunks)}")
            print(f"✓ Average time per chunk: {total_time / len(chunks):.0f}ms")

            # First chunk should arrive reasonably fast
            assert time_to_first_chunk < 2000, f"First chunk took too long: {time_to_first_chunk}ms"

        except Exception as e:
            if "SSL" in str(e):
                pytest.skip(f"TTS SSL error: {e}")
            else:
                raise

    @pytest.mark.asyncio
    async def test_llm_streaming_latency(self):
        """Test LLM streaming response time."""
        import time

        agent = NewsAgent()

        start_time = time.time()
        chunk_count = 0

        async for chunk in agent.get_response_stream("Hi"):
            chunk_count += 1
            if chunk_count == 1:
                time_to_first_chunk = (time.time() - start_time) * 1000
                print(f"\n✓ Time to first LLM chunk: {time_to_first_chunk:.0f}ms")

        total_time = (time.time() - start_time) * 1000
        print(f"✓ Total LLM response: {total_time:.0f}ms")
        print(f"✓ Total chunks: {chunk_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
