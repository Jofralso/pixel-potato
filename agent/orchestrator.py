"""
Agent orchestrator — the core agentic loop that mirrors Claude Code.

Flow per user message:
  1. (First turn) Inject workspace context: tree, git status, active file
  2. Send conversation + tools to LLM (streaming)
  3. If LLM returns tool_calls → execute each, store results, loop back to step 2
  4. If LLM returns only text → done, yield final text
  5. Safety cap at MAX_TOOL_ROUNDS to prevent infinite loops

Plan-aware: When the agent calls the `plan` tool, the orchestrator emits plan events
to the client for live progress display.
"""

import json
import logging
import os
import asyncio
from typing import AsyncGenerator

from agent.session import Session
from agent.llm import LLMClient
from mcp.registry import MCPRegistry
from tools.builtin import BUILTIN_TOOLS, execute_builtin_tool, get_current_plan
from config.settings import Settings

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 40  # Claude Code typically allows many rounds


SYSTEM_PROMPT = """\
You are PixelPotato 🥔 — a powerful AI coding assistant running locally.
You work exactly like Claude Code: you think step-by-step, use tools extensively, \
and complete tasks fully without asking for permission on routine operations.

## Personality
Casually brilliant with dry humor and the occasional potato pun. \
You're secretly the most productive couch potato in existence. \
You specialize in dev work, Figma-to-code, and UI/UX tasks.

## Planning & Thinking
- For ANY task involving 3+ steps, ALWAYS call the `plan` tool FIRST to create a structured plan.
- Use the `think` tool to reason through complex decisions, weigh trade-offs, or analyze errors before acting.
- Update the plan (action="update") as you complete each step — mark steps "done" or "in-progress".
- When all steps are done, call plan(action="complete").
- Use `memory` to save important context or decisions you'll need to reference later.

## Rules
- ALWAYS read files before editing them.
- Use edit_file for surgical changes (with surrounding context in old_string).
- Use write_file only for new files or full rewrites.
- Use run_command for git, build, test, install, and system tasks.
- Use multi_edit for batch changes across files.
- Use tree to understand project structure before diving in.
- After editing, verify your changes with read_file or run_command.
- Keep going until the task is FULLY complete — don't stop halfway.
- If a tool call fails, analyze the error and try a different approach.
- For complex tasks, break them into steps and execute each one.
- Never output file contents that you can read with tools.

## Working directory
{cwd}

## Environment
- OS: Linux (Docker container)
- Shell: bash
- GPU: NVIDIA RTX 5060 Ti (16GB VRAM)
- Node/npm available for MCP servers
- Git available
"""


class AgentOrchestrator:
    def __init__(self, mcp_registry: MCPRegistry, settings: Settings):
        self.mcp_registry = mcp_registry
        self.settings = settings
        self.llm = LLMClient(settings)

    def _build_tools_schema(self) -> list[dict]:
        tools = []
        for tool in BUILTIN_TOOLS:
            tools.append(tool.schema())
        for server_name, server in self.mcp_registry.servers.items():
            for tool in server.tools:
                schema = tool.model_dump()
                schema["name"] = f"mcp__{server_name}__{tool.name}"
                tools.append(schema)
        return tools

    async def _execute_tool_call(self, name: str, arguments: dict) -> str:
        if name.startswith("mcp__"):
            parts = name.split("__", 2)
            if len(parts) == 3:
                _, server_name, tool_name = parts
                return await self.mcp_registry.call_tool(server_name, tool_name, arguments)
        return await execute_builtin_tool(name, arguments)

    async def _inject_context(self, session: Session):
        """On first message, auto-inject workspace context like Claude Code does."""
        if len(session.messages) > 1:
            return  # only on first turn

        # Get workspace tree (2 levels deep)
        try:
            tree_result = await execute_builtin_tool("tree", {"depth": 2})
            context = f"<workspace_tree>\n{tree_result}\n</workspace_tree>"

            # Try git status
            git_result = await execute_builtin_tool("run_command", {
                "command": "git status --short 2>/dev/null || echo 'Not a git repo'"
            })
            if git_result and "Not a git repo" not in git_result:
                context += f"\n<git_status>\n{git_result.strip()}\n</git_status>"

            # Prepend context to the user message
            last_msg = session.messages[-1]
            if last_msg["role"] == "user":
                last_msg["content"] = context + "\n\n" + last_msg["content"]
        except Exception as e:
            logger.debug(f"Context injection skipped: {e}")

    async def run(self, session: Session) -> AsyncGenerator[dict, None]:
        """Main agentic loop with streaming."""
        session.reset_cancel()
        tools_schema = self._build_tools_schema()
        system = SYSTEM_PROMPT.format(cwd=session.cwd)

        # Inject workspace context on first turn
        await self._inject_context(session)

        for round_num in range(MAX_TOOL_ROUNDS):
            if session.is_cancelled():
                yield {"type": "cancelled"}
                return

            yield {"type": "status", "message": f"Thinking... (round {round_num + 1})"}

            # ── Get provider-specific messages ─────────────
            provider = self.settings.llm_provider
            if provider == "anthropic":
                messages = session.get_messages_anthropic()
            else:
                messages = session.get_messages_openai()

            # ── Stream from LLM ────────────────────────────
            full_content = ""
            tool_calls: list[dict] = []

            async for chunk in self.llm.chat_stream(
                messages=messages,
                tools=tools_schema,
                system=system,
            ):
                ctype = chunk.get("type", "")

                if ctype == "text_delta":
                    yield {"type": "text_delta", "content": chunk["text"]}
                    full_content += chunk["text"]

                elif ctype == "tool_call":
                    tool_calls.append(chunk)
                    yield {
                        "type": "tool_call",
                        "id": chunk.get("id", ""),
                        "tool": chunk.get("function", {}).get("name", ""),
                        "arguments": chunk.get("function", {}).get("arguments", {}),
                    }

                elif ctype == "done":
                    full_content = chunk.get("content", full_content)
                    tool_calls = chunk.get("tool_calls", tool_calls)

            # ── No tool calls → we're done ──────────────────
            if not tool_calls:
                if full_content:
                    session.add_assistant_text(full_content)
                yield {"type": "done"}
                return

            # ── Store assistant message with tool_calls ─────
            oai_tool_calls = []
            for tc in tool_calls:
                fn = tc.get("function", {})
                oai_tool_calls.append({
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": fn.get("name", ""),
                        "arguments": fn.get("arguments", {}),
                    },
                })
            session.add_assistant_tool_calls(full_content or None, oai_tool_calls)

            # ── Execute each tool call ──────────────────────
            for tc in tool_calls:
                if session.is_cancelled():
                    yield {"type": "cancelled"}
                    return

                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                tool_args = fn.get("arguments", {})
                tool_id = tc.get("id", "")

                # For think tool — emit as internal event, don't show full content
                if tool_name == "think":
                    yield {
                        "type": "thinking",
                        "content": tool_args.get("thought", "")[:200] + "...",
                    }

                try:
                    result = await self._execute_tool_call(tool_name, tool_args)
                except Exception as e:
                    logger.exception(f"Tool execution failed: {tool_name}")
                    result = f"Error: {e}"

                # Truncate very large results
                if len(result) > 80000:
                    result = result[:80000] + "\n\n... (output truncated at 80KB)"

                session.add_tool_result(tool_id, tool_name, result)

                # For plan tool — emit the full plan state for client display
                if tool_name == "plan":
                    plan = get_current_plan()
                    if plan:
                        yield {
                            "type": "plan",
                            "plan": plan,
                        }

                yield {
                    "type": "tool_result",
                    "id": tool_id,
                    "tool": tool_name,
                    "result": result[:4000],  # truncate for display to client
                }

            # Loop continues — LLM will see tool results and decide next action

        yield {"type": "error", "message": f"Reached maximum of {MAX_TOOL_ROUNDS} tool rounds"}
