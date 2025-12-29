"""
True Streaming Processor
真流式策略 - 适用于 Deepgram

工作原理:
1. 建立到 Deepgram 的 WebSocket 连接
2. 实时透传音频块 (Zero buffering)
3. 接收实时转录结果 (Interim + Final)
4. 支持说话人区分 (Diarization)

注意:
- 使用轻量级 VAD 过滤死寂静音 (节省带宽)
- 音频依然会被基类保存到本地 (双写保障)
"""

import asyncio
import json
from collections.abc import Awaitable, Callable

from loguru import logger

from .base import BaseAudioProcessor, ProcessorConfig, TranscriptEvent


class TrueStreamingProcessor(BaseAudioProcessor):
    """
    真流式处理器

    适用于支持 WebSocket 流的 STT API (Deepgram, Azure)。
    特点:
    - 超低延迟 (音频直接透传)
    - 支持 Interim 结果 (灰色文字)
    - 支持说话人区分
    """

    def __init__(
        self,
        config: ProcessorConfig,
        on_transcript: Callable[[TranscriptEvent], Awaitable[None]] | None = None,
        on_error: Callable[[str], Awaitable[None]] | None = None,
    ):
        super().__init__(config, on_transcript, on_error)

        self._upstream_ws = None  # Deepgram WebSocket connection
        self._listener_task: asyncio.Task | None = None
        self._silence_counter = 0  # 连续静音计数器 (用于僵尸检测)
        self._last_speech_time = 0.0

        # 暂停状态
        self._is_paused = False
        self._pause_start_time = 0.0
        self._keepalive_task: asyncio.Task | None = None
        self._on_auto_stop: Callable[[], Awaitable[None]] | None = None

        # 轻量级 VAD 门控阈值
        self._silence_gate_threshold = 0.1  # 极低阈值，只过滤绝对静音

        logger.info(
            f"TrueStreamingProcessor initialized: model={config.model}, diarization={config.diarization}"
        )

    async def _on_start(self) -> None:
        """启动 Deepgram 连接"""
        import time

        self._last_speech_time = time.time()
        self._silence_counter = 0

        # 连接 Deepgram
        await self._connect_deepgram()

        # 启动监听任务
        if self._upstream_ws:
            self._listener_task = asyncio.create_task(self._listen_upstream())

    async def _connect_deepgram(self) -> None:
        """建立 Deepgram WebSocket 连接"""
        try:
            import websockets

            model = self.config.model

            # Flux 模型需要使用 v2 endpoint
            is_flux = model.startswith("flux")

            # 构建 URL 参数
            # 注意: 浏览器发送的是 WebM/Opus 格式，Deepgram 可以自动检测
            # 不指定 encoding 让 Deepgram 自动检测容器格式
            params = {
                "model": model,
                "language": self.config.source_lang,
                "punctuate": "true",
                "interim_results": str(self.config.interim_results).lower(),
                # 移除 encoding 和 sample_rate，让 Deepgram 自动检测 WebM/Opus
            }

            if self.config.diarization and not is_flux:
                # Flux 可能不支持 diarization
                params["diarize"] = "true"

            if self.config.smart_format:
                params["smart_format"] = "true"

            query_string = "&".join(f"{k}={v}" for k, v in params.items())

            # 选择正确的端点
            if is_flux:
                base_url = "wss://api.deepgram.com/v2/listen"
                logger.info(f"Using v2 endpoint for Flux model: {model}")
            else:
                base_url = "wss://api.deepgram.com/v1/listen"

            url = f"{base_url}?{query_string}"

            # 建立连接
            headers = {"Authorization": f"Token {self.config.api_key}"}

            self._upstream_ws = await websockets.connect(
                url,
                additional_headers=headers,  # websockets v15+ uses additional_headers
                ping_interval=20,
                ping_timeout=10,
            )

            logger.info(
                f"Connected to Deepgram: model={model}, endpoint={'v2' if is_flux else 'v1'}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            await self._emit_error(f"Deepgram 连接失败: {str(e)}")
            self._upstream_ws = None

    async def _process_chunk(self, chunk: bytes) -> None:
        """
        处理音频块 - 直接透传给 Deepgram

        注意: 基类已经保存了音频，这里只需要透传
        """
        if not self._upstream_ws:
            return

        # 可选: 轻量级静音检测 (节省带宽)
        # 注意: 这里只过滤绝对静音，真正的 VAD 由 Deepgram 处理
        if await self._is_silence(chunk):
            self._silence_counter += 1

            # 僵尸连接检测: 5 分钟无语音自动断开
            import time

            if time.time() - self._last_speech_time > 300:  # 5 minutes
                logger.warning("Zombie connection detected, closing")
                await self._emit_error("长时间无语音，连接已断开")
                await self.stop()
                return

            # 即使是静音，也定期发送一些数据保持连接活性
            if self._silence_counter % 10 != 0:
                return
        else:
            self._silence_counter = 0
            import time

            self._last_speech_time = time.time()

        # 透传给 Deepgram
        try:
            await self._upstream_ws.send(chunk)
        except Exception as e:
            logger.error(f"Failed to send to Deepgram: {e}")

    async def _is_silence(self, chunk: bytes) -> bool:
        """轻量级静音检测 (仅检测绝对静音)"""
        # 简单的音量检测 (不使用 VAD，太重)
        # 计算 RMS
        import struct

        try:
            # 假设是 16-bit PCM
            samples = struct.unpack(f"{len(chunk) // 2}h", chunk)
            if not samples:
                return True

            rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5

            # 极低阈值 (只过滤绝对静音)
            return rms < 100  # 16-bit 范围是 -32768 ~ 32767

        except Exception:
            # 解析失败时不过滤
            return False

    async def _listen_upstream(self) -> None:
        """监听 Deepgram 返回的结果"""
        if not self._upstream_ws:
            return

        try:
            async for message in self._upstream_ws:
                if not self._is_active:
                    break

                try:
                    data = json.loads(message)
                    await self._handle_deepgram_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from Deepgram: {message[:100]}")

        except Exception as e:
            if self._is_active:
                logger.error(f"Deepgram listener error: {e}")
                await self._emit_error(f"Deepgram 连接断开: {str(e)}")

    async def _handle_deepgram_message(self, data: dict) -> None:
        """处理 Deepgram 返回的消息"""
        msg_type = data.get("type", "")

        if msg_type == "Results":
            channel = data.get("channel", {})
            alternatives = channel.get("alternatives", [])

            if not alternatives:
                return

            alt = alternatives[0]
            text = alt.get("transcript", "").strip()

            if not text:
                return

            is_final = data.get("is_final", False)

            # 说话人信息 (如果启用了 diarization)
            speaker = None
            words = alt.get("words", [])
            if words and "speaker" in words[0]:
                speaker = f"Speaker {words[0]['speaker']}"

            # 为 Final 消息生成唯一 ID（用于关联翻译）
            import uuid

            transcript_id = str(uuid.uuid4()) if is_final else ""

            # 发送事件
            event = TranscriptEvent(
                text=text,
                is_final=is_final,
                speaker=speaker,
                start_time=data.get("start", 0),
                end_time=data.get("start", 0) + data.get("duration", 0),
                confidence=alt.get("confidence", 1.0),
                transcript_id=transcript_id,
            )

            await self._emit_transcript(event)

            if is_final:
                logger.info(f"[Final] {text[:80]}")
            else:
                logger.debug(f"[Interim] {text[:50]}...")

        elif msg_type == "Metadata":
            logger.info(f"Deepgram metadata: {data}")

        elif msg_type == "SpeechStarted":
            logger.debug("Speech started")

        elif msg_type == "UtteranceEnd":
            logger.debug("Utterance ended")

    async def pause(self, on_auto_stop: Callable[[], Awaitable[None]] | None = None) -> None:
        """暂停录制，启动 KeepAlive 保持 Deepgram 连接"""
        if self._is_paused:
            return

        import time

        self._is_paused = True
        self._pause_start_time = time.time()
        self._on_auto_stop = on_auto_stop

        # 启动 KeepAlive 任务
        if self._upstream_ws and not self._keepalive_task:
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
            logger.info("Paused: KeepAlive started")

    async def resume(self) -> None:
        """恢复录制，停止 KeepAlive"""
        if not self._is_paused:
            return

        self._is_paused = False
        self._pause_start_time = 0.0

        # 停止 KeepAlive 任务
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None
            logger.info("Resumed: KeepAlive stopped")

    async def _keepalive_loop(self) -> None:
        """KeepAlive 循环：每 5 秒发送心跳，10 分钟后自动停止"""
        import time

        KEEPALIVE_INTERVAL = 5  # 秒
        PAUSE_TIMEOUT = 600  # 10 分钟

        try:
            while self._is_paused and self._upstream_ws:
                # 检查是否超过 10 分钟
                elapsed = time.time() - self._pause_start_time
                if elapsed > PAUSE_TIMEOUT:
                    logger.warning(f"Pause timeout ({PAUSE_TIMEOUT}s), auto stopping")
                    await self._emit_error("录制已自动结束（暂停超过10分钟）")
                    if self._on_auto_stop:
                        await self._on_auto_stop()
                    return

                # 发送 KeepAlive
                try:
                    await self._upstream_ws.send(json.dumps({"type": "KeepAlive"}))
                    logger.debug(f"KeepAlive sent (paused {elapsed:.0f}s)")
                except Exception as e:
                    logger.warning(f"KeepAlive failed: {e}")
                    break

                await asyncio.sleep(KEEPALIVE_INTERVAL)

        except asyncio.CancelledError:
            pass

    async def _on_stop(self) -> None:
        """停止并关闭连接"""
        # 停止 KeepAlive
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass

        # 发送 CloseStream 信号
        if self._upstream_ws:
            try:
                # Deepgram 需要发送空的 JSON 来关闭
                await self._upstream_ws.send(json.dumps({"type": "CloseStream"}))
                await asyncio.sleep(0.5)  # 等待最后的结果
            except Exception as e:
                logger.warning(f"Error sending close signal: {e}")

            try:
                await self._upstream_ws.close()
            except Exception:
                pass

            self._upstream_ws = None

        # 取消监听任务
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
