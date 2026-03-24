"""
Agent orchestrator: drives the LLM ↔ tool loop, similar to Claude Code.
Streams events back to the client via async generators.
"""

import json
import logging
from typing import AsyncGenerator

from agent.session import Session
from agent.llm import LLMClient
from mcp.registry import MCPRegistry
from tools.builtin import BUILTIN_TOOLS, execute_builtin_tool
from config.settings import Settings

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 25  # safety limit to prevent infinite loops


class AgentOrchestrator:
    def __init__(self, mcp_registry: MCPRegistry, settings: Settings):
        self.mcp_registry = mcp_registry
        self.settings = settings
        self.llm = LLMClient(settings)

    def _build_tools_schema(self) -> list[dict]:
        tools = []
        # Built-in tools
        for tool in BUILTIN_TOOLS:
            tools.append(tool.schema())

        # MCP tools
        for server_name, server in self.mcp_registry.servers.items():
            for tool in server.tools:
                schema = tool.model_dump()
                schema["name"] = f"mcp__{server_name}__{tool.name}"
                tools.append(schema)

        return tools

    async def _execute_tool_call(self, name: str, arguments: dict) -> str:
        # Check if it's an MCP tool
        if name.startswith("mcp__"):
            parts = name.split("__", 2)
            if len(parts) == 3:
                _, server_name, tool_name = parts
                return await self.mcp_registry.call_tool(
                    server_name, tool_name, arguments
                )

        # Otherwise it's a built-in tool
        return await execute_builtin_tool(name, arguments)

    async def run(self, session: Session) -> AsyncGenerator[dict, None]:
        session.reset_cancel()
        tools_schema = self._build_tools_schema()

        system_prompt = (
            "You are PixelPotato 🥔 — a suspiciously productive couch potato "
            "that codes, designs, and handles UI needs. You speak casually with "
            "dry humor and potato puns when appropriate, but you're secretly "
            "brilliant at dev work, Figma-to-code, and UI/UX tasks. "
            "You have access to tools for file operations, shell commands, and MCP servers. "
            "Use tools to accomplish tasks. Always read files before editing them. "
            "Be thorough and complete tasks fully. Never half-bake anything (except yourself). "
            "Working directory: /workspace"
        )

        for round_num in range(MAX_TOOL_ROUNDS):
            if session.is_cancelled():
                yield {"type": "cancelled"}
                return

            yield {"type": "thinking", "round": round_num + 1}

            response = await self.llm.chat(
                messages=session.get_history(),
                tools=tools_schema,
                system=system_prompt,
            )

            # Handle text response
            if response.get("content"):
                text = response["content"]
                session.add_message("assistant", text)
                yield {"type": "text", "content": text}

            # Handle tool calls
            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                yield {"type": "done"}
                return

            # Execute each tool call
            tool_results = []
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("arguments", {})
                tool_id = tc.get("id", "")

                yield {
                    "type": "tool_call",
                    "tool": tool_name,
                    "arguments": tool_args,
                }

                try:
                    result = await self._execute_tool_call(tool_name, tool_args)
                except Exception as e:
                    logger.exception(f"Tool execution failed: {tool_name}")
                    result = f"Error executing tool {tool_name}: {e}"

                tool_results.append({
                    "tool_call_id": tool_id,
                    "name": tool_name,
                    "content": result,
                })

                yield {
                    "type": "tool_result",
                    "tool": tool_name,
                    "result": result[:2000],  # truncate for display
                }

            # Add assistant message with tool calls + tool results to history
            session.add_message(
                "assistant",
                json.dumps({"tool_calls": tool_calls}),
            )
            session.add_message(
                "tool",
                json.dumps(tool_results),
            )

        yield {"type": "error", "message": "Reached maximum tool rounds"}
