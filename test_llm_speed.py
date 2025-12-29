#!/usr/bin/env python3
"""
SiliconFlowGlobal + Qwen3-30B-A3B 翻译响应速度测试
"""

import asyncio
import time
from openai import AsyncOpenAI

API_KEY = "sk-rvdslbuehbtiebsmgzfghqrtwzqcurgexrhoqwblymzqbkcw"
BASE_URL = "https://api.siliconflow.com/v1"
MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"

# 测试用例：50 个不同长度和类型的英文文本
TEST_CASES = [
    # 短句 (5-10 词) - 15 个
    ("short_01", "I don't feel like talking today."),
    ("short_02", "Hello, how are you doing?"),
    ("short_03", "The weather is nice outside."),
    ("short_04", "Can you help me with this?"),
    ("short_05", "I need to go now."),
    ("short_06", "What time is it?"),
    ("short_07", "That sounds like a good idea."),
    ("short_08", "Let me think about it."),
    ("short_09", "I'll call you later."),
    ("short_10", "Thanks for your help today."),
    ("short_11", "Where is the nearest station?"),
    ("short_12", "I completely agree with you."),
    ("short_13", "This coffee tastes amazing."),
    ("short_14", "Please wait a moment."),
    ("short_15", "I'm not sure about that."),
    
    # 中等句子 (15-25 词) - 20 个
    ("medium_01", "I'm going to buy an Aura ring because I want to track my sleep and activity levels better."),
    ("medium_02", "This one is a bit more snug but it's not tight where it's uncomfortable at all."),
    ("medium_03", "If you've got an aura ring, please let me know if you sized up or stayed true to size."),
    ("medium_04", "The meeting has been rescheduled to next Monday at three o'clock in the afternoon."),
    ("medium_05", "I've been working on this project for three months and it's finally coming together nicely."),
    ("medium_06", "Could you please send me the report by the end of the day? It's quite urgent."),
    ("medium_07", "The restaurant we went to last night had the most incredible seafood I've ever tasted."),
    ("medium_08", "I think we should consider all the options before making a final decision on this matter."),
    ("medium_09", "My flight gets in at six thirty, so I should be at the hotel by eight o'clock."),
    ("medium_10", "The new software update includes several bug fixes and performance improvements across the board."),
    ("medium_11", "She mentioned that the conference would be held in the main auditorium on the third floor."),
    ("medium_12", "I've been trying to learn a new language, but finding time to practice is really challenging."),
    ("medium_13", "The customer service team will be available to assist you from nine AM to five PM."),
    ("medium_14", "We need to finalize the budget proposal before the quarterly review meeting next week."),
    ("medium_15", "The documentary about climate change really opened my eyes to the severity of the situation."),
    ("medium_16", "I recommend checking the weather forecast before planning any outdoor activities this weekend."),
    ("medium_17", "The package should arrive within three to five business days depending on your location."),
    ("medium_18", "It would be great if we could schedule a follow-up call to discuss the next steps."),
    ("medium_19", "The training session will cover all the essential features of the new content management system."),
    ("medium_20", "I appreciate you taking the time to explain everything so clearly during our conversation."),
    
    # 长句 (40-60 词) - 10 个
    ("long_01", "I'm just thinking about the summer where it's gonna get hot and my body becomes more swollen with water retention and all that sort of stuff so I'm thinking about it might be a smart idea to go for the larger size but I really don't know what to choose."),
    ("long_02", "The sizing kit came this morning and I am between two sizes which I knew this would happen so this one is the size seven fits fine it's a bit snug but it's not tight whereas this one's a size eight and this one has a bit more room in as you can see."),
    ("long_03", "The company has announced a comprehensive restructuring plan that will affect multiple departments across all regional offices, and employees are encouraged to attend the town hall meeting scheduled for next Wednesday to learn more about how these changes might impact their roles and responsibilities."),
    ("long_04", "After careful consideration of all the proposals submitted by the various vendors, the selection committee has decided to move forward with the option that offers the best combination of cost effectiveness, technical capabilities, and long-term sustainability for our organization's needs."),
    ("long_05", "The research team has published their findings in a peer-reviewed journal, demonstrating that the new treatment approach shows promising results in early clinical trials, though they emphasize that more extensive studies are needed before any definitive conclusions can be drawn about its effectiveness."),
    ("long_06", "During yesterday's presentation, the marketing director outlined an ambitious strategy for expanding into emerging markets over the next fiscal year, which includes establishing partnerships with local distributors and launching targeted advertising campaigns tailored to each region's unique cultural preferences."),
    ("long_07", "The city council has approved a multimillion dollar infrastructure project that will modernize the public transportation system, including the installation of electric charging stations and the expansion of bike lanes throughout the downtown area to promote sustainable commuting options."),
    ("long_08", "Our analysis of customer feedback data reveals that users are generally satisfied with the product's core functionality but have expressed interest in additional features such as improved mobile integration and more customizable notification settings that would enhance their overall experience."),
    ("long_09", "The educational initiative aims to provide underprivileged students with access to high-quality learning resources and mentorship opportunities, partnering with local businesses and community organizations to create a supportive network that fosters academic achievement and career development."),
    ("long_10", "I want to express my sincere gratitude for all the support and guidance you have provided throughout this challenging period, your expertise and patience have been invaluable in helping our team navigate these complex issues and achieve our objectives despite the numerous obstacles we encountered."),
    
    # 技术/专业文本 - 5 个
    ("tech_01", "The API endpoint returns a JSON response with the user's configuration including LLM provider settings and authentication tokens."),
    ("tech_02", "We need to implement a WebSocket connection handler that processes real-time audio streams and sends transcription results back to the client."),
    ("tech_03", "The database migration script adds a new column to the user configuration table to store provider-specific API keys securely."),
    ("tech_04", "The frontend component uses React Query to manage server state and automatically handles caching, background updates, and error retries."),
    ("tech_05", "The Docker container orchestration is configured using Compose with health checks and automatic restart policies for improved reliability."),
]

SYSTEM_PROMPT = """You are a professional translator.
Translate the user input from English to Chinese.

<rules>
1. Translate EVERY SINGLE sentence word-by-word.
2. Do NOT skip, merge, or summarize ANY content.
3. Only output the translated text.
</rules>"""


async def test_single(client: AsyncOpenAI, name: str, text: str) -> dict:
    """测试单个翻译请求"""
    word_count = len(text.split())
    char_count = len(text)
    
    start_time = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.3,
        )
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        translation = response.choices[0].message.content.strip()
        
        return {
            "name": name,
            "word_count": word_count,
            "char_count": char_count,
            "latency_ms": latency_ms,
            "translation": translation,
            "success": True,
            "error": None,
        }
    except Exception as e:
        end_time = time.perf_counter()
        return {
            "name": name,
            "word_count": word_count,
            "char_count": char_count,
            "latency_ms": (end_time - start_time) * 1000,
            "translation": None,
            "success": False,
            "error": str(e),
        }


async def run_tests():
    """运行所有测试"""
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    print("=" * 60)
    print("SiliconFlowGlobal + Qwen3-30B-A3B 翻译响应速度测试")
    print("=" * 60)
    print(f"模型: {MODEL}")
    print(f"API: {BASE_URL}")
    print(f"测试用例数: {len(TEST_CASES)}")
    print("=" * 60)
    print()
    
    results = []
    
    # 预热请求
    print("🔥 预热请求...")
    await test_single(client, "warmup", "Hello world")
    print("✓ 预热完成\n")
    
    # 顺序测试（模拟实际使用场景）
    print("📊 开始测试（顺序请求，模拟实际场景）...\n")
    
    for name, text in TEST_CASES:
        result = await test_single(client, name, text)
        results.append(result)
        
        status = "✓" if result["success"] else "✗"
        print(f"{status} {name}: {result['latency_ms']:.0f}ms ({result['word_count']} 词)")
        if result["success"]:
            print(f"   原文: {text[:50]}...")
            print(f"   译文: {result['translation'][:50]}...")
        else:
            print(f"   错误: {result['error']}")
        print()
    
    # 统计分析
    successful = [r for r in results if r["success"]]
    
    if successful:
        latencies = [r["latency_ms"] for r in successful]
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        # 按类型分组
        short = [r for r in successful if r["name"].startswith("short")]
        medium = [r for r in successful if r["name"].startswith("medium")]
        long = [r for r in successful if r["name"].startswith("long")]
        tech = [r for r in successful if r["name"].startswith("tech")]
        
        print("=" * 60)
        print("📈 测试报告")
        print("=" * 60)
        print()
        print(f"总测试数: {len(TEST_CASES)}")
        print(f"成功数: {len(successful)}")
        print(f"失败数: {len(results) - len(successful)}")
        print()
        print("⏱️ 延迟统计（毫秒）:")
        print(f"   平均: {avg_latency:.0f}ms")
        print(f"   最小: {min_latency:.0f}ms")
        print(f"   最大: {max_latency:.0f}ms")
        print()
        
        print("📊 按文本类型分析:")
        if short:
            avg_short = sum(r["latency_ms"] for r in short) / len(short)
            print(f"   短句 (5-10 词): 平均 {avg_short:.0f}ms")
        if medium:
            avg_medium = sum(r["latency_ms"] for r in medium) / len(medium)
            print(f"   中句 (15-25 词): 平均 {avg_medium:.0f}ms")
        if long:
            avg_long = sum(r["latency_ms"] for r in long) / len(long)
            print(f"   长句 (40-60 词): 平均 {avg_long:.0f}ms")
        if tech:
            avg_tech = sum(r["latency_ms"] for r in tech) / len(tech)
            print(f"   技术文本: 平均 {avg_tech:.0f}ms")
        
        print()
        print("🎯 结论:")
        if avg_latency < 500:
            print("   ⭐⭐⭐⭐⭐ 极速 - 非常适合实时翻译场景")
        elif avg_latency < 1000:
            print("   ⭐⭐⭐⭐ 快速 - 适合流式翻译场景")
        elif avg_latency < 2000:
            print("   ⭐⭐⭐ 正常 - 可接受的延迟")
        else:
            print("   ⭐⭐ 较慢 - 可能影响实时体验")
        
        print()
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
