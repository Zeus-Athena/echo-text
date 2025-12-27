"""
Balance Check API Tests
测试余额查询功能
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLLMBalanceCheck:
    """LLM Service balance check tests"""

    def test_check_balance_no_api_key(self):
        """验证：无 API Key 时返回错误"""
        from app.services.llm_service import LLMService

        service = LLMService(None)
        # Since it's async, we need to run it
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(service.check_balance())
        assert "error" in result

    @pytest.mark.asyncio
    async def test_check_balance_siliconflow_success(self):
        """验证：SiliconFlow 余额查询成功"""
        from app.services.llm_service import LLMService

        mock_config = MagicMock()
        mock_config.llm_provider = "siliconflow"
        mock_config.llm_siliconflow_api_key = "test-key"
        mock_config.llm_base_url = None
        mock_config.llm_model = "test-model"

        service = LLMService(mock_config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"balance": "13.64"}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await service.check_balance()

        assert result["balance"] == 13.64
        assert result["currency"] == "CNY"
        assert result["provider"] == "SiliconFlow"

    @pytest.mark.asyncio
    async def test_check_balance_unsupported_provider(self):
        """验证：不支持的 provider 返回提示信息"""
        from app.services.llm_service import LLMService

        mock_config = MagicMock()
        mock_config.llm_provider = "groq"
        mock_config.llm_groq_api_key = "test-key"
        mock_config.llm_base_url = None
        mock_config.llm_model = "test-model"

        service = LLMService(mock_config)
        result = await service.check_balance()

        assert "message" in result
        assert "not supported" in result["message"]


class TestSTTBalanceCheck:
    """STT Service balance check tests"""

    @pytest.mark.asyncio
    async def test_check_balance_no_api_key(self):
        """验证：无 API Key 时返回错误"""
        from app.services.stt_service import STTService

        service = STTService(None)
        result = await service.check_balance()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_check_balance_deepgram_success(self):
        """验证：Deepgram 余额查询成功"""
        from app.services.stt_service import STTService

        mock_config = MagicMock()
        mock_config.stt_provider = "deepgram"
        mock_config.stt_deepgram_api_key = "test-key"
        mock_config.stt_base_url = None
        mock_config.stt_model = "nova-2"

        service = STTService(mock_config)

        # Mock projects response
        mock_projects_resp = MagicMock()
        mock_projects_resp.status_code = 200
        mock_projects_resp.json.return_value = {"projects": [{"project_id": "proj-123"}]}

        # Mock balances response
        mock_balance_resp = MagicMock()
        mock_balance_resp.status_code = 200
        mock_balance_resp.json.return_value = {"balances": [{"amount": 199.43}]}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[mock_projects_resp, mock_balance_resp])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await service.check_balance()

        assert result["balance"] == 199.43
        assert result["currency"] == "USD"
        assert result["provider"] == "Deepgram"


class TestBalanceAPI:
    """API endpoint tests"""

    @pytest.mark.asyncio
    async def test_balance_endpoint_invalid_service_type(self):
        """验证：无效 service_type 返回 400"""
        from fastapi import HTTPException

        from app.api.v1.users import check_balance

        with pytest.raises(HTTPException) as exc_info:
            await check_balance(
                service_type="invalid",
                current_user=MagicMock(),
                db=MagicMock(),
            )

        assert exc_info.value.status_code == 400
