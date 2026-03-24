"""
MCP stdio client – launches and communicates with MCP servers over stdin/stdout
using the Model Context Protocol (JSON-RPC over stdio).
"""

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_REQUEST_ID = 0


def _next_id() -> int:
    global _REQUEST_ID
    _REQUEST_ID += 1
    return _REQUEST_ID


class MCPClient:
    """Connects to an MCP server via stdio (subprocess)."""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ):
        self.command = command
        self.args = args or []
        self.env = {**os.environ, **(env or {})}
        self._process: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()

    async def connect(self):
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
        )
        # Send initialize
        resp = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pixelpotato", "version": "1.0.0"},
        })
        # Send initialized notification
        await self._send_notification("notifications/initialized", {})
        return resp

    async def list_tools(self) -> list[dict]:
        resp = await self._send_request("tools/list", {})
        return resp.get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> Any:
        resp = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        # Extract text content from response
        content = resp.get("content", [])
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts) if texts else json.dumps(resp)

    async def disconnect(self):
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()

    async def _send_request(self, method: str, params: dict) -> dict:
        async with self._lock:
            req_id = _next_id()
            message = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params,
            }
            await self._write(message)
            return await self._read_response(req_id)

    async def _send_notification(self, method: str, params: dict):
        async with self._lock:
            message = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
            await self._write(message)

    async def _write(self, message: dict):
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP server process not running")
        data = json.dumps(message)
        content = f"Content-Length: {len(data)}\r\n\r\n{data}"
        self._process.stdin.write(content.encode())
        await self._process.stdin.drain()

    async def _read_response(self, expected_id: int) -> dict:
        if not self._process or not self._process.stdout:
            raise RuntimeError("MCP server process not running")

        while True:
            # Read headers
            header_line = await asyncio.wait_for(
                self._process.stdout.readline(), timeout=30.0
            )
            header = header_line.decode().strip()

            content_length = 0
            if header.startswith("Content-Length:"):
                content_length = int(header.split(":")[1].strip())

            # Read blank line separator
            await self._process.stdout.readline()

            # Read body
            body = await asyncio.wait_for(
                self._process.stdout.readexactly(content_length), timeout=30.0
            )
            data = json.loads(body.decode())

            if data.get("id") == expected_id:
                if "error" in data:
                    raise RuntimeError(
                        f"MCP error: {data['error'].get('message', data['error'])}"
                    )
                return data.get("result", {})
