"""
LLM client with streaming support for Ollama, OpenAI-compatible, and Anthropic.
Handles proper tool_call message threading matching each provider's native format.
"""

import json
import uuid
import httpx
import logging
from typing import AsyncGenerator

from config.settings import Settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=300.0)

    # ── Unified entry point ───────────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str = "",
    ) -> dict:
        """Non-streaming call. Returns {"content": str, "tool_calls": list}."""
        provider = self.settings.llm_provider
        if provider == "ollama":
            return await self._ollama_chat(messages, tools, system)
        elif provider == "openai":
            return await self._openai_chat(messages, tools, system)
        elif provider == "anthropic":
            return await self._anthropic_chat(messages, tools, system)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str = "",
    ) -> AsyncGenerator[dict, None]:
        """Streaming call. Yields {"type": "text_delta"|"tool_call"|"done", ...}."""
        provider = self.settings.llm_provider
        if provider == "ollama":
            async for chunk in self._ollama_stream(messages, tools, system):
                yield chunk
        elif provider == "openai":
            async for chunk in self._openai_stream(messages, tools, system):
                yield chunk
        elif provider == "anthropic":
            async for chunk in self._anthropic_stream(messages, tools, system):
                yield chunk

    # ── Ollama ────────────────────────────────────────────────

    def _ollama_payload(self, messages, tools, system):
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        for msg in messages:
            m = {"role": msg["role"]}
            if msg.get("content"):
                m["content"] = msg["content"]
            if msg.get("tool_calls"):
                m["tool_calls"] = [
                    {"function": {"name": tc.get("function", tc).get("name", tc.get("name", "")),
                                  "arguments": tc.get("function", tc).get("arguments", {})}}
                    for tc in msg["tool_calls"]
                ]
            if msg["role"] == "tool":
                m["content"] = msg.get("content", "")
            msgs.append(m)

        payload = {"model": self.settings.llm_model, "messages": msgs}
        if tools:
            payload["tools"] = self._to_ollama_tools(tools)
        return payload

    async def _ollama_chat(self, messages, tools, system) -> dict:
        url = f"{self.settings.llm_base_url}/api/chat"
        payload = self._ollama_payload(messages, tools, system)
        payload["stream"] = False
        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return self._parse_ollama_response(data)

    async def _ollama_stream(self, messages, tools, system) -> AsyncGenerator[dict, None]:
        url = f"{self.settings.llm_base_url}/api/chat"
        payload = self._ollama_payload(messages, tools, system)
        payload["stream"] = True

        async with self.client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            full_content = ""
            tool_calls = []
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                data = json.loads(line)
                msg = data.get("message", {})

                # Text delta
                if msg.get("content"):
                    full_content += msg["content"]
                    yield {"type": "text_delta", "text": msg["content"]}

                # Tool calls come in the final message
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        call = {
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": {"name": fn.get("name", ""), "arguments": fn.get("arguments", {})},
                        }
                        tool_calls.append(call)
                        yield {"type": "tool_call", **call}

                if data.get("done"):
                    break

            yield {"type": "done", "content": full_content, "tool_calls": tool_calls}

    def _parse_ollama_response(self, data) -> dict:
        msg = data.get("message", {})
        result = {"content": msg.get("content", ""), "tool_calls": []}
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            result["tool_calls"].append({
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {"name": fn.get("name", ""), "arguments": fn.get("arguments", {})},
            })
        return result

    def _to_ollama_tools(self, tools):
        return [{"type": "function", "function": {
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": t.get("inputSchema", t.get("parameters", {})),
        }} for t in tools]

    # ── OpenAI / Compatible ───────────────────────────────────

    def _openai_payload(self, messages, tools, system):
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        for msg in messages:
            msgs.append(msg)

        payload = {"model": self.settings.llm_model, "messages": msgs}
        if tools:
            payload["tools"] = [{"type": "function", "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", t.get("parameters", {})),
            }} for t in tools]
        return payload

    def _openai_headers(self):
        h = {"content-type": "application/json"}
        if self.settings.llm_api_key:
            h["Authorization"] = f"Bearer {self.settings.llm_api_key}"
        return h

    async def _openai_chat(self, messages, tools, system) -> dict:
        url = f"{self.settings.llm_base_url}/v1/chat/completions"
        payload = self._openai_payload(messages, tools, system)
        resp = await self.client.post(url, json=payload, headers=self._openai_headers())
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]["message"]

        result = {"content": choice.get("content", "") or "", "tool_calls": []}
        for tc in choice.get("tool_calls", []):
            fn = tc.get("function", {})
            args = fn.get("arguments", "{}")
            if isinstance(args, str):
                args = json.loads(args)
            result["tool_calls"].append({
                "id": tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                "type": "function",
                "function": {"name": fn["name"], "arguments": args},
            })
        return result

    async def _openai_stream(self, messages, tools, system) -> AsyncGenerator[dict, None]:
        url = f"{self.settings.llm_base_url}/v1/chat/completions"
        payload = self._openai_payload(messages, tools, system)
        payload["stream"] = True

        async with self.client.stream("POST", url, json=payload, headers=self._openai_headers()) as resp:
            resp.raise_for_status()
            full_content = ""
            tc_buffers: dict[int, dict] = {}  # index -> {id, name, args_str}

            async for line in resp.aiter_lines():
                if not line.startswith("data: ") or line.strip() == "data: [DONE]":
                    if line.strip() == "data: [DONE]":
                        break
                    continue
                data = json.loads(line[6:])
                delta = data["choices"][0].get("delta", {})

                # Text
                if delta.get("content"):
                    full_content += delta["content"]
                    yield {"type": "text_delta", "text": delta["content"]}

                # Tool calls (streamed incrementally)
                for tc in delta.get("tool_calls", []):
                    idx = tc["index"]
                    if idx not in tc_buffers:
                        tc_buffers[idx] = {"id": tc.get("id", ""), "name": "", "args": ""}
                    buf = tc_buffers[idx]
                    if tc.get("id"):
                        buf["id"] = tc["id"]
                    fn = tc.get("function", {})
                    if fn.get("name"):
                        buf["name"] = fn["name"]
                    if fn.get("arguments"):
                        buf["args"] += fn["arguments"]

            # Emit completed tool calls
            tool_calls = []
            for idx in sorted(tc_buffers.keys()):
                buf = tc_buffers[idx]
                args = json.loads(buf["args"]) if buf["args"] else {}
                call = {
                    "id": buf["id"] or f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {"name": buf["name"], "arguments": args},
                }
                tool_calls.append(call)
                yield {"type": "tool_call", **call}

            yield {"type": "done", "content": full_content, "tool_calls": tool_calls}

    # ── Anthropic ─────────────────────────────────────────────

    def _anthropic_headers(self):
        return {
            "x-api-key": self.settings.llm_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def _anthropic_chat(self, messages, tools, system) -> dict:
        url = f"{self.settings.llm_base_url}/v1/messages"
        payload = {"model": self.settings.llm_model, "max_tokens": 16384, "messages": messages}
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [{"name": t["name"], "description": t.get("description", ""),
                                  "input_schema": t.get("inputSchema", t.get("parameters", {}))} for t in tools]

        resp = await self.client.post(url, json=payload, headers=self._anthropic_headers())
        resp.raise_for_status()
        data = resp.json()

        result = {"content": "", "tool_calls": []}
        for block in data.get("content", []):
            if block["type"] == "text":
                result["content"] += block["text"]
            elif block["type"] == "tool_use":
                result["tool_calls"].append({
                    "id": block["id"],
                    "type": "function",
                    "function": {"name": block["name"], "arguments": block.get("input", {})},
                })
        return result

    async def _anthropic_stream(self, messages, tools, system) -> AsyncGenerator[dict, None]:
        url = f"{self.settings.llm_base_url}/v1/messages"
        payload = {"model": self.settings.llm_model, "max_tokens": 16384, "messages": messages, "stream": True}
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [{"name": t["name"], "description": t.get("description", ""),
                                  "input_schema": t.get("inputSchema", t.get("parameters", {}))} for t in tools]

        async with self.client.stream("POST", url, json=payload, headers=self._anthropic_headers()) as resp:
            resp.raise_for_status()
            full_content = ""
            tool_calls = []
            current_tool: dict | None = None
            current_tool_json = ""

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                etype = event.get("type", "")

                if etype == "content_block_start":
                    block = event.get("content_block", {})
                    if block.get("type") == "tool_use":
                        current_tool = {"id": block["id"], "name": block["name"]}
                        current_tool_json = ""

                elif etype == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        full_content += delta["text"]
                        yield {"type": "text_delta", "text": delta["text"]}
                    elif delta.get("type") == "input_json_delta":
                        current_tool_json += delta.get("partial_json", "")

                elif etype == "content_block_stop":
                    if current_tool:
                        args = json.loads(current_tool_json) if current_tool_json else {}
                        call = {
                            "id": current_tool["id"],
                            "type": "function",
                            "function": {"name": current_tool["name"], "arguments": args},
                        }
                        tool_calls.append(call)
                        yield {"type": "tool_call", **call}
                        current_tool = None

                elif etype == "message_stop":
                    break

            yield {"type": "done", "content": full_content, "tool_calls": tool_calls}
