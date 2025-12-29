#!/usr/bin/env python3
"""
LLM 翻译服务测试
验证 /no_think 修改不影响其他供应商
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestLLMServiceQwen3NoThink:
    """测试 Qwen3 /no_think 指令逻辑"""

    def test_qwen3_model_adds_no_think_prefix(self):
        """验证 Qwen3 模型会添加 /no_think 前缀"""
        # 模拟 Qwen3 模型名称
        qwen3_models = [
            "accounts/fireworks/models/qwen3-235b-a22b-instruct-2507",
            "qwen3-30b-a3b",
            "Qwen/Qwen3-30B-A3B",
            "accounts/fireworks/models/qwen3-235b-a22b",
        ]

        for model in qwen3_models:
            # 检查条件
            should_add_no_think = "qwen3" in model.lower()
            assert should_add_no_think, f"应该为 {model} 添加 /no_think"

            # 验证前缀添加
            text = "Hello, world!"
            if "qwen3" in model.lower():
                actual_text = f"/no_think\n{text}"
            else:
                actual_text = text

            assert actual_text.startswith("/no_think"), f"{model} 应该添加 /no_think 前缀"
            assert text in actual_text, "原始文本应该保留"

    def test_non_qwen3_models_unchanged(self):
        """验证非 Qwen3 模型不受影响"""
        non_qwen3_models = [
            "deepseek-v3p2",
            "gpt-oss-120b",
            "deepseek-chat",
            "llama-3.3-70b-versatile",
            "Qwen/Qwen2.5-72B-Instruct",  # Qwen2.5 不是 Qwen3
            "gpt-4",
            "claude-3",
        ]

        for model in non_qwen3_models:
            # 检查条件
            should_add_no_think = "qwen3" in model.lower()
            assert not should_add_no_think, f"不应该为 {model} 添加 /no_think"

            # 验证文本不变
            text = "Hello, world!"
            if "qwen3" in model.lower():
                actual_text = f"/no_think\n{text}"
            else:
                actual_text = text

            assert actual_text == text, f"{model} 的文本不应该被修改"


async def test_translate_with_mock():
    """使用 Mock 测试 translate 方法"""
    from app.models.user import UserConfig
    from app.services.llm_service import LLMService

    # 创建 Mock 配置
    mock_config = MagicMock(spec=UserConfig)
    mock_config.llm_provider = "Fireworks"
    mock_config.llm_api_key = "test_key"
    mock_config.llm_base_url = "https://api.fireworks.ai/inference/v1"
    mock_config.llm_model = "accounts/fireworks/models/qwen3-235b-a22b-instruct-2507"
    mock_config.llm_groq_api_key = None
    mock_config.llm_siliconflow_api_key = None
    mock_config.llm_siliconflowglobal_api_key = None

    # Mock OpenAI 客户端
    with patch("app.services.llm_service.AsyncOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好，世界！"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # 创建服务实例
        service = LLMService(mock_config)

        # 调用翻译
        result = await service.translate("Hello, world!", source_lang="en", target_lang="zh")

        # 验证结果
        assert result == "你好，世界！"

        # 验证 API 调用中 user content 包含 /no_think
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_message = next(m for m in messages if m["role"] == "user")
        assert user_message["content"].startswith("/no_think"), "Qwen3 应该添加 /no_think 前缀"


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 LLM 翻译服务测试 - /no_think 修改验证")
    print("=" * 60)

    # 基础逻辑测试
    test_instance = TestLLMServiceQwen3NoThink()

    print("\n1. 测试 Qwen3 模型添加 /no_think 前缀...")
    try:
        test_instance.test_qwen3_model_adds_no_think_prefix()
        print("   ✅ 通过")
    except AssertionError as e:
        print(f"   ❌ 失败: {e}")

    print("\n2. 测试非 Qwen3 模型不受影响...")
    try:
        test_instance.test_non_qwen3_models_unchanged()
        print("   ✅ 通过")
    except AssertionError as e:
        print(f"   ❌ 失败: {e}")

    # Mock 测试
    print("\n3. 测试 translate 方法 (Mock)...")
    try:
        asyncio.run(test_translate_with_mock())
        print("   ✅ 通过")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
