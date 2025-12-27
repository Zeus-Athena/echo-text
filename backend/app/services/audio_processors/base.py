"""
Base Audio Processor
抽象基类 - 所有音频处理策略的父类

核心职责:
1. 强制音频持久化 (保存到数据库)
2. 统一事件输出格式
3. 会话管理
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from loguru import logger


@dataclass
class TranscriptEvent:
    """统一的转录事件格式"""

    text: str
    is_final: bool = False
    speaker: str | None = None  # For diarization
    start_time: float = 0.0
    end_time: float = 0.0
    confidence: float = 1.0


@dataclass
class ProcessorConfig:
    """处理器配置"""

    provider: str
    model: str
    source_lang: str = "en"
    target_lang: str = "zh"
    api_key: str = ""
    api_base_url: str = ""

    # Simulated streaming specific
    silence_threshold: float = 30.0  # 0-100 scale
    buffer_duration: float = 6.0  # seconds

    # True streaming specific
    diarization: bool = False
    smart_format: bool = True
    interim_results: bool = True


class BaseAudioProcessor(ABC):
    """
    音频处理器抽象基类

    所有策略 (Simulated/TrueStreaming) 都必须继承此类。
    基类负责:
    - 音频块的本地缓存 (用于最终保存)
    - 事件回调机制
    - 生命周期管理
    """

    def __init__(
        self,
        config: ProcessorConfig,
        on_transcript: Callable[[TranscriptEvent], Awaitable[None]] | None = None,
        on_error: Callable[[str], Awaitable[None]] | None = None,
    ):
        self.config = config
        self.on_transcript = on_transcript
        self.on_error = on_error

        # === 核心保障: 全量音频缓存 ===
        # 无论用什么策略，都必须保存所有音频数据用于最终存档
        self._all_audio_chunks: list[bytes] = []
        self._header_chunk: bytes = b""

        # 状态管理
        self._is_active = False
        self._start_time: float = 0.0

        logger.info(
            f"BaseAudioProcessor initialized: provider={config.provider}, model={config.model}"
        )

    # ==================== 公共接口 ====================

    async def start(self) -> None:
        """启动处理器"""
        import time

        self._is_active = True
        self._start_time = time.time()
        self._all_audio_chunks = []
        self._header_chunk = b""
        await self._on_start()
        logger.info(f"{self.__class__.__name__} started")

    async def process_audio(self, chunk: bytes) -> None:
        """
        处理音频块

        注意: 此方法会自动保存音频到本地缓存，子类不需要再次保存。
        """
        if not self._is_active:
            logger.warning("Processor not active, ignoring audio chunk")
            return

        # === 核心保障: 无条件保存到本地缓存 ===
        # 这是"双写"的第一步，确保录音数据永不丢失
        self._save_chunk(chunk)

        # 委托给子类处理
        await self._process_chunk(chunk)

    async def stop(self) -> tuple[bytes, bytes]:
        """
        停止处理器并返回完整的音频数据

        Returns:
            tuple[bytes, bytes]: (header_chunk, all_audio_data)
        """
        self._is_active = False
        await self._on_stop()

        # 返回完整的音频数据用于保存
        all_data = b"".join(self._all_audio_chunks)
        logger.info(
            f"{self.__class__.__name__} stopped, total chunks={len(self._all_audio_chunks)}, total_bytes={len(all_data)}"
        )

        return self._header_chunk, all_data

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def elapsed_time(self) -> float:
        """获取已录制时间 (秒)"""
        import time

        if not self._is_active or self._start_time == 0:
            return 0.0
        return time.time() - self._start_time

    @property
    def chunk_count(self) -> int:
        """获取已接收的音频块数量"""
        return len(self._all_audio_chunks)

    @property
    def header_chunk(self) -> bytes:
        """获取 WebM 头部块"""
        return self._header_chunk

    # ==================== 内部方法 ====================

    def _save_chunk(self, chunk: bytes) -> None:
        """保存音频块到本地缓存"""
        # 第一个块通常是 WebM 头部
        if not self._header_chunk:
            self._header_chunk = chunk

        self._all_audio_chunks.append(chunk)

    async def _emit_transcript(self, event: TranscriptEvent) -> None:
        """发送转录事件"""
        if self.on_transcript:
            try:
                await self.on_transcript(event)
            except Exception as e:
                logger.error(f"Error in transcript callback: {e}")

    async def _emit_error(self, message: str) -> None:
        """发送错误事件"""
        if self.on_error:
            try:
                await self.on_error(message)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")

    # ==================== 抽象方法 (子类实现) ====================

    @abstractmethod
    async def _on_start(self) -> None:
        """子类启动逻辑"""
        pass

    @abstractmethod
    async def _process_chunk(self, chunk: bytes) -> None:
        """
        子类处理音频块逻辑

        注意: 此时音频已经被基类保存到缓存，子类只需处理业务逻辑。
        """
        pass

    @abstractmethod
    async def _on_stop(self) -> None:
        """子类停止逻辑"""
        pass
