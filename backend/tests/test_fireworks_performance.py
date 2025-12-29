#!/usr/bin/env python3
"""
Fireworks LLM 模型性能测试 (多速率测试)
测试不同请求间隔下的限流情况
"""

import asyncio
import statistics
import time

from openai import AsyncOpenAI

# Fireworks API 配置
API_KEY = "fw_EzsCUGbkVBkiR44fozToM5"
BASE_URL = "https://api.fireworks.ai/inference/v1"

# 只测试 qwen3-235b-a22b-instruct-2507
MODELS = [
    "accounts/fireworks/models/qwen3-235b-a22b-instruct-2507",
]

# 测试文本
TEST_TEXTS = [
    "Hello everyone",
    "Today we're going to discuss",
    "the importance of machine learning",
    "in modern software development",
    "Let's start with the basics",
    "首先我们来看一下",
    "这个项目的整体架构",
    "然后再讨论具体的实现细节",
    "大家有什么问题可以随时提出",
    "我们的目标是提高效率",
]

# 翻译提示词
SYSTEM_PROMPT = "Translate to Chinese. Output translation only, no explanation."


async def test_single_request(client: AsyncOpenAI, model: str, text: str) -> dict:
    """单次请求测试"""
    start = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=100,
            temperature=0.3,
        )
        latency = (time.perf_counter() - start) * 1000  # ms
        output = response.choices[0].message.content
        return {
            "success": True,
            "latency_ms": latency,
            "output": output,
        }
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return {"success": False, "latency_ms": latency, "error": str(e)}


async def test_model(client: AsyncOpenAI, model: str, delay: float, num_requests: int = 50) -> dict:
    """测试单个模型在特定延迟下的表现"""
    print(f"\n{'=' * 60}")
    print(f"测试模型: {model.split('/')[-1]}")
    print(f"请求间隔: {delay}s | 请求次数: {num_requests}")
    print(f"{'=' * 60}")

    results = []
    successes = 0
    failures = 0

    # 连续错误计数器，用于提前终止严重限流的测试
    consecutive_failures = 0

    for i in range(num_requests):
        text = TEST_TEXTS[i % len(TEST_TEXTS)]
        result = await test_single_request(client, model, text)
        results.append(result)

        if result["success"]:
            successes += 1
            consecutive_failures = 0
            if i < 3:
                print(f"  [{i + 1}] ✅ {result['latency_ms']:.0f}ms")
        else:
            failures += 1
            consecutive_failures += 1
            error_msg = result["error"]
            if "429" in error_msg:
                print(f"  [{i + 1}] ❌ 限流 (429)")
            else:
                print(f"  [{i + 1}] ❌ {error_msg[:50]}")

            # 如果连续失败超过10次，提前终止该组测试
            if consecutive_failures >= 10:
                print(f"\n⚠️ 连续失败 10 次，提前终止本组测试 (Interval: {delay}s)")
                break

        # 进度
        if (i + 1) % 10 == 0:
            print(f"  进度: {i + 1}/{num_requests}")

        # 请求间隔
        await asyncio.sleep(delay)

    # 统计
    successful_results = [r for r in results if r["success"]]
    latencies = [r["latency_ms"] for r in successful_results]

    # fix: prevent division by zero if len(results) is 0 (though num_requests > 0, loop might break early)
    total_run = len(results)
    success_rate = (successes / total_run * 100) if total_run > 0 else 0

    stats = {
        "model": model.split("/")[-1],
        "delay": delay,
        "total_requests": total_run,
        "successes": successes,
        "failures": failures,
        "success_rate": success_rate,
        "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
        "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
    }

    print(f"\n📊 间隔 {delay}s 统计:")
    print(f"   成功率: {stats['success_rate']:.1f}% ({successes}/{total_run})")
    print(f"   平均延迟: {stats['avg_latency_ms']:.0f}ms")

    return stats


async def main():
    print("=" * 60)
    print("🚀 Fireworks LLM 速率限制压力测试")
    print("=" * 60)
    print(f"API Base: {BASE_URL}")

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

    # 测试不同的延迟间隔
    delays = [0.5, 1.0, 2.0]
    all_stats = []

    model = MODELS[0]  # 这里只测第一个模型 qwen3

    for delay in delays:
        try:
            stats = await test_model(client, model, delay=delay, num_requests=50)
            all_stats.append(stats)
            # 组间休息，防止上一组的限流影响下一组
            print("\nWaiting 5 seconds before next test...")
            await asyncio.sleep(5.0)
        except Exception as e:
            print(f"❌ 测试出错: {e}")

    # 汇总报告
    print("\n" + "=" * 60)
    print("📋 速率测试报告汇总")
    print("=" * 60)
    print(f"{'间隔(s)':<10} {'成功率':>10} {'平均延迟':>12} {'建议':>10}")
    print("-" * 60)

    for stats in all_stats:
        rec = "✅ 可用" if stats["success_rate"] > 95 else "❌ 限流"
        print(
            f"{stats['delay']:<10.1f} "
            f"{stats['success_rate']:>9.1f}% "
            f"{stats['avg_latency_ms']:>10.0f}ms "
            f"{rec:>10}"
        )

    print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
