"""
核心文本对话模块
支持流式输出、对话历史管理、多模型切换
"""
import asyncio
from openai import AsyncOpenAI
from typing import AsyncGenerator, Optional


class AIChatModule:
    def __init__(self, config: dict):
        self.config = config
        self._client: Optional[AsyncOpenAI] = None
        self._rebuild_client()

    def _rebuild_client(self):
        ai_cfg = self.config.get("ai", {})
        self._client = AsyncOpenAI(
            api_key=ai_cfg.get("text_api_key", "sk-placeholder"),
            base_url=ai_cfg.get("text_api_url", "https://api.openai.com/v1"),
        )

    def update_config(self, config: dict):
        self.config = config
        self._rebuild_client()

    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> AsyncGenerator[str, None]:
        """流式返回 AI 回复，逐 token yield"""
        ai_cfg = self.config.get("ai", {})
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        try:
            stream = await self._client.chat.completions.create(
                model=ai_cfg.get("text_model", "gpt-4o-mini"),
                messages=full_messages,
                max_tokens=ai_cfg.get("max_tokens", 2000),
                temperature=ai_cfg.get("temperature", 0.8),
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            yield f"\n[错误] {str(e)}"

    async def chat_once(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> str:
        """非流式，返回完整回复"""
        result = []
        async for token in self.chat_stream(messages, system_prompt):
            result.append(token)
        return "".join(result)
