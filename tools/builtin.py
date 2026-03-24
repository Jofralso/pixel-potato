"""
Built-in tools — full Claude Code-equivalent tool set.
File I/O, editing, search, shell, tree, multi-edit, and diagnostics.
"""

import asyncio
import os
import glob as glob_module
import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/workspace")


# ── Security ──────────────────────────────────────────────────

def _safe_path(path: str) -> str:
    """Resolve path and ensure it lives under WORKSPACE_DIR."""
    if os.path.isabs(path):
        resolved = os.path.realpath(path)
    else:
        resolved = os.path.realpath(os.path.join(WORKSPACE_DIR, path))
    workspace_real = os.path.realpath(WORKSPACE_DIR)
    if not resolved.startswith(workspace_real + "/") and resolved != workspace_real:
        raise PermissionError(f"Access denied: path escapes workspace: {path}")
    return resolved


# ── Tool definitions ──────────────────────────────────────────

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
        description=(
            "Read a file from the workspace. Returns numbered lines. "
            "Use start_line/end_line for large files. Always read before editing."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (relative to workspace or absolute)"},
                "start_line": {"type": "integer", "description": "Start line number (1-based, inclusive)"},
                "end_line": {"type": "integer", "description": "End line number (1-based, inclusive)"},
            },
            "required": ["path"],
        },
    ),
    ToolDef(
        name="write_file",
        description="Create a new file or completely overwrite an existing file. Creates directories as needed.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (relative to workspace or absolute)"},
                "content": {"type": "string", "description": "Complete file content"},
            },
            "required": ["path", "content"],
        },
    ),
    ToolDef(
        name="edit_file",
        description=(
            "Replace an exact string in a file. The old_string must match exactly one location "
            "in the file (including whitespace and indentation). Include 3-5 lines of context "
            "before and after the target text to ensure uniqueness."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "old_string": {"type": "string", "description": "Exact text to find (must match exactly once)"},
                "new_string": {"type": "string", "description": "Replacement text"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    ),
    ToolDef(
        name="multi_edit",
        description=(
            "Apply multiple find-and-replace operations across one or more files in a single call. "
            "Each edit has path, old_string, new_string. Applied sequentially."
        ),
        parameters={
            "type": "object",
            "properties": {
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "old_string": {"type": "string"},
                            "new_string": {"type": "string"},
                        },
                        "required": ["path", "old_string", "new_string"],
                    },
                    "description": "Array of edit operations",
                },
            },
            "required": ["edits"],
        },
    ),
    ToolDef(
        name="list_directory",
        description="List files and directories at a path. Shows type (file/dir) and size.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (default: workspace root)"},
            },
            "required": [],
        },
    ),
    ToolDef(
        name="tree",
        description=(
            "Show workspace directory tree structure. "
            "Use this first to understand the project layout before making changes."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Root path (default: workspace root)"},
                "depth": {"type": "integer", "description": "Max depth (default: 3)"},
            },
            "required": [],
        },
    ),
    ToolDef(
        name="search_files",
        description="Search for text/regex pattern in files using grep. Returns matching lines with file:line context.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Search pattern (regex by default)"},
                "path": {"type": "string", "description": "Directory to search (default: workspace root)"},
                "include": {"type": "string", "description": "File glob to include (e.g. '*.py', '*.ts')"},
                "fixed_string": {"type": "boolean", "description": "Treat pattern as literal text, not regex"},
            },
            "required": ["pattern"],
        },
    ),
    ToolDef(
        name="run_command",
        description=(
            "Execute a shell command in the workspace. Use for: git operations, build, test, "
            "install packages, curl, docker, etc. Captures stdout+stderr. Max 5 min timeout."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "cwd": {"type": "string", "description": "Working directory (default: workspace root)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 120, max: 300)"},
            },
            "required": ["command"],
        },
    ),
    ToolDef(
        name="glob_search",
        description="Find files matching a glob pattern (e.g. '**/*.py', 'src/**/*.tsx').",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (recursive with **)"},
            },
            "required": ["pattern"],
        },
    ),
    ToolDef(
        name="file_info",
        description="Get metadata about a file: size, line count, last modified time, permissions.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
            },
            "required": ["path"],
        },
    ),
]


# ── Dispatch ──────────────────────────────────────────────────

_DISPATCH = {}


def _register(name):
    def decorator(fn):
        _DISPATCH[name] = fn
        return fn
    return decorator


async def execute_builtin_tool(name: str, arguments: dict) -> str:
    handler = _DISPATCH.get(name)
    if handler:
        return await handler(arguments)
    return f"Unknown tool: {name}"


# ── Implementations ──────────────────────────────────────────

@_register("read_file")
async def _read_file(args: dict) -> str:
    path = _safe_path(args["path"])
    try:
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()

        start = args.get("start_line")
        end = args.get("end_line")

        if start is not None:
            start = max(1, start)
            end = end or len(lines)
            end = min(end, len(lines))
            selected = lines[start - 1:end]
            numbered = [f"{i}: {l}" for i, l in enumerate(selected, start=start)]
            header = f"[Lines {start}-{end} of {len(lines)}]"
        else:
            # For large files, show first 500 lines with a warning
            if len(lines) > 500:
                selected = lines[:500]
                numbered = [f"{i}: {l}" for i, l in enumerate(selected, start=1)]
                header = f"[Showing first 500 of {len(lines)} lines — use start_line/end_line for more]"
            else:
                numbered = [f"{i}: {l}" for i, l in enumerate(lines, start=1)]
                header = f"[{len(lines)} lines]"

        return header + "\n" + "".join(numbered)
    except FileNotFoundError:
        return f"Error: file not found: {args['path']}"
    except Exception as e:
        return f"Error reading file: {e}"


@_register("write_file")
async def _write_file(args: dict) -> str:
    path = _safe_path(args["path"])
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = args["content"]
        with open(path, "w") as f:
            f.write(content)
        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        return f"✓ Wrote {len(content)} bytes ({lines} lines) to {args['path']}"
    except Exception as e:
        return f"Error writing file: {e}"


@_register("edit_file")
async def _edit_file(args: dict) -> str:
    path = _safe_path(args["path"])
    try:
        with open(path, "r") as f:
            content = f.read()

        old = args["old_string"]
        new = args["new_string"]

        count = content.count(old)
        if count == 0:
            # Help debug: show similar lines
            old_lines = old.strip().split("\n")
            if old_lines:
                first_line = old_lines[0].strip()
                candidates = [
                    l.rstrip() for l in content.split("\n")
                    if first_line[:30] in l
                ][:3]
                hint = ""
                if candidates:
                    hint = "\nSimilar lines found:\n" + "\n".join(f"  {c}" for c in candidates)
                return f"Error: old_string not found in {args['path']}.{hint}"
            return f"Error: old_string not found in {args['path']}"

        if count > 1:
            return f"Error: old_string found {count} times in {args['path']} — must be unique. Add more context lines."

        new_content = content.replace(old, new, 1)
        with open(path, "w") as f:
            f.write(new_content)

        # Show a compact diff
        old_lines = old.split("\n")
        new_lines = new.split("\n")
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=1))
        diff_preview = "\n".join(diff[:20])
        if len(diff) > 20:
            diff_preview += f"\n... ({len(diff) - 20} more diff lines)"

        return f"✓ Edited {args['path']}\n{diff_preview}"
    except FileNotFoundError:
        return f"Error: file not found: {args['path']}"
    except Exception as e:
        return f"Error editing file: {e}"


@_register("multi_edit")
async def _multi_edit(args: dict) -> str:
    edits = args.get("edits", [])
    results = []
    for i, edit in enumerate(edits):
        r = await _edit_file(edit)
        results.append(f"[{i+1}/{len(edits)}] {r}")
    return "\n".join(results)


@_register("list_directory")
async def _list_directory(args: dict) -> str:
    path = _safe_path(args.get("path", "."))
    try:
        entries = sorted(os.listdir(path))
        result = []
        for entry in entries:
            if entry.startswith(".") and entry not in (".env", ".gitignore"):
                continue  # skip hidden except common ones
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                result.append(f"📁 {entry}/")
            else:
                size = os.path.getsize(full)
                if size > 1024 * 1024:
                    size_str = f"{size / (1024*1024):.1f}MB"
                elif size > 1024:
                    size_str = f"{size / 1024:.1f}KB"
                else:
                    size_str = f"{size}B"
                result.append(f"   {entry}  ({size_str})")
        return "\n".join(result) if result else "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {e}"


@_register("tree")
async def _tree(args: dict) -> str:
    root = _safe_path(args.get("path", "."))
    max_depth = min(args.get("depth", 3), 6)

    SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv",
            ".next", "dist", "build", ".mypy_cache", ".pytest_cache",
            "target", ".tox", "*.egg-info", ".DS_Store"}

    lines = []
    file_count = 0
    MAX_ENTRIES = 500

    def _walk(current: str, prefix: str, depth: int):
        nonlocal file_count
        if depth > max_depth or file_count > MAX_ENTRIES:
            return

        try:
            entries = sorted(os.listdir(current))
        except PermissionError:
            return

        dirs = []
        files = []
        for e in entries:
            if e in SKIP or any(e.endswith(s.lstrip("*")) for s in SKIP if s.startswith("*")):
                continue
            if e.startswith(".") and e not in (".env", ".gitignore", ".dockerignore"):
                continue
            full = os.path.join(current, e)
            if os.path.isdir(full):
                dirs.append(e)
            else:
                files.append(e)

        items = [(d, True) for d in dirs] + [(f, False) for f in files]

        for i, (name, is_dir) in enumerate(items):
            file_count += 1
            if file_count > MAX_ENTRIES:
                lines.append(f"{prefix}... (truncated at {MAX_ENTRIES} entries)")
                return

            connector = "├── " if i < len(items) - 1 else "└── "
            if is_dir:
                lines.append(f"{prefix}{connector}{name}/")
                extension = "│   " if i < len(items) - 1 else "    "
                _walk(os.path.join(current, name), prefix + extension, depth + 1)
            else:
                lines.append(f"{prefix}{connector}{name}")

    root_name = os.path.basename(root) or "."
    lines.append(f"{root_name}/")
    _walk(root, "", 1)

    return "\n".join(lines)


@_register("search_files")
async def _search_files(args: dict) -> str:
    search_path = _safe_path(args.get("path", "."))
    pattern = args["pattern"]
    include = args.get("include", "")
    fixed = args.get("fixed_string", False)

    cmd = ["grep", "-rn", "--color=never", "-I"]  # -I skips binary
    if fixed:
        cmd.append("-F")
    if include:
        cmd.extend(["--include", include])
    cmd.extend(["--", pattern, search_path])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = stdout.decode(errors="replace")

        # Make paths relative to workspace
        workspace_real = os.path.realpath(WORKSPACE_DIR)
        output = output.replace(workspace_real + "/", "")

        lines = output.split("\n")
        if len(lines) > 150:
            return "\n".join(lines[:150]) + f"\n\n... ({len(lines) - 150} more matches)"
        return output.strip() or "No matches found."
    except asyncio.TimeoutError:
        return "Search timed out after 30s"
    except Exception as e:
        return f"Search error: {e}"


@_register("run_command")
async def _run_command(args: dict) -> str:
    command = args["command"]
    timeout = min(args.get("timeout", 120), 300)
    cwd = args.get("cwd")
    if cwd:
        cwd = _safe_path(cwd)
    else:
        cwd = WORKSPACE_DIR

    # Security: block obviously destructive patterns
    blocked = ["rm -rf /", "rm -rf /*", "mkfs.", "dd if=/dev/zero of=/dev/sd",
               "> /dev/sd", ":(){ :|:& };:"]
    for b in blocked:
        if b in command:
            return f"Blocked dangerous command: {b}"

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env={**os.environ, "TERM": "dumb", "NO_COLOR": "1"},
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        parts = []
        if stdout:
            parts.append(stdout.decode(errors="replace"))
        if stderr:
            stderr_text = stderr.decode(errors="replace").strip()
            if stderr_text:
                parts.append(f"STDERR:\n{stderr_text}")

        parts.append(f"[exit code: {proc.returncode}]")
        output = "\n".join(parts)

        # Truncate massive output
        if len(output) > 60000:
            output = output[:30000] + "\n\n... (middle truncated) ...\n\n" + output[-10000:]

        return output
    except asyncio.TimeoutError:
        return f"Command timed out after {timeout}s. Consider increasing the timeout."
    except Exception as e:
        return f"Command error: {e}"


@_register("glob_search")
async def _glob_search(args: dict) -> str:
    pattern = args["pattern"]
    matches = glob_module.glob(os.path.join(WORKSPACE_DIR, pattern), recursive=True)
    results = sorted(os.path.relpath(m, WORKSPACE_DIR) for m in matches)

    # Filter out common junk
    skip = {"node_modules", "__pycache__", ".git", ".venv", "venv"}
    results = [r for r in results if not any(s in r.split(os.sep) for s in skip)]

    if not results:
        return "No files found matching pattern."
    if len(results) > 300:
        return "\n".join(results[:300]) + f"\n\n... ({len(results) - 300} more files)"
    return "\n".join(results)


@_register("file_info")
async def _file_info(args: dict) -> str:
    path = _safe_path(args["path"])
    try:
        stat = os.stat(path)
        import time
        modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))

        info = {
            "path": args["path"],
            "size": stat.st_size,
            "modified": modified,
            "permissions": oct(stat.st_mode)[-3:],
        }

        if os.path.isfile(path):
            with open(path, "r", errors="replace") as f:
                line_count = sum(1 for _ in f)
            info["lines"] = line_count
            info["type"] = "file"
        else:
            info["type"] = "directory"

        return "\n".join(f"{k}: {v}" for k, v in info.items())
    except FileNotFoundError:
        return f"File not found: {args['path']}"
    except Exception as e:
        return f"Error: {e}"
