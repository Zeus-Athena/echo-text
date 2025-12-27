"""
Tests for vad_service.py
VAD 服务单元测试
"""

import io
import wave

import numpy as np
import pytest


def create_wav_bytes(samples: np.ndarray, sample_rate: int = 16000) -> bytes:
    """创建 WAV 格式字节"""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        # Convert float [-1, 1] to int16
        int_samples = (samples * 32767).astype(np.int16)
        wav.writeframes(int_samples.tobytes())
    return buffer.getvalue()


class TestVADService:
    """VADService 单元测试"""

    @pytest.fixture
    def vad_service(self):
        """获取 VAD 服务实例"""
        from app.services.vad_service import get_vad_service

        return get_vad_service()

    @pytest.fixture
    def silence_wav(self):
        """创建静音 WAV"""
        samples = np.zeros(512, dtype=np.float32)
        return create_wav_bytes(samples)

    @pytest.fixture
    def speech_wav(self):
        """创建模拟语音 WAV (正弦波)"""
        t = np.linspace(0, 0.032, 512)  # 32ms at 16kHz
        samples = (np.sin(2 * np.pi * 300 * t) * 0.5).astype(np.float32)
        return create_wav_bytes(samples)

    @pytest.fixture
    def long_silence_wav(self):
        """创建较长静音 WAV (1秒)"""
        samples = np.zeros(16000, dtype=np.float32)
        return create_wav_bytes(samples)

    @pytest.fixture
    def long_speech_wav(self):
        """创建较长语音 WAV (1秒)"""
        t = np.linspace(0, 1.0, 16000)
        samples = (np.sin(2 * np.pi * 300 * t) * 0.5).astype(np.float32)
        return create_wav_bytes(samples)

    # === 基础功能测试 ===

    def test_get_instance_returns_same_instance(self):
        """get_instance 返回同一实例 (单例模式)"""
        from app.services.vad_service import VADService

        instance1 = VADService.get_instance()
        instance2 = VADService.get_instance()

        assert instance1 is instance2

    def test_get_vad_service_returns_instance(self, vad_service):
        """get_vad_service 返回实例"""
        assert vad_service is not None

    def test_model_loaded(self, vad_service):
        """模型应已加载"""
        from app.services.vad_service import VADService

        assert VADService._session is not None

    # === get_speech_probability 测试 ===

    def test_get_speech_probability_returns_float(self, vad_service, silence_wav):
        """get_speech_probability 返回 float"""
        vad_service.reset_states()
        prob = vad_service.get_speech_probability(silence_wav)

        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

    def test_get_speech_probability_silence_low(self, vad_service, silence_wav):
        """静音应该返回低概率"""
        vad_service.reset_states()
        prob = vad_service.get_speech_probability(silence_wav)

        assert prob < 0.5  # 静音概率应较低

    def test_get_speech_probability_short_audio_returns_low(self, vad_service):
        """过短音频返回低概率 (模型仍会处理)"""
        # 创建只有 100 样本的 WAV (少于 512)
        samples = np.zeros(100, dtype=np.float32)
        short_wav = create_wav_bytes(samples)

        prob = vad_service.get_speech_probability(short_wav)

        # 短音频应该返回很低的概率
        assert prob < 0.1

    def test_get_speech_probability_invalid_wav_returns_zero(self, vad_service):
        """无效 WAV 返回 0"""
        invalid_data = b"not a wav file"

        prob = vad_service.get_speech_probability(invalid_data)

        assert prob == 0.0

    def test_get_speech_probability_empty_returns_zero(self, vad_service):
        """空数据返回 0"""
        prob = vad_service.get_speech_probability(b"")

        assert prob == 0.0

    # === is_speech 测试 ===

    def test_is_speech_returns_bool(self, vad_service, silence_wav):
        """is_speech 返回 bool"""
        vad_service.reset_states()
        result = vad_service.is_speech(silence_wav)

        assert isinstance(result, bool)

    def test_is_speech_silence_false(self, vad_service, silence_wav):
        """静音返回 False"""
        vad_service.reset_states()
        result = vad_service.is_speech(silence_wav)

        assert result is False

    # === reset_states 测试 ===

    def test_reset_states_resets_context(self, vad_service):
        """reset_states 重置状态"""
        # 先处理一些音频
        samples = np.random.randn(512).astype(np.float32) * 0.1
        wav = create_wav_bytes(samples)
        vad_service.get_speech_probability(wav)

        # 重置
        vad_service.reset_states()

        # 验证 context 被重置
        assert np.all(vad_service._context == 0)

    # === _wav_bytes_to_numpy 测试 ===

    def test_wav_bytes_to_numpy_correct_shape(self, vad_service, silence_wav):
        """_wav_bytes_to_numpy 返回正确形状"""
        result = vad_service._wav_bytes_to_numpy(silence_wav)

        assert isinstance(result, np.ndarray)
        assert result.ndim == 1
        assert len(result) == 512

    def test_wav_bytes_to_numpy_normalized(self, vad_service):
        """_wav_bytes_to_numpy 归一化到 [-1, 1]"""
        # 创建最大振幅的 WAV
        samples = np.ones(512, dtype=np.float32)
        wav = create_wav_bytes(samples)

        result = vad_service._wav_bytes_to_numpy(wav)

        assert result.max() <= 1.0
        assert result.min() >= -1.0

    def test_wav_bytes_to_numpy_resamples(self, vad_service):
        """_wav_bytes_to_numpy 重采样"""
        # 创建 8kHz 的 WAV
        samples = np.zeros(256, dtype=np.float32)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(8000)
            int_samples = (samples * 32767).astype(np.int16)
            wav.writeframes(int_samples.tobytes())
        wav_8k = buffer.getvalue()

        # 转换到 16kHz
        result = vad_service._wav_bytes_to_numpy(wav_8k, target_sample_rate=16000)

        # 8kHz 256 样本 -> 16kHz 应该是 512 样本
        assert len(result) == 512

    def test_wav_bytes_to_numpy_stereo_to_mono(self, vad_service):
        """_wav_bytes_to_numpy 立体声转单声道"""
        # 创建立体声 WAV
        samples_l = np.zeros(512, dtype=np.float32)
        samples_r = np.ones(512, dtype=np.float32) * 0.5
        stereo = np.column_stack([samples_l, samples_r]).flatten()

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            int_samples = (stereo * 32767).astype(np.int16)
            wav.writeframes(int_samples.tobytes())
        stereo_wav = buffer.getvalue()

        result = vad_service._wav_bytes_to_numpy(stereo_wav)

        # 应该是单声道
        assert result.ndim == 1

    # === get_speech_timestamps 测试 ===

    def test_get_speech_timestamps_returns_list(self, vad_service, long_silence_wav):
        """get_speech_timestamps 返回列表"""
        vad_service.reset_states()
        result = vad_service.get_speech_timestamps(long_silence_wav)

        assert isinstance(result, list)

    def test_get_speech_timestamps_silence_empty(self, vad_service, long_silence_wav):
        """静音返回空列表"""
        vad_service.reset_states()
        result = vad_service.get_speech_timestamps(long_silence_wav)

        assert len(result) == 0

    def test_get_speech_timestamps_format(self, vad_service, long_speech_wav):
        """get_speech_timestamps 格式正确"""
        vad_service.reset_states()
        result = vad_service.get_speech_timestamps(long_speech_wav, threshold=0.1)

        if len(result) > 0:
            assert "start" in result[0]
            assert "end" in result[0]
            assert isinstance(result[0]["start"], int)
            assert isinstance(result[0]["end"], int)

    # === extract_speech_audio 测试 ===

    def test_extract_speech_audio_returns_tuple(self, vad_service, long_silence_wav):
        """extract_speech_audio 返回元组 (bytes, float)"""
        vad_service.reset_states()
        result = vad_service.extract_speech_audio(long_silence_wav)

        # API 返回 (audio_bytes, duration) 元组
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_extract_speech_audio_silence_returns_empty(self, vad_service, long_silence_wav):
        """静音返回空 bytes"""
        vad_service.reset_states()
        result = vad_service.extract_speech_audio(long_silence_wav)

        # 静音时返回 (b'', 0.0)
        assert result[0] == b""
        assert result[1] == 0.0


class TestVADServiceEdgeCases:
    """VAD 服务边界情况测试"""

    @pytest.fixture
    def vad_service(self):
        from app.services.vad_service import get_vad_service

        return get_vad_service()

    def test_various_sample_rates(self, vad_service):
        """测试不同采样率"""
        for sample_rate in [8000, 16000, 44100, 48000]:
            samples = np.zeros(sample_rate // 10, dtype=np.float32)  # 100ms
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                int_samples = (samples * 32767).astype(np.int16)
                wav.writeframes(int_samples.tobytes())

            vad_service.reset_states()
            prob = vad_service.get_speech_probability(buffer.getvalue(), sample_rate)
            assert 0.0 <= prob <= 1.0

    def test_consecutive_calls_maintain_context(self, vad_service):
        """连续调用维护上下文"""
        vad_service.reset_states()

        samples = np.zeros(512, dtype=np.float32)
        wav = create_wav_bytes(samples)

        # 第一次调用
        prob1 = vad_service.get_speech_probability(wav)

        # 第二次调用应该使用更新后的上下文
        prob2 = vad_service.get_speech_probability(wav)

        # 两次调用都应该返回有效值
        assert 0.0 <= prob1 <= 1.0
        assert 0.0 <= prob2 <= 1.0
