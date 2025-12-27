"""
Audio Utilities
音频处理工具
"""

import os
import struct
import subprocess
import tempfile

from loguru import logger


def calculate_wav_rms(wav_data: bytes) -> float:
    """
    Calculate peak RMS (Root Mean Square) volume of WAV audio data.

    Uses sliding window approach and returns the MAXIMUM RMS across all windows,
    not the average. This ensures that even if most of the audio is silent,
    any portion with speech will be detected.

    Args:
        wav_data: WAV file bytes (must be 16-bit PCM)

    Returns:
        Peak RMS value in the same scale as frontend (0-60 range)
        Returns 0 if audio is invalid or too short
    """
    try:
        # Parse WAV header to get audio format info
        if len(wav_data) < 44:
            logger.debug(f"WAV too short: {len(wav_data)} bytes")
            return 0.0

        # Check WAV header
        if wav_data[:4] != b"RIFF" or wav_data[8:12] != b"WAVE":
            logger.warning("Invalid WAV header")
            return 0.0

        # Find data chunk
        data_offset = 12
        data_start = None
        while data_offset < len(wav_data) - 8:
            chunk_id = wav_data[data_offset : data_offset + 4]
            chunk_size = struct.unpack("<I", wav_data[data_offset + 4 : data_offset + 8])[0]

            if chunk_id == b"data":
                data_start = data_offset + 8
                break

            data_offset += 8 + chunk_size

        if data_start is None:
            logger.warning("No data chunk found in WAV")
            return 0.0

        # Read audio samples (assume 16-bit PCM mono)
        audio_bytes = wav_data[data_start:]
        if len(audio_bytes) < 100:  # Too short
            logger.debug(f"Audio data too short: {len(audio_bytes)} bytes")
            return 0.0

        # Convert to samples
        num_samples = len(audio_bytes) // 2
        samples = struct.unpack(f"<{num_samples}h", audio_bytes[: num_samples * 2])

        # Calculate peak RMS using sliding windows
        # Window size: ~0.5 second at 16kHz = 8000 samples
        # Step size: 4000 samples (50% overlap for better detection)
        window_size = 8000
        step_size = 4000

        max_rms = 0.0
        window_start = 0

        while window_start < num_samples:
            window_end = min(window_start + window_size, num_samples)
            window_samples = samples[window_start:window_end]

            if len(window_samples) < 100:
                break

            # Calculate RMS for this window
            sum_squares = 0
            for s in window_samples:
                # Normalize 16-bit sample to 8-bit scale (divide by 256)
                normalized = s / 256.0
                sum_squares += normalized * normalized

            window_rms = (sum_squares / len(window_samples)) ** 0.5

            # Track maximum RMS
            if window_rms > max_rms:
                max_rms = window_rms

            window_start += step_size

        logger.debug(
            f"WAV peak RMS: {max_rms:.2f} from {num_samples} samples ({num_samples // step_size} windows)"
        )

        return max_rms

    except Exception as e:
        logger.error(f"Error calculating WAV RMS: {e}")
        return 0.0


def get_audio_duration(file_path: str) -> float:
    """Get audio duration in seconds using ffprobe or ffmpeg"""
    try:
        # Try ffprobe first
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except FileNotFoundError:
        pass  # ffprobe not found, try ffmpeg
    except Exception as e:
        logger.warning(f"ffprobe failed: {e}")

    # Fallback to ffmpeg
    try:
        result = subprocess.run(["ffmpeg", "-i", file_path], capture_output=True, text=True)
        # Parse Duration: 00:00:05.12 from stderr
        output = result.stderr
        if "Duration:" in output:
            import re

            match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", output)
            if match:
                hours, minutes, seconds = map(float, match.groups())
                return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        logger.warning(f"ffmpeg duration check failed: {e}")

    return 0.0


def convert_webm_to_wav(webm_data: bytes) -> bytes:
    """Convert WebM audio to WAV format"""
    try:
        # Write WebM to temp file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as webm_file:
            webm_file.write(webm_data)
            webm_path = webm_file.name

        wav_path = webm_path.replace(".webm", ".wav")

        try:
            # Convert using ffmpeg
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    webm_path,
                    "-ar",
                    "16000",  # 16kHz sample rate (good for STT)
                    "-ac",
                    "1",  # Mono
                    wav_path,
                ],
                capture_output=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr.decode()}")
                # Return original data if conversion fails
                return webm_data

            # Read converted file
            with open(wav_path, "rb") as f:
                wav_data = f.read()

            return wav_data
        finally:
            # Cleanup
            if os.path.exists(webm_path):
                os.unlink(webm_path)
            if os.path.exists(wav_path):
                os.unlink(wav_path)

    except Exception as e:
        logger.error(f"Audio conversion error: {e}")
        return webm_data


def compress_to_opus(input_data: bytes, bitrate: str = "48k") -> bytes:
    """
    Compress audio to Opus format using FFmpeg.
    Opus provides excellent compression for voice at 48kbps.
    60 minutes of audio ≈ 22MB.

    Args:
        input_data: Raw audio bytes (WAV, WebM, etc.)
        bitrate: Target bitrate (default 48k for voice)

    Returns:
        Compressed audio bytes in Opus/OGG container
    """
    try:
        # Write input to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as input_file:
            input_file.write(input_data)
            input_path = input_file.name

        output_path = input_path.replace(".wav", ".opus")

        try:
            # Convert using ffmpeg: input -> Opus in OGG container
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_path,
                    "-c:a",
                    "libopus",
                    "-b:a",
                    bitrate,
                    "-vbr",
                    "on",
                    "-compression_level",
                    "10",
                    "-application",
                    "voip",  # Optimized for voice
                    "-ar",
                    "48000",  # Opus native sample rate
                    "-ac",
                    "1",  # Mono
                    output_path,
                ],
                capture_output=True,
                timeout=300,  # 5 minutes max for long recordings
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg Opus error: {result.stderr.decode()}")
                # Return original data if compression fails
                return input_data

            # Read compressed file
            with open(output_path, "rb") as f:
                opus_data = f.read()

            original_size = len(input_data)
            compressed_size = len(opus_data)
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            logger.info(
                f"Audio compressed: {original_size} -> {compressed_size} bytes ({ratio:.1f}% reduction)"
            )

            return opus_data

        finally:
            # Cleanup
            if os.path.exists(input_path):
                os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    except Exception as e:
        logger.error(f"Opus compression error: {e}")
        return input_data


def ensure_upload_dir() -> str:
    """Ensure upload directory exists and return path"""
    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"
    )
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir
