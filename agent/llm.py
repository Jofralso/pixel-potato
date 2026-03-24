"""
LLM client supporting multiple backends: Ollama, OpenAI-compatible, Anthropic.
"""

import json
import httpx
import logging

from config.settings import Settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=300.0)

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str = "",
    ) -> dict:
        provider = self.settings.llm_provider

        if provider == "ollama":
            return await self._ollama_chat(messages, tools, system)
        elif provider == "openai":
            return await self._openai_chat(messages, tools, system)
        elif provider == "anthropic":
            return await self._anthropic_chat(messages, tools, system)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    async def _ollama_chat(
        self, messages: list[dict], tools: list[dict] | None, system: str
    ) -> dict:
        url = f"{self.settings.llm_base_url}/api/chat"

        ollama_messages = []
        if system:
            ollama_messages.append({"role": "system", "content": system})

        for msg in messages:
            ollama_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": self.settings.llm_model,
            "messages": ollama_messages,
            "stream": False,
        }

        if tools:
            payload["tools"] = self._convert_tools_to_ollama(tools)

        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        result = {"content": "", "tool_calls": []}
        msg = data.get("message", {})
        result["content"] = msg.get("content", "")

        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            result["tool_calls"].append({
                "id": fn.get("name", ""),
                "name": fn.get("name", ""),
                "arguments": fn.get("arguments", {}),
            })

        return result

    async def _openai_chat(
        self, messages: list[dict], tools: list[dict] | None, system: str
    ) -> dict:
        url = f"{self.settings.llm_base_url}/v1/chat/completions"

        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        for msg in messages:
            oai_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": self.settings.llm_model,
            "messages": oai_messages,
        }

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("inputSchema", t.get("parameters", {})),
                    },
                }
                for t in tools
            ]

        headers = {}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"

        resp = await self.client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        msg = choice["message"]

        result = {"content": msg.get("content", "") or "", "tool_calls": []}

        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            args = fn.get("arguments", "{}")
            if isinstance(args, str):
                args = json.loads(args)
            result["tool_calls"].append({
                "id": tc.get("id", ""),
                "name": fn.get("name", ""),
                "arguments": args,
            })

        return result

    async def _anthropic_chat(
        self, messages: list[dict], tools: list[dict] | None, system: str
    ) -> dict:
        url = f"{self.settings.llm_base_url}/v1/messages"

        anthropic_messages = []
        for msg in messages:
            if msg["role"] in ("user", "assistant"):
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        payload = {
            "model": self.settings.llm_model,
            "max_tokens": 8192,
            "messages": anthropic_messages,
        }
        if system:
            payload["system"] = system

        if tools:
            payload["tools"] = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("inputSchema", t.get("parameters", {})),
                }
                for t in tools
            ]

        headers = {
            "x-api-key": self.settings.llm_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        resp = await self.client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        result = {"content": "", "tool_calls": []}

        for block in data.get("content", []):
            if block["type"] == "text":
                result["content"] += block["text"]
            elif block["type"] == "tool_use":
                result["tool_calls"].append({
                    "id": block["id"],
                    "name": block["name"],
                    "arguments": block.get("input", {}),
                })

        return result

    def _convert_tools_to_ollama(self, tools: list[dict]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("inputSchema", t.get("parameters", {})),
                },
            }
            for t in tools
        ]
