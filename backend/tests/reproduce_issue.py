from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.config import test_llm_config
from app.models.user import User, UserConfig
from app.schemas.user import ConfigTestRequest


@pytest.mark.asyncio
async def test_llm_config_key_resolution():
    """
    Verify that test_llm_config correctly resolves masked API keys ("***")
    for specific providers (SiliconFlow Global, Fireworks).
    """

    # Mock user and config
    mock_user = User(id="test_user_id", role="user")
    mock_config = UserConfig(
        user_id="test_user_id",
        llm_api_key="generic_key",
        llm_groq_api_key="groq_key",
        llm_siliconflow_api_key="siliconflow_cn_key",
        llm_siliconflowglobal_api_key="siliconflow_global_key",
        llm_fireworks_api_key="fireworks_key",
    )

    # Mock DB session (not used deeply because we mock get_effective_config)
    mock_db = AsyncMock()

    # Mock get_effective_config to return our mock_config
    with patch("app.api.v1.config.get_effective_config", new=AsyncMock(return_value=mock_config)):
        # Mock openai.AsyncOpenAI directly since it is imported inside the function
        with patch("openai.AsyncOpenAI") as MockAsyncOpenAI:
            # Setup the Mock Client instance
            mock_client_instance = MockAsyncOpenAI.return_value
            mock_client_instance.models.list = AsyncMock()
            mock_client_instance.chat.completions.create = AsyncMock(
                return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="OK"))])
            )

            # --- Test Case 1: SiliconFlow Global ---
            request_sf_global = ConfigTestRequest(
                provider="SiliconFlowGlobal",
                api_key="***",
                base_url="https://api.siliconflow.com/v1",
                model="test_model",
            )

            await test_llm_config(request_sf_global, current_user=mock_user, db=mock_db)

            # Verify correct key was used
            # We look at the call args of AsyncOpenAI constructor
            args, kwargs = MockAsyncOpenAI.call_args
            assert (
                kwargs.get("api_key") == "siliconflow_global_key"
            ), f"Expected 'siliconflow_global_key' for SiliconFlow Global, but got '{kwargs.get('api_key')}'"

            print("\n✅ SiliconFlow Global key resolution verified.")

            # --- Test Case 2: Fireworks ---
            request_fireworks = ConfigTestRequest(
                provider="Fireworks",
                api_key="***",
                base_url="https://api.fireworks.ai/inference/v1",
                model="test_model",
            )

            await test_llm_config(request_fireworks, current_user=mock_user, db=mock_db)

            args, kwargs = MockAsyncOpenAI.call_args
            assert (
                kwargs.get("api_key") == "fireworks_key"
            ), f"Expected 'fireworks_key' for Fireworks, but got '{kwargs.get('api_key')}'"

            print("✅ Fireworks key resolution verified.")

            # --- Test Case 3: SiliconFlow (CN) - Regression Check ---
            request_sf_cn = ConfigTestRequest(
                provider="SiliconFlow",
                api_key="***",
                base_url="https://api.siliconflow.cn/v1",
                model="test_model",
            )

            await test_llm_config(request_sf_cn, current_user=mock_user, db=mock_db)

            args, kwargs = MockAsyncOpenAI.call_args
            assert (
                kwargs.get("api_key") == "siliconflow_cn_key"
            ), f"Expected 'siliconflow_cn_key' for SiliconFlow (CN), but got '{kwargs.get('api_key')}'"

            print("✅ SiliconFlow (CN) key resolution verified.")


if __name__ == "__main__":
    # Allow running directly with python
    import asyncio
    import sys

    try:
        asyncio.run(test_llm_config_key_resolution())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
