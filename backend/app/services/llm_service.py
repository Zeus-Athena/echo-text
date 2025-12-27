"""
LLM Service
统一的 LLM 调用接口
"""

from collections.abc import AsyncGenerator

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.user import UserConfig


class LLMService:
    """LLM Service for translation and AI summary"""

    def __init__(self, config: UserConfig | None = None):
        """Initialize with user config or defaults"""
        # Determine active key based on provider
        self.provider = "unknown"
        if config:
            self.model = config.llm_model or settings.DEFAULT_LLM_MODEL
            self.base_url = config.llm_base_url or settings.DEFAULT_LLM_BASE_URL

            self.provider = (config.llm_provider or "").lower()
            if self.provider == "groq":
                self.api_key = config.llm_groq_api_key
            elif self.provider == "siliconflow":
                self.api_key = config.llm_siliconflow_api_key
            else:
                self.api_key = config.llm_api_key
        else:
            self.api_key = None
            self.base_url = settings.DEFAULT_LLM_BASE_URL
            self.model = settings.DEFAULT_LLM_MODEL

        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None

    async def check_balance(self) -> dict:
        """Check account balance for current provider"""
        if not self.api_key:
            return {"error": "API Key not configured"}

        import httpx

        try:
            if self.provider == "siliconflow":
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        "https://api.siliconflow.cn/v1/user/info",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        timeout=10.0,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        user_data = data.get("data", {})
                        balance = user_data.get("balance")
                        return {
                            "balance": float(balance) if balance else 0,
                            "currency": "CNY",
                            "provider": "SiliconFlow",
                        }
                    else:
                        return {"error": f"API Error: {resp.status_code}"}

            return {"message": f"Balance check not supported for: {self.provider}"}

        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return {"error": str(e)}

    async def translate(
        self,
        text: str,
        source_lang: str = "zh",
        target_lang: str = "en",
        style: str = "standard",
        context: str = "",
        custom_prompt: str | None = None,
    ) -> str:
        """Translate text with optional context for better continuity"""
        if not self.client:
            raise ValueError("LLM not configured. Please set API key in settings.")

        style_prompts = {
            "standard": "使用标准、自然的语言风格",
            "formal": "使用正式、专业的语言风格",
            "casual": "使用轻松、口语化的语言风格",
        }
        style_hint = style_prompts.get(style, style_prompts["standard"])

        lang_names = {"zh": "中文", "en": "English", "ja": "日本語", "ko": "한국어"}
        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)

        # Build context section if provided
        context_section = ""
        if context:
            context_section = f"""
<context>
The following is previous text for context only. DO NOT TRANSLATE THIS:
"{context}"
</context>"""

        if custom_prompt:
            # Custom prompt overrides default
            system_prompt = (
                custom_prompt.replace("{{source_lang}}", source_name)
                .replace("{{target_lang}}", target_name)
                .replace("{{style}}", style_hint)
            )
            if "{{text}}" in system_prompt:
                system_prompt = system_prompt.replace("{{text}}", text)
        else:
            system_prompt = f"""You are a professional translator.
Translate the user input from {source_name} to {target_name}.
{style_hint}

{context_section}

<rules>
1. Translate EVERY SINGLE sentence word-by-word.
2. Do NOT skip, merge, or summarize ANY content.
3. The output must have the SAME number of sentences as the input.
4. If the text appears incomplete (ends mid-sentence), translate what is given literally.
5. Do NOT add explanations. Only output the translated text.
6. Do NOT translate the content inside <context> tags.
</rules>"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM translation error: {e}")
            raise

    async def translate_stream(
        self,
        text: str,
        source_lang: str = "zh",
        target_lang: str = "en",
        custom_prompt: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Translate text with streaming response"""
        if not self.client:
            raise ValueError("LLM not configured")

        lang_names = {"zh": "中文", "en": "English"}
        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)

        if custom_prompt:
            system_prompt = custom_prompt.replace("{{source_lang}}", source_name).replace(
                "{{target_lang}}", target_name
            )
            if "{{text}}" in system_prompt:
                system_prompt = system_prompt.replace("{{text}}", text)
        else:
            system_prompt = f"""You are a professional translator.
Translate the user input from {source_name} to {target_name}.

<rules>
1. Translate EVERY SINGLE sentence word-by-word.
2. Do NOT skip, merge, or summarize ANY content.
3. The output must have the SAME number of sentences as the input.
4. If the text appears incomplete (ends mid-sentence), translate what is given literally.
5. Do NOT add explanations. Only output the translated text.
</rules>"""

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.3,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            raise

    async def generate_summary(
        self,
        transcript: str,
        target_lang: str = "zh",
        segments: list = None,
        duration_seconds: int = 0,
        custom_prompt: str | None = None,
    ) -> dict:
        """Generate AI summary from transcript in target language, including chapters"""
        if not self.client:
            raise ValueError("LLM not configured")

        # Calculate total duration for chapter estimation
        total_duration = duration_seconds
        if not total_duration and segments:
            # Estimate from segments
            for seg in segments:
                end_time = 0
                if isinstance(seg, dict):
                    end_time = seg.get("end", 0)
                elif hasattr(seg, "end"):
                    end_time = getattr(seg, "end", 0)

                total_duration = max(total_duration, int(end_time))

        # Language-specific prompts with chapter support
        lang_prompts = {
            "zh": f"""你是一个专业的会议/录音分析助手。
请分析以下转录文本，并用中文生成：
1. summary: 简洁的内容总结（100-200字）
2. key_points: 关键要点列表（3-5个要点）
3. action_items: 待办事项/行动项（如果有）
4. auto_tags: 自动标签（2-4个标签，用于分类）
5. chapters: 章节划分（3-6个章节），每个章节包含：
   - timestamp: 估计的开始时间（秒数，总时长约{total_duration}秒）
   - title: 章节标题

请以 JSON 格式输出，例如：
{{
  "summary": "...",
  "key_points": ["要点1", "要点2"],
  "action_items": ["待办1", "待办2"],
  "auto_tags": ["工作", "会议"],
  "chapters": [
    {{"timestamp": 0, "title": "开场介绍"}},
    {{"timestamp": 60, "title": "主题讨论"}}
  ]
}}""",
            "en": f"""You are a professional meeting/recording analysis assistant.
Analyze the following transcript and generate in English:
1. summary: A concise summary (100-200 words)
2. key_points: Key points list (3-5 points)
3. action_items: Action items/todos (if any)
4. auto_tags: Auto tags (2-4 tags for categorization)
5. chapters: Chapter divisions (3-6 chapters), each with:
   - timestamp: Estimated start time in seconds (total duration ~{total_duration}s)
   - title: Chapter title

Output in JSON format, for example:
{{
  "summary": "...",
  "key_points": ["Point 1", "Point 2"],
  "action_items": ["Todo 1", "Todo 2"],
  "auto_tags": ["work", "meeting"],
  "chapters": [
    {{"timestamp": 0, "title": "Introduction"}},
    {{"timestamp": 60, "title": "Main Discussion"}}
  ]
}}""",
            "ja": f"""あなたはプロフェッショナルな会議/録音分析アシスタントです。
以下の文字起こしを分析し、日本語で生成してください：
1. summary: 簡潔な内容要約（100-200字）
2. key_points: 重要ポイントリスト（3-5個）
3. action_items: アクションアイテム/TODO（あれば）
4. auto_tags: 自動タグ（2-4個、分類用）
5. chapters: チャプター分割（3-6個）、各チャプターには：
   - timestamp: 推定開始時間（秒、総時間約{total_duration}秒）
   - title: チャプタータイトル

JSON形式で出力してください：
{{
  "summary": "...",
  "key_points": ["ポイント1", "ポイント2"],
  "action_items": ["TODO1", "TODO2"],
  "auto_tags": ["仕事", "会議"],
  "chapters": [
    {{"timestamp": 0, "title": "導入"}},
    {{"timestamp": 60, "title": "本題"}}
  ]
}}""",
        }

        # Use target language prompt, fallback to English
        system_prompt = lang_prompts.get(target_lang, lang_prompts["en"])

        if custom_prompt:
            system_prompt = custom_prompt.replace("{{target_lang}}", target_lang).replace(
                "{{duration}}", str(total_duration)
            )
            if "{{text}}" in system_prompt:
                # If transcript is very large, replacing {{text}} in system prompt might be okay
                # but typically we user message for that.
                pass

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript},
                ],
                temperature=0.5,
                response_format={"type": "json_object"},
            )

            import json

            result = json.loads(response.choices[0].message.content)
            result_data = {
                "summary": result.get("summary", ""),
                "key_points": result.get("key_points", []),
                "action_items": result.get("action_items", []),
                "auto_tags": result.get("auto_tags", []),
                "chapters": result.get("chapters") or [],
            }

            # Post-process chapters: timestamp validation and clamping
            chapters = result_data["chapters"]
            if chapters and isinstance(chapters, list) and total_duration > 0:
                for chapter in chapters:
                    ts = chapter.get("timestamp", 0)
                    try:
                        ts = float(ts)
                        # Logic Fix: Clamp timestamp to [0, total_duration]
                        # If LLM hallucinates 55s for 49s audio, we correct it to 49s instead of hiding it
                        ts = max(0, min(ts, total_duration))
                        chapter["timestamp"] = int(ts)
                    except (ValueError, TypeError):
                        chapter["timestamp"] = 0

                # Sort exactly by time
                chapters.sort(key=lambda x: x.get("timestamp", 0))
                result_data["chapters"] = chapters

            return result_data
        except Exception as e:
            logger.error(f"LLM summary error: {e}")
            raise

    async def lookup_word(
        self, word: str, language: str = "en", custom_prompt: str | None = None
    ) -> dict:
        """Lookup word definition using LLM"""
        if not self.client:
            raise ValueError("LLM not configured")

        if custom_prompt:
            system_prompt = custom_prompt.replace("{{language}}", language).replace(
                "{{word}}", word
            )
        else:
            system_prompt = f"""你是一个专业的词典助手。请为以下 {language} 单词提供详细的中文解析。
请务必以 JSON 格式输出，包含以下字段：
{{
  "word": "单词名称",
  "phonetic": "音标",
  "definitions": [
    {{
      "part_of_speech": "词性（请使用中文，例如：名词、动词、形容词）", 
      "definition": "该词性的详细中文释义", 
      "example": "英语例句，并在括号内附带中文翻译"
    }}
  ],
  "phrases": ["常用的中英对照词组，例如：take off (起飞；脱下)"],
  "synonyms": ["英文同义词"],
  "antonyms": ["英文反义词"]
}}
请确保 definitions 列表中的所有内容、词性和释义均使用中文。"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": word},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            import json

            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"LLM dictionary error: {e}")
            raise


async def get_llm_service(config: UserConfig | None = None) -> LLMService:
    """Get LLM service instance"""
    return LLMService(config)
