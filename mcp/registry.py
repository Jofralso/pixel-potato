"""
MCP (Model Context Protocol) server registry and client.
Manages launching, connecting to, and calling tools on MCP servers.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp.client import MCPClient

logger = logging.getLogger(__name__)


@dataclass
class MCPToolDef:
    name: str
    description: str = ""
    inputSchema: dict = field(default_factory=dict)

    def model_dump(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema,
        }


@dataclass
class MCPServer:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    tools: list[MCPToolDef] = field(default_factory=list)
    status: str = "stopped"
    client: MCPClient | None = None


class MCPRegistry:
    def __init__(self):
        self.servers: dict[str, MCPServer] = {}

    async def load_from_config(self, config_path: str):
        path = Path(config_path)
        if not path.exists():
            logger.info(f"No MCP config found at {config_path}, skipping")
            return

        with open(path) as f:
            config = json.load(f)

        for name, server_config in config.get("mcpServers", {}).items():
            server = MCPServer(
                name=name,
                command=server_config["command"],
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
            )
            self.servers[name] = server
            await self._start_server(name)

    async def _start_server(self, name: str):
        server = self.servers[name]
        try:
            client = MCPClient(
                command=server.command,
                args=server.args,
                env=server.env,
            )
            await client.connect()
            server.client = client
            server.status = "running"

            # Discover tools
            tools_response = await client.list_tools()
            server.tools = [
                MCPToolDef(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    inputSchema=t.get("inputSchema", {}),
                )
                for t in tools_response
            ]
            logger.info(
                f"MCP server '{name}' started with {len(server.tools)} tools"
            )
        except Exception as e:
            server.status = f"error: {e}"
            logger.error(f"Failed to start MCP server '{name}': {e}")

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: dict
    ) -> str:
        server = self.servers.get(server_name)
        if not server or not server.client:
            return f"MCP server '{server_name}' not available"

        try:
            result = await server.client.call_tool(tool_name, arguments)
            return json.dumps(result) if not isinstance(result, str) else result
        except Exception as e:
            logger.error(f"MCP tool call failed: {server_name}/{tool_name}: {e}")
            return f"Error: {e}"

    async def shutdown_all(self):
        for name, server in self.servers.items():
            if server.client:
                try:
                    await server.client.disconnect()
                except Exception:
                    pass
                server.status = "stopped"
