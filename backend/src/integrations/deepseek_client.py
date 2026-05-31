"""DeepSeek V4 chat client (OpenAI-compatible HTTP API)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class DeepSeekError(RuntimeError):
    """Raised when the DeepSeek API returns an error or is misconfigured."""


class DeepSeekClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _require_key(self) -> str:
        key = settings.deepseek_api_key.get_secret_value().strip()
        if not key:
            raise DeepSeekError(
                "未配置 DeepSeek API Key。请在 backend/.env 中设置 DEEPSEEK_API_KEY"
            )
        return key

    def _client_instance(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=settings.llm_timeout_seconds)
        return self._client

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        json_object: bool = True,
    ) -> str:
        api_key = self._require_key()
        body: dict[str, Any] = {
            "model": settings.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "thinking": {
                "type": "enabled" if settings.deepseek_thinking else "disabled",
            },
        }
        if json_object:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        url = settings.deepseek_chat_completions_url()

        try:
            response = await self._client_instance().post(url, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise DeepSeekError(f"DeepSeek 请求超时（{settings.llm_timeout_seconds}s）") from exc
        except httpx.HTTPError as exc:
            raise DeepSeekError(f"DeepSeek 网络错误: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text[:500]
            raise DeepSeekError(f"DeepSeek API {response.status_code}: {detail}")

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected DeepSeek response: %s", data)
            raise DeepSeekError("DeepSeek 响应格式异常") from exc

        if not content or not str(content).strip():
            raise DeepSeekError("DeepSeek 返回空内容")
        return str(content).strip()


deepseek_client = DeepSeekClient()
