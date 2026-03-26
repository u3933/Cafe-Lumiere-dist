"""
LLM Client - OpenAI互換 / Gemini 両対応 (vA1)

config.yaml の llm.provider で切り替え:
  provider: "openai"   → llama.cpp / LM Studio / Ollama / OpenAI API（OpenAI互換）
  provider: "gemini"   → Gemini REST API
  provider: "llamacpp" → "openai" として後方互換処理

プロバイダー別エンドポイント例:
  llama.cpp  : http://localhost:8080/v1/chat/completions
  LM Studio  : http://localhost:1234/v1/chat/completions
  Ollama     : http://localhost:11434/v1/chat/completions
  OpenAI API : https://api.openai.com/v1/chat/completions
"""
import asyncio
import json
import logging
from typing import AsyncIterator, List, Dict

import aiohttp

logger = logging.getLogger(__name__)

_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMClient:
    """OpenAI互換 / Gemini 両対応 LLM クライアント"""

    def __init__(self, config: dict):
        llm_config = config.get("llm", {})
        self.endpoint    = llm_config.get("endpoint", "http://localhost:8080/v1/chat/completions")
        self.model       = llm_config.get("model", "default")
        self.max_tokens  = llm_config.get("max_tokens", 256)
        self.temperature = llm_config.get("temperature", 0.8)
        self.stream      = llm_config.get("stream", True)

        # llamacpp は openai に統合（後方互換）
        provider = llm_config.get("provider", "openai").strip().lower()
        self._provider = "openai" if provider == "llamacpp" else provider

        # APIキー（OpenAI API使用時は必須。llama.cpp/LM Studio/Ollamaは空でOK）
        self._api_key = llm_config.get("api_key", "").strip()

        # Gemini設定
        gemini_cfg = config.get("gemini", {})
        self._gemini_api_key = gemini_cfg.get("api_key", "").strip()
        self._gemini_model   = llm_config.get("gemini_model", gemini_cfg.get("model", "gemini-2.0-flash"))

        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(force_close=True)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=120, connect=15)
            )
        return self._session

    async def generate_stream(self, messages: List[Dict[str, str]], max_tokens: int = None) -> AsyncIterator[str]:
        if self._provider == "gemini":
            text = await self._generate_gemini(messages, max_tokens)
            if text:
                yield text
            return

        # OpenAI互換（llama.cpp / LM Studio / Ollama / OpenAI API）
        session = await self._get_session()

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model":       self.model,
            "messages":    messages,
            "max_tokens":  max_tokens or self.max_tokens,
            "temperature": self.temperature,
            "stream":      self.stream,
        }

        try:
            async with session.post(self.endpoint, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"❌ LLM API エラー: {resp.status} - {error_text}")
                    return

                async for line in resp.content:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️ JSON パースエラー: {data[:100]}")

        except aiohttp.ClientError as e:
            logger.error(f"❌ LLM 通信エラー: {e}")
        except asyncio.TimeoutError:
            logger.error("❌ LLM タイムアウト")

    async def generate(self, messages: List[Dict[str, str]], max_tokens: int = None) -> str:
        async with self._lock:
            full_text = ""
            async for token in self.generate_stream(messages, max_tokens=max_tokens):
                full_text += token
            return full_text

    async def _generate_gemini(self, messages: List[Dict[str, str]], max_tokens: int = None) -> str:
        if not self._gemini_api_key:
            logger.error("❌ Gemini API キーが未設定です（gemini.api_key）")
            return ""

        url = _GEMINI_ENDPOINT.format(model=self._gemini_model)
        params = {"key": self._gemini_api_key}

        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        chat_messages = [m for m in messages if m.get("role") != "system"]

        if not chat_messages:
            chat_messages = [{"role": "user", "content": "実行してください"}]

        body: dict = {
            "contents": [
                {
                    "role": "user" if m["role"] == "user" else "model",
                    "parts": [{"text": m["content"]}],
                }
                for m in chat_messages
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": max_tokens or self.max_tokens,
            },
        }

        if system_parts:
            body["system_instruction"] = {
                "parts": [{"text": "\n".join(system_parts)}]
            }

        timeout = aiohttp.ClientTimeout(total=60, connect=15)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, params=params, json=body) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.error(f"❌ Gemini LLM API エラー: {resp.status} - {text[:300]}")
                        return ""
                    data = await resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()

        except aiohttp.ClientError as e:
            logger.error(f"❌ Gemini LLM 通信エラー: {e}")
            return ""
        except (KeyError, IndexError) as e:
            logger.error(f"❌ Gemini LLM レスポンス解析エラー: {e}")
            return ""

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
