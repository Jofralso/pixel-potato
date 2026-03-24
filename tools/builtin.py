"""
Built-in tools available to the agent: file operations, shell, search.
These mirror the core capabilities of Claude Code.
"""

import asyncio
import os
import glob as glob_module
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/workspace")

# Security: restrict file operations to workspace
def _safe_path(path: str) -> str:
    resolved = os.path.realpath(os.path.join(WORKSPACE_DIR, path))
    if not resolved.startswith(os.path.realpath(WORKSPACE_DIR)):
        raise PermissionError(f"Access denied: path escapes workspace: {path}")
    return resolved


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameters,
        }


BUILTIN_TOOLS = [
    ToolDef(
        name="read_file",
        description="Read the contents of a file. Returns the file content as text.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path from workspace root"},
                "start_line": {"type": "integer", "description": "Start line (1-based, optional)"},
                "end_line": {"type": "integer", "description": "End line (1-based, inclusive, optional)"},
            },
            "required": ["path"],
        },
    ),
    ToolDef(
        name="write_file",
        description="Write content to a file. Creates parent directories if needed.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path from workspace root"},
                "content": {"type": "string", "description": "File content to write"},
            },
            "required": ["path", "content"],
        },
    ),
    ToolDef(
        name="edit_file",
        description="Replace an exact string in a file with new content.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path from workspace root"},
                "old_string": {"type": "string", "description": "Exact text to find and replace"},
                "new_string": {"type": "string", "description": "Replacement text"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    ),
    ToolDef(
        name="list_directory",
        description="List files and directories at a given path.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path from workspace root (default: '.')"},
            },
            "required": [],
        },
    ),
    ToolDef(
        name="search_files",
        description="Search for text pattern in files using grep.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Search pattern (regex)"},
                "path": {"type": "string", "description": "Directory to search in (default: '.')"},
                "include": {"type": "string", "description": "File glob pattern to include"},
            },
            "required": ["pattern"],
        },
    ),
    ToolDef(
        name="run_command",
        description="Execute a shell command in the workspace directory. Use for build, test, git, etc.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)"},
            },
            "required": ["command"],
        },
    ),
    ToolDef(
        name="glob_search",
        description="Find files matching a glob pattern.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g. '**/*.py')"},
            },
            "required": ["pattern"],
        },
    ),
]


async def execute_builtin_tool(name: str, arguments: dict) -> str:
    if name == "read_file":
        return await _read_file(arguments)
    elif name == "write_file":
        return await _write_file(arguments)
    elif name == "edit_file":
        return await _edit_file(arguments)
    elif name == "list_directory":
        return await _list_directory(arguments)
    elif name == "search_files":
        return await _search_files(arguments)
    elif name == "run_command":
        return await _run_command(arguments)
    elif name == "glob_search":
        return await _glob_search(arguments)
    else:
        return f"Unknown tool: {name}"


async def _read_file(args: dict) -> str:
    path = _safe_path(args["path"])
    try:
        with open(path, "r") as f:
            lines = f.readlines()

        start = args.get("start_line")
        end = args.get("end_line")
        if start is not None:
            start = max(1, start) - 1
            end = end if end else len(lines)
            lines = lines[start:end]

        return "".join(lines)
    except FileNotFoundError:
        return f"File not found: {args['path']}"
    except Exception as e:
        return f"Error reading file: {e}"


async def _write_file(args: dict) -> str:
    path = _safe_path(args["path"])
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(args["content"])
        return f"Successfully wrote to {args['path']}"
    except Exception as e:
        return f"Error writing file: {e}"


async def _edit_file(args: dict) -> str:
    path = _safe_path(args["path"])
    try:
        with open(path, "r") as f:
            content = f.read()

        old = args["old_string"]
        new = args["new_string"]

        count = content.count(old)
        if count == 0:
            return "Error: old_string not found in file"
        if count > 1:
            return f"Error: old_string found {count} times, must be unique"

        content = content.replace(old, new, 1)
        with open(path, "w") as f:
            f.write(content)

        return f"Successfully edited {args['path']}"
    except FileNotFoundError:
        return f"File not found: {args['path']}"
    except Exception as e:
        return f"Error editing file: {e}"


async def _list_directory(args: dict) -> str:
    path = _safe_path(args.get("path", "."))
    try:
        entries = sorted(os.listdir(path))
        result = []
        for entry in entries:
            full = os.path.join(path, entry)
            suffix = "/" if os.path.isdir(full) else ""
            result.append(f"{entry}{suffix}")
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory: {e}"


async def _search_files(args: dict) -> str:
    search_path = _safe_path(args.get("path", "."))
    pattern = args["pattern"]
    include = args.get("include", "")

    cmd = ["grep", "-rn", "--color=never"]
    if include:
        cmd.extend(["--include", include])
    cmd.extend([pattern, search_path])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = stdout.decode(errors="replace")
        # Limit output
        lines = output.split("\n")
        if len(lines) > 100:
            return "\n".join(lines[:100]) + f"\n... ({len(lines) - 100} more lines)"
        return output or "No matches found"
    except asyncio.TimeoutError:
        return "Search timed out"
    except Exception as e:
        return f"Search error: {e}"


async def _run_command(args: dict) -> str:
    command = args["command"]
    timeout = min(args.get("timeout", 60), 300)  # cap at 5 minutes

    # Security: basic command blocklist
    blocked = ["rm -rf /", "mkfs", "dd if=", "> /dev/sd"]
    for b in blocked:
        if b in command:
            return f"Blocked dangerous command pattern: {b}"

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=WORKSPACE_DIR,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        output = ""
        if stdout:
            output += stdout.decode(errors="replace")
        if stderr:
            output += "\nSTDERR:\n" + stderr.decode(errors="replace")

        output += f"\n[exit code: {proc.returncode}]"

        # Truncate
        if len(output) > 50000:
            output = output[:50000] + "\n... (output truncated)"

        return output
    except asyncio.TimeoutError:
        return f"Command timed out after {timeout}s"
    except Exception as e:
        return f"Command error: {e}"


async def _glob_search(args: dict) -> str:
    pattern = args["pattern"]
    base = WORKSPACE_DIR
    matches = glob_module.glob(os.path.join(base, pattern), recursive=True)
    # Make paths relative
    results = [os.path.relpath(m, base) for m in sorted(matches)]
    if not results:
        return "No files found matching pattern"
    if len(results) > 200:
        return "\n".join(results[:200]) + f"\n... ({len(results) - 200} more)"
    return "\n".join(results)
