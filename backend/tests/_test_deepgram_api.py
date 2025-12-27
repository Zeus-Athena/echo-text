"""
Deepgram API Connection Test
测试 Deepgram 各模型的可用性
"""

import asyncio
import io
import struct
import wave


# 创建一个简单的静音 WAV 文件用于测试
def create_silent_wav(duration_seconds=0.5, sample_rate=16000):
    """创建一个静音 WAV 文件"""
    num_samples = int(duration_seconds * sample_rate)
    samples = struct.pack("<" + "h" * num_samples, *([0] * num_samples))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples)

    return buffer.getvalue()


async def test_deepgram_model(api_key: str, model: str):
    """测试单个 Deepgram 模型"""
    import httpx

    # Flux 需要 v2 endpoint
    if model.startswith("flux"):
        endpoint = "v2"
    else:
        endpoint = "v1"

    url = f"https://api.deepgram.com/{endpoint}/listen?model={model}&language=en"
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "audio/wav"}

    wav_data = create_silent_wav()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, content=wav_data)
            result = response.json()

            if response.status_code == 200:
                transcript = (
                    result.get("results", {})
                    .get("channels", [{}])[0]
                    .get("alternatives", [{}])[0]
                    .get("transcript", "")
                )
                return {
                    "model": model,
                    "status": "OK",
                    "transcript": transcript,
                    "endpoint": endpoint,
                }
            else:
                return {
                    "model": model,
                    "status": "ERROR",
                    "error": result.get("err_msg", str(result)),
                    "endpoint": endpoint,
                }
        except Exception as e:
            return {"model": model, "status": "EXCEPTION", "error": str(e), "endpoint": endpoint}


async def main():
    api_key = "593cb13eb3660b7d908fb995c466b997fa96f2ca"

    models_to_test = [
        "flux-general-en",  # v2 endpoint
        "nova-3",
        "nova-3-general",
        "nova-2",
        "nova-2-general",
        "nova",
        "enhanced",
    ]

    print("=" * 60)
    print("Deepgram Model Availability Test")
    print("=" * 60)

    for model in models_to_test:
        result = await test_deepgram_model(api_key, model)
        status_icon = "✅" if result["status"] == "OK" else "❌"
        print(f"{status_icon} {model:20} - {result['status']}")
        if result["status"] != "OK":
            print(f"   Error: {result.get('error', 'Unknown')[:50]}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
