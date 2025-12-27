"""
Final Utils Coverage Tests
Focus on WAV RMS calculation and ensure_upload_dir (simpler logic).
"""

import struct
from unittest.mock import patch

from app.utils.audio_utils import calculate_wav_rms, ensure_upload_dir

# ========== WAV RMS Tests ==========


def test_calculate_wav_rms_invalid_header():
    # Too short
    assert calculate_wav_rms(b"short") == 0.0
    # Invalid header
    assert calculate_wav_rms(b"NOTARIFF12345678901234567890123456789012") == 0.0


def test_calculate_wav_rms_valid_wav():
    # Construct a minimal valid WAV with 16-bit PCM data
    # RIFF header (12 bytes)
    riff = b"RIFF" + struct.pack("<I", 0) + b"WAVE"
    # fmt chunk (24 bytes)
    fmt_chunk = b"fmt " + struct.pack("<I", 16) + struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
    # data chunk with ~8000 samples for window
    samples = [1000] * 8000
    data = struct.pack(f"<{len(samples)}h", *samples)
    data_chunk = b"data" + struct.pack("<I", len(data)) + data

    wav_bytes = riff + fmt_chunk + data_chunk

    rms = calculate_wav_rms(wav_bytes)
    assert rms > 0.0  # Should produce a non-zero RMS


# ========== ensure_upload_dir Tests ==========


def test_ensure_upload_dir():
    with patch("os.makedirs") as mock_makedirs:
        path = ensure_upload_dir()
        mock_makedirs.assert_called_once()
        assert "uploads" in path
