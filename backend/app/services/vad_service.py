"""
VAD Service - Voice Activity Detection using Silero VAD (ONNX Runtime)
使用 Silero VAD ONNX 模型进行语音活动检测

Based on official Silero VAD OnnxWrapper implementation:
https://github.com/snakers4/silero-vad/blob/master/src/silero_vad/utils_vad.py
"""

import io
import wave
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger
from scipy import signal


class VADService:
    """Silero VAD 服务封装 (ONNX Runtime 版本)

    Key insight from official implementation:
    - Each 512-sample chunk needs a 64-sample context prepended
    - The context is the last 64 samples from the previous chunk
    - Hidden state tensor shape is (2, 1, 128)
    """

    _instance: Optional["VADService"] = None
    _session = None  # ONNX InferenceSession

    def __init__(self):
        """Private constructor - use get_instance() instead"""
        self.reset_states()

    @classmethod
    def get_instance(cls) -> "VADService":
        """获取 VAD 服务单例"""
        if cls._instance is None:
            cls._instance = cls()
            cls._load_model()
        return cls._instance

    @classmethod
    def _load_model(cls):
        """加载 Silero VAD ONNX 模型"""
        if cls._session is None:
            try:
                import onnxruntime as ort

                logger.info("Loading Silero VAD ONNX model...")

                # Model path: backend/models/silero_vad.onnx
                model_path = Path(__file__).parent.parent.parent / "models" / "silero_vad.onnx"

                if not model_path.exists():
                    raise FileNotFoundError(f"ONNX model not found: {model_path}")

                # Create inference session with CPU provider
                sess_options = ort.SessionOptions()
                sess_options.inter_op_num_threads = 1
                sess_options.intra_op_num_threads = 1

                cls._session = ort.InferenceSession(
                    str(model_path), sess_options, providers=["CPUExecutionProvider"]
                )

                logger.info("Silero VAD ONNX model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Silero VAD ONNX model: {e}")
                raise

    def is_speech(self, audio_data: bytes, sample_rate: int = 16000) -> bool:
        """
        判断音频是否包含人声

        Args:
            audio_data: WAV 格式的音频数据
            sample_rate: 采样率 (默认 16000)

        Returns:
            bool: True 如果检测到人声
        """
        try:
            speech_prob = self.get_speech_probability(audio_data, sample_rate)
            return speech_prob > 0.5
        except Exception as e:
            logger.warning(f"VAD detection error: {e}")
            # 出错时返回 True，避免丢失语音
            return True

    def get_speech_probability(self, audio_data: bytes, sample_rate: int = 16000) -> float:
        """
        获取音频末尾的语音概率（只检测最后 32ms）

        Silero VAD 的实时接口只接受固定长度的输入：
        - 16kHz: 512 样本 (32ms)
        - 8kHz: 256 样本 (32ms)

        Returns:
            float: 0.0 到 1.0 之间的概率值
        """
        if self._session is None:
            self._load_model()

        try:
            audio_array = self._wav_bytes_to_numpy(audio_data, sample_rate)

            if audio_array is None or len(audio_array) == 0:
                logger.warning("VAD: audio_array is None or empty")
                return 0.0

            # Silero VAD settings
            num_samples = 512 if sample_rate == 16000 else 256
            context_size = 64 if sample_rate == 16000 else 32

            # 只取最后 num_samples 样本来检测当前是否在说话
            if len(audio_array) > num_samples:
                audio_array = audio_array[-num_samples:]
            elif len(audio_array) < num_samples:
                # 如果不足，在前面补零
                padding = np.zeros(num_samples - len(audio_array), dtype=np.float32)
                audio_array = np.concatenate([padding, audio_array])

            # Add context (crucial for ONNX model!)
            # Context is zeros if not initialized, otherwise last samples from previous call
            if len(self._context) == 0:
                self._context = np.zeros(context_size, dtype=np.float32)

            # Concatenate context + audio chunk
            audio_with_context = np.concatenate([self._context, audio_array])

            # Prepare input for ONNX model
            input_data = audio_with_context.reshape(1, -1).astype(np.float32)

            # Run inference with state
            ort_inputs = {
                "input": input_data,
                "state": self._state,
                "sr": np.array(sample_rate, dtype=np.int64),
            }

            output, self._state = self._session.run(None, ort_inputs)
            speech_prob = float(output[0][0])

            # Update context for next call
            self._context = audio_array[-context_size:].copy()

            return speech_prob

        except Exception as e:
            logger.warning(f"VAD probability error: {e}")
            return 0.5  # 不确定时返回中间值

    def _wav_bytes_to_numpy(
        self, wav_bytes: bytes, target_sample_rate: int = 16000
    ) -> np.ndarray | None:
        """
        将 WAV 字节转换为 numpy array

        Args:
            wav_bytes: WAV 格式的音频字节
            target_sample_rate: 目标采样率

        Returns:
            np.ndarray: 音频数组，形状为 (samples,)，值范围 [-1, 1]
        """
        try:
            # 读取 WAV 数据
            with io.BytesIO(wav_bytes) as wav_file:
                with wave.open(wav_file, "rb") as wf:
                    n_channels = wf.getnchannels()
                    sample_width = wf.getsampwidth()
                    frame_rate = wf.getframerate()
                    n_frames = wf.getnframes()

                    audio_bytes = wf.readframes(n_frames)

            # 转换为 numpy 数组
            if sample_width == 2:
                dtype = np.int16
            elif sample_width == 4:
                dtype = np.int32
            else:
                dtype = np.int16

            audio_array = np.frombuffer(audio_bytes, dtype=dtype)

            # 如果是多声道，转为单声道
            if n_channels > 1:
                audio_array = audio_array.reshape(-1, n_channels)
                audio_array = audio_array.mean(axis=1)

            # 归一化到 [-1, 1]
            audio_float = audio_array.astype(np.float32) / np.iinfo(dtype).max

            # 如果采样率不匹配，进行重采样
            if frame_rate != target_sample_rate:
                # 使用 scipy 进行重采样
                num_samples = int(len(audio_float) * target_sample_rate / frame_rate)
                audio_float = signal.resample(audio_float, num_samples).astype(np.float32)

            return audio_float

        except Exception as e:
            logger.error(f"Error converting WAV to numpy: {e}")
            return None

    def reset_states(self):
        """重置 VAD 模型状态（用于新的录音会话）"""
        # Hidden state tensor: shape (2, batch_size=1, 128)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        # Context buffer: last N samples from previous chunk
        self._context = np.zeros(0, dtype=np.float32)
        logger.debug("VAD states reset")

    def get_speech_timestamps(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
    ) -> list[dict]:
        """
        获取音频中所有语音片段的时间戳

        Args:
            audio_data: WAV 格式的音频数据
            sample_rate: 采样率 (默认 16000)
            threshold: VAD 置信度阈值 (0-1)
            min_speech_duration_ms: 最短语音段时长（毫秒）
            min_silence_duration_ms: 最短静音段时长（毫秒）

        Returns:
            list[dict]: 语音片段列表，每个元素包含 'start' 和 'end' (采样点)
                       可通过 start/sample_rate 转换为秒数
        """
        if self._session is None:
            self._load_model()

        try:
            audio_array = self._wav_bytes_to_numpy(audio_data, sample_rate)

            if audio_array is None or len(audio_array) == 0:
                return []

            # Window size for VAD
            num_samples = 512 if sample_rate == 16000 else 256
            context_size = 64 if sample_rate == 16000 else 32

            # Reset states for batch processing (use local state for batch)
            state = np.zeros((2, 1, 128), dtype=np.float32)
            context = np.zeros(context_size, dtype=np.float32)

            # Process audio in windows
            speech_probs = []
            for i in range(0, len(audio_array), num_samples):
                chunk = audio_array[i : i + num_samples]
                if len(chunk) < num_samples:
                    # Pad last chunk
                    chunk = np.pad(chunk, (0, num_samples - len(chunk)), mode="constant")

                # Add context to chunk (crucial!)
                audio_with_context = np.concatenate([context, chunk])
                input_data = audio_with_context.reshape(1, -1).astype(np.float32)

                ort_inputs = {
                    "input": input_data,
                    "state": state,
                    "sr": np.array(sample_rate, dtype=np.int64),
                }

                output, state = self._session.run(None, ort_inputs)
                speech_probs.append(float(output[0][0]))

                # Update context for next chunk
                context = chunk[-context_size:].copy()

            # Log probabilities for debugging
            if speech_probs:
                max_prob = max(speech_probs)
                avg_prob = sum(speech_probs) / len(speech_probs)
                above_threshold = sum(1 for p in speech_probs if p > threshold)
                logger.info(
                    f"VAD probs: windows={len(speech_probs)}, max={max_prob:.4f}, avg={avg_prob:.4f}, above_threshold={above_threshold} (threshold={threshold:.2f})"
                )

            # Convert probabilities to timestamps
            min_speech_samples = int(min_speech_duration_ms * sample_rate / 1000)
            min_silence_samples = int(min_silence_duration_ms * sample_rate / 1000)
            min_speech_windows = max(1, min_speech_samples // num_samples)
            min_silence_windows = max(1, min_silence_samples // num_samples)

            speech_timestamps = []
            in_speech = False
            speech_start = 0
            silence_count = 0
            speech_count = 0

            for i, prob in enumerate(speech_probs):
                is_speech = prob > threshold

                if not in_speech:
                    if is_speech:
                        speech_count += 1
                        if speech_count >= min_speech_windows:
                            in_speech = True
                            speech_start = (i - speech_count + 1) * num_samples
                            speech_count = 0
                    else:
                        speech_count = 0
                else:
                    if not is_speech:
                        silence_count += 1
                        if silence_count >= min_silence_windows:
                            # End of speech segment
                            speech_end = (i - silence_count + 1) * num_samples
                            speech_timestamps.append({"start": speech_start, "end": speech_end})
                            in_speech = False
                            silence_count = 0
                    else:
                        silence_count = 0

            # Handle final segment
            if in_speech:
                speech_timestamps.append({"start": speech_start, "end": len(audio_array)})

            logger.info(f"VAD detected {len(speech_timestamps)} speech segments")
            return speech_timestamps

        except Exception as e:
            logger.error(f"Error getting speech timestamps: {e}")
            return []

    def extract_speech_audio(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
    ) -> tuple[bytes, float]:
        """
        从音频中提取纯语音部分

        Args:
            audio_data: WAV 格式的音频数据
            sample_rate: 采样率 (默认 16000)
            threshold: VAD 置信度阈值
            min_speech_duration_ms: 最短语音段时长
            min_silence_duration_ms: 最短静音段时长

        Returns:
            tuple[bytes, float]: (提取后的 WAV 音频, 语音总时长秒数)
        """
        if self._session is None:
            self._load_model()

        try:
            # 获取语音时间戳
            speech_timestamps = self.get_speech_timestamps(
                audio_data, sample_rate, threshold, min_speech_duration_ms, min_silence_duration_ms
            )

            if not speech_timestamps:
                logger.info("No speech detected in audio")
                return b"", 0.0

            # 读取原始 WAV 参数
            with io.BytesIO(audio_data) as wav_file:
                with wave.open(wav_file, "rb") as wf:
                    n_channels = wf.getnchannels()
                    sample_width = wf.getsampwidth()
                    frame_rate = wf.getframerate()
                    n_frames = wf.getnframes()
                    audio_bytes = wf.readframes(n_frames)

            # 转换为 numpy 数组
            if sample_width == 2:
                dtype = np.int16
            elif sample_width == 4:
                dtype = np.int32
            else:
                dtype = np.int16

            audio_array = np.frombuffer(audio_bytes, dtype=dtype)

            # 如果是多声道，reshape
            if n_channels > 1:
                audio_array = audio_array.reshape(-1, n_channels)

            # 计算重采样比例（如果需要）
            resample_ratio = frame_rate / sample_rate if frame_rate != sample_rate else 1.0

            # 提取语音片段
            speech_segments = []
            total_speech_samples = 0

            for ts in speech_timestamps:
                # 时间戳是基于 sample_rate 的，需要转换到原始采样率
                start_sample = int(ts["start"] * resample_ratio)
                end_sample = int(ts["end"] * resample_ratio)

                # 边界检查
                if n_channels > 1:
                    start_sample = min(start_sample, len(audio_array))
                    end_sample = min(end_sample, len(audio_array))
                    segment = audio_array[start_sample:end_sample, :]
                else:
                    start_sample = min(start_sample, len(audio_array))
                    end_sample = min(end_sample, len(audio_array))
                    segment = audio_array[start_sample:end_sample]

                if len(segment) > 0:
                    speech_segments.append(segment)
                    total_speech_samples += len(segment) if n_channels == 1 else len(segment)

            if not speech_segments:
                return b"", 0.0

            # 拼接所有语音片段
            if n_channels > 1:
                concatenated = np.vstack(speech_segments)
            else:
                concatenated = np.concatenate(speech_segments)

            # 转回 WAV 字节
            output = io.BytesIO()
            with wave.open(output, "wb") as wf_out:
                wf_out.setnchannels(n_channels)
                wf_out.setsampwidth(sample_width)
                wf_out.setframerate(frame_rate)
                wf_out.writeframes(concatenated.tobytes())

            speech_duration = total_speech_samples / frame_rate
            logger.info(
                f"Extracted {len(speech_segments)} speech segments, total {speech_duration:.2f}s"
            )

            return output.getvalue(), speech_duration

        except Exception as e:
            logger.error(f"Error extracting speech audio: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return b"", 0.0


# 便捷函数
def get_vad_service() -> VADService:
    """获取 VAD 服务实例"""
    return VADService.get_instance()
