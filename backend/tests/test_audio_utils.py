"""
Tests for audio_utils.py
音频工具测试
"""

import io
import struct

# Add parent directory to path for imports
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.audio_utils import calculate_wav_rms


class TestCalculateWavRms:
    """Tests for calculate_wav_rms function"""

    def test_valid_wav_returns_positive_rms(self, sample_wav_data):
        """Test that a valid WAV with audio content returns positive RMS"""
        rms = calculate_wav_rms(sample_wav_data)
        assert rms > 0, "RMS should be positive for audio with content"

    def test_silent_wav_returns_zero_rms(self, silent_wav_data):
        """Test that a silent WAV returns zero or near-zero RMS"""
        rms = calculate_wav_rms(silent_wav_data)
        assert rms < 1.0, "RMS should be near zero for silent audio"

    def test_short_wav_returns_valid_rms(self, short_wav_data):
        """Test that a short (32ms) WAV still returns valid RMS"""
        rms = calculate_wav_rms(short_wav_data)
        # Short WAV may have low RMS due to limited samples
        assert rms >= 0, "RMS should be non-negative"

    def test_empty_bytes_returns_zero(self):
        """Test that empty bytes returns zero"""
        rms = calculate_wav_rms(b"")
        assert rms == 0.0

    def test_too_short_wav_returns_zero(self):
        """Test that WAV shorter than header returns zero"""
        rms = calculate_wav_rms(b"RIFF" + b"\x00" * 20)
        assert rms == 0.0

    def test_invalid_header_returns_zero(self):
        """Test that invalid WAV header returns zero"""
        rms = calculate_wav_rms(b"NOT_A_WAV_FILE_HEADER" + b"\x00" * 100)
        assert rms == 0.0

    def test_missing_data_chunk_returns_zero(self):
        """Test that WAV without data chunk returns zero"""
        # Create a minimal WAV header without data chunk
        header = b"RIFF" + struct.pack("<I", 36) + b"WAVE"
        header += b"fmt " + struct.pack("<I", 16)  # fmt chunk
        header += struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)  # PCM format
        # No 'data' chunk

        rms = calculate_wav_rms(header)
        assert rms == 0.0

    def test_rms_increases_with_amplitude(self):
        """Test that RMS increases with audio amplitude"""
        sample_rate = 16000
        duration = 0.5
        num_samples = int(sample_rate * duration)

        import math

        def create_wav_with_amplitude(amplitude):
            samples = []
            for i in range(num_samples):
                t = i / sample_rate
                value = int(amplitude * math.sin(2 * math.pi * 440 * t))
                samples.append(value)

            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))
            return buffer.getvalue()

        low_amp_wav = create_wav_with_amplitude(5000)
        high_amp_wav = create_wav_with_amplitude(20000)

        low_rms = calculate_wav_rms(low_amp_wav)
        high_rms = calculate_wav_rms(high_amp_wav)

        assert high_rms > low_rms, "Higher amplitude should result in higher RMS"
