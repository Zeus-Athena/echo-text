"""
WebSocket Connection Manager
连接管理器
"""

from __future__ import annotations

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """管理 WebSocket 连接"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """接受并注册连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.debug(f"WebSocket connected: {client_id}")

    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.debug(f"WebSocket disconnected: {client_id}")

    def get(self, client_id: str) -> WebSocket | None:
        """获取连接"""
        return self.active_connections.get(client_id)

    def is_connected(self, client_id: str) -> bool:
        """检查是否已连接"""
        return client_id in self.active_connections

    async def send_json(self, client_id: str, data: dict) -> bool:
        """发送 JSON 消息，返回是否成功"""
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return False

        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to {client_id}: {e}")
            self.disconnect(client_id)
            return False

    async def send_transcript(
        self,
        client_id: str,
        text: str,
        is_final: bool,
        speaker: str | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        transcript_id: str = "",
    ) -> bool:
        """发送转录结果"""
        data = {
            "type": "transcript",
            "text": text,
            "is_final": is_final,
        }
        if speaker:
            data["speaker"] = speaker
        if start_time is not None:
            data["start_time"] = start_time
        if end_time is not None:
            data["end_time"] = end_time
        if transcript_id:
            data["transcript_id"] = transcript_id
        return await self.send_json(client_id, data)

    async def send_translation(
        self,
        client_id: str,
        text: str,
        is_final: bool,
        transcript_id: str = "",
    ) -> bool:
        """发送翻译结果"""
        data = {
            "type": "translation",
            "text": text,
            "is_final": is_final,
        }
        if transcript_id:
            data["transcript_id"] = transcript_id
        return await self.send_json(client_id, data)

    async def send_status(self, client_id: str, message: str) -> bool:
        """发送状态消息"""
        return await self.send_json(
            client_id,
            {
                "type": "status",
                "message": message,
            },
        )

    async def send_error(self, client_id: str, message: str) -> bool:
        """发送错误消息"""
        return await self.send_json(
            client_id,
            {
                "type": "error",
                "message": message,
            },
        )

    async def send_pong(self, client_id: str) -> bool:
        """发送 pong 响应"""
        return await self.send_json(client_id, {"type": "pong"})


# 全局连接管理器实例
manager = ConnectionManager()
