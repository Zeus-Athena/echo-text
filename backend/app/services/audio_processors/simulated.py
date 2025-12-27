"""
Simulated Streaming Processor
伪流式策略 - 适用于 Groq/OpenAI Whisper

工作原理:
1. 累积音频块到缓冲区
2. 使用 VAD 检测静音/停顿
3. 达到阈值后切片发送 HTTP 请求
4. 返回完整的转录结果
"""

import asyncio
import time
from collections.abc import Awaitable, Callable

from loguru import logger

from app.services.stt_service import STTService
from app.services.vad_service import get_vad_service

from .base import BaseAudioProcessor, ProcessorConfig, TranscriptEvent


class SimulatedStreamingProcessor(BaseAudioProcessor):
    """
    伪流式处理器

    从 ws.py 中提取的原有逻辑，封装为独立的策略类。
    适用于不支持 WebSocket 流的 STT API (Groq, OpenAI)。
    """

    def __init__(
        self,
        config: ProcessorConfig,
        stt_service: STTService,
        on_transcript: Callable[[TranscriptEvent], Awaitable[None]] | None = None,
        on_error: Callable[[str], Awaitable[None]] | None = None,
    ):
        super().__init__(config, on_transcript, on_error)

        self.stt_service = stt_service

        # STT 处理状态
        self._stt_last_index = 0  # 上次处理的音频块索引
        self._pending_tasks: list[asyncio.Task] = []

        # 弹性窗口参数
        buffer_duration = max(3.0, config.buffer_duration)  # 至少 3 秒
        self._min_chunks = max(4, int(buffer_duration * 2))  # 每块约 0.5s
        self._max_chunks = self._min_chunks * 2

        logger.info(
            f"SimulatedStreamingProcessor: min_chunks={self._min_chunks}, max_chunks={self._max_chunks}"
        )

    async def _on_start(self) -> None:
        """启动时重置状态"""
        self._stt_last_index = 0
        self._pending_tasks = []

        # 重置 VAD 状态
        vad_service = get_vad_service()
        vad_service.reset_states()

    async def _process_chunk(self, chunk: bytes) -> None:
        """
        处理音频块

        实现弹性窗口逻辑:
        - Phase 1: 积累到 min_chunks
        - Phase 2: 在 min~max 之间检测静音
        - Phase 3: 达到 max 强制发送
        """
        total_chunks = self.chunk_count
        new_chunk_count = total_chunks - self._stt_last_index

        # 日志记录
        if total_chunks == 1:
            logger.info(f"[T+{self.elapsed_time:.1f}s] First chunk received")
        elif total_chunks % 10 == 0:
            logger.debug(
                f"[T+{self.elapsed_time:.1f}s] Total: {total_chunks}, pending: {new_chunk_count}"
            )

        should_send = False
        send_reason = ""

        # Phase 1: 未达到最小值，继续积累
        if new_chunk_count < self._min_chunks:
            should_send = False

        # Phase 2: 在弹性区间内，检测静音
        elif new_chunk_count < self._max_chunks:
            should_send, send_reason = await self._check_silence()

        # Phase 3: 达到最大值，强制发送
        if new_chunk_count >= self._max_chunks:
            should_send = True
            send_reason = f"max window reached ({new_chunk_count} >= {self._max_chunks})"

        # 发送处理
        if should_send:
            logger.info(f"[T+{self.elapsed_time:.1f}s] STT triggered: {send_reason}")
            await self._send_for_transcription()

    async def _check_silence(self) -> tuple[bool, str]:
        """检测是否有静音（使用 VAD）"""
        try:
            from app.utils.audio_utils import convert_webm_to_wav

            # 获取最后 ~1 秒的音频
            chunks = self._all_audio_chunks
            recent_chunks = chunks[-2:] if len(chunks) >= 2 else chunks[-1:]
            recent_audio = b"".join(recent_chunks)

            # 添加头部
            if self._header_chunk and recent_chunks[0] != self._header_chunk:
                recent_audio = self._header_chunk + recent_audio

            # 转换为 WAV
            recent_wav = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, convert_webm_to_wav, recent_audio),
                timeout=3,
            )

            if not recent_wav:
                return False, ""

            # VAD 检测
            vad_service = get_vad_service()
            speech_prob = vad_service.get_speech_probability(recent_wav)

            # 阈值判断
            vad_threshold = max(0.0, min(1.0, self.config.silence_threshold / 100.0))

            if speech_prob < vad_threshold:
                return (
                    True,
                    f"silence detected (prob={speech_prob:.2f} < threshold={vad_threshold:.2f})",
                )

            return False, ""

        except TimeoutError:
            logger.warning("VAD check timeout")
            return False, ""
        except Exception as e:
            logger.warning(f"VAD check error: {e}")
            return False, ""

    async def _send_for_transcription(self) -> None:
        """发送音频进行转录 (非阻塞)"""
        # 获取新的音频块
        new_chunks = self._all_audio_chunks[self._stt_last_index :]
        if not new_chunks:
            return

        audio_data = b"".join(new_chunks)

        # 更新索引 (在开始任务前更新，避免重复处理)
        self._stt_last_index = len(self._all_audio_chunks)
        elapsed = self.elapsed_time

        # 创建后台任务
        task = asyncio.create_task(self._process_audio_batch(audio_data, elapsed))
        self._pending_tasks.append(task)

    async def _process_audio_batch(self, audio_data: bytes, elapsed_time: float) -> None:
        """处理音频批次 (后台任务)"""
        from app.utils.audio_utils import convert_webm_to_wav

        try:
            # 添加头部
            if self._header_chunk and not audio_data.startswith(self._header_chunk):
                audio_data = self._header_chunk + audio_data

            # 转换为 WAV
            wav_data = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, convert_webm_to_wav, audio_data),
                timeout=10,
            )

            if not wav_data:
                logger.warning("Audio conversion returned None")
                return

            # VAD 过滤
            vad_service = get_vad_service()
            vad_threshold = max(0.0, min(1.0, self.config.silence_threshold / 100.0))

            speech_audio, speech_duration = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: vad_service.extract_speech_audio(wav_data, threshold=vad_threshold),
                ),
                timeout=10,
            )

            logger.info(f"[T+{elapsed_time:.1f}s] VAD extracted {speech_duration:.2f}s of speech")

            if not speech_audio or speech_duration <= 0.3:
                logger.info(f"[T+{elapsed_time:.1f}s] No speech detected, skipping STT")
                return

            # STT 调用
            stt_start = time.time()
            result = await asyncio.wait_for(
                self.stt_service.transcribe(
                    speech_audio, language=self.config.source_lang, filename="speech.wav"
                ),
                timeout=30,
            )
            stt_time = time.time() - stt_start

            text = result.get("text", "").strip()
            logger.info(
                f"[T+{elapsed_time:.1f}s] STT returned in {stt_time:.2f}s: '{text[:80] if text else 'empty'}'"
            )

            if not text:
                return

            # 过滤幻觉
            if not self._is_valid_text(text):
                logger.debug(f"Filtered hallucination: '{text}'")
                return

            # 发送事件
            event = TranscriptEvent(
                text=text,
                is_final=True,  # 伪流式只有 Final 结果
                start_time=elapsed_time,
                end_time=elapsed_time + speech_duration,
            )
            await self._emit_transcript(event)

        except TimeoutError:
            logger.error("Audio processing timeout")
            await self._emit_error("处理超时")
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            import traceback

            logger.error(traceback.format_exc())

    def _is_valid_text(self, text: str) -> bool:
        """检查文本是否有效 (过滤幻觉)"""
        if len(text) <= 3:
            return False

        if all(c in ".?!,;:。？！，；：" for c in text):
            return False

        hallucinations = [
            "thank you.",
            "thank you",
            "thanks.",
            "thanks",
            "so.",
            "so",
            "you.",
            "you",
            "yeah.",
            "yeah",
            "okay.",
            "okay",
            "ok.",
            "ok",
            "bye.",
            "bye",
            "谢谢。",
            "谢谢",
            "好的。",
            "好的",
            "嗯。",
            "嗯",
        ]

        return text.lower() not in hallucinations

    async def _on_stop(self) -> None:
        """停止时处理剩余音频"""
        # 处理最后的未发送音频
        remaining_chunks = len(self._all_audio_chunks) - self._stt_last_index
        if remaining_chunks > 0:
            logger.info(f"Processing remaining {remaining_chunks} chunks")
            await self._send_for_transcription()

        # 等待所有后台任务完成
        if self._pending_tasks:
            logger.info(f"Waiting for {len(self._pending_tasks)} pending tasks")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._pending_tasks, return_exceptions=True), timeout=30
                )
            except TimeoutError:
                logger.warning("Timeout waiting for pending tasks")
