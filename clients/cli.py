#!/usr/bin/env python3
"""
PixelPotato 🥔 CLI — streaming terminal client.
Token-by-token display, tool call visualization, Claude Code-like UX.
"""

import asyncio
import json
import sys

import websockets


DEFAULT_URL = "ws://localhost:8000/ws"

# ANSI escape codes
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
MAGENTA = "\033[35m"
CLEAR_LINE = "\033[2K\r"


class AgentCLI:
    def __init__(self, url: str = DEFAULT_URL):
        self.url = url
        self.ws = None
        self.session_id = None
        self.running = True
        self._streaming_text = False  # True while receiving text_delta tokens

    async def connect(self):
        print(f"{DIM}Connecting to {self.url}...{RESET}")
        self.ws = await websockets.connect(self.url, max_size=2**22)

        msg = json.loads(await self.ws.recv())
        if msg["type"] == "error":
            print(f"{RED}Error: {msg['message']}{RESET}")
            sys.exit(1)

        self.session_id = msg.get("session_id", "unknown")
        print(f"{GREEN}Connected!{RESET} Session: {DIM}{self.session_id[:8]}{RESET}")
        print(f"{DIM}Type your message and press Enter. /quit to exit, /cancel to stop.{RESET}\n")

    async def send_message(self, message: str):
        await self.ws.send(json.dumps({"type": "chat", "message": message}))

    async def receive_events(self):
        """Process server events until a terminal event (done/error/cancelled)."""
        while True:
            try:
                raw = await self.ws.recv()
                event = json.loads(raw)
                self._render_event(event)

                if event.get("type") in ("done", "error", "cancelled"):
                    break
            except websockets.ConnectionClosed:
                print(f"\n{RED}Connection lost.{RESET}")
                self.running = False
                break

    def _end_streaming(self):
        """Close a text streaming block if open."""
        if self._streaming_text:
            print(f"{RESET}\n")
            self._streaming_text = False

    def _render_event(self, event: dict):
        etype = event.get("type", "")

        if etype == "text_delta":
            # Token-by-token streaming — append to current line
            if not self._streaming_text:
                print(f"\n{CYAN}{BOLD}🥔 ", end="", flush=True)
                self._streaming_text = True
            print(f"{RESET}{event.get('content', '')}", end="", flush=True)

        elif etype == "text":
            # Full text block (non-streaming fallback)
            self._end_streaming()
            print(f"\n{CYAN}{BOLD}🥔 {RESET}{event.get('content', '')}\n")

        elif etype == "status":
            self._end_streaming()
            status = event.get("message", "")
            round_num = event.get("round", "")
            round_str = f" [round {round_num}]" if round_num else ""
            print(f"{DIM}  ● {status}{round_str}{RESET}", flush=True)

        elif etype == "thinking":
            self._end_streaming()
            thought = event.get("content", "")
            print(f"{DIM}{MAGENTA}  💭 {thought}{RESET}", flush=True)

        elif etype == "plan":
            self._end_streaming()
            plan = event.get("plan", {})
            title = plan.get("title", "Plan")
            steps = plan.get("steps", [])
            status_sym = {"pending": "○", "in-progress": "◐", "done": "●", "skipped": "⊘"}
            status_color = {"pending": DIM, "in-progress": YELLOW, "done": GREEN, "skipped": DIM}
            print(f"\n{BOLD}{MAGENTA}  📋 {title}{RESET}")
            for s in steps:
                st = s.get("status", "pending")
                sym = status_sym.get(st, "○")
                clr = status_color.get(st, DIM)
                print(f"  {clr}  {sym} {s.get('title', '?')}{RESET}")
            print()

        elif etype == "tool_call":
            self._end_streaming()
            tool = event.get("tool", "?")
            tool_id = event.get("id", "")[:8]
            args = event.get("arguments", {})

            # Don't show verbose details for think/plan/memory tools
            if tool in ("think", "plan", "memory"):
                return  # these have their own events

            print(f"\n{YELLOW}  ▶ {tool}{RESET} {DIM}{tool_id}{RESET}")
            for k, v in args.items():
                val = str(v)
                # Truncate long values but show first/last
                if len(val) > 120:
                    val = val[:80] + f"...({len(val)} chars)"
                print(f"{DIM}    {k}: {val}{RESET}")

        elif etype == "tool_result":
            tool_name = event.get("tool", "")
            # Skip display for internal tools (they have their own events)
            if tool_name in ("think", "plan", "memory"):
                return
            result = event.get("result", "")
            lines = result.split("\n")
            # Show compact preview
            max_lines = 8
            preview = "\n".join(f"    {l}" for l in lines[:max_lines])
            if len(lines) > max_lines:
                preview += f"\n    {DIM}... ({len(lines) - max_lines} more lines){RESET}"
            name_str = f" ({tool_name})" if tool_name else ""
            print(f"{GREEN}  ✓{name_str}{RESET}\n{DIM}{preview}{RESET}")

        elif etype == "done":
            self._end_streaming()

        elif etype == "error":
            self._end_streaming()
            print(f"\n{RED}✗ Error: {event.get('message', 'Unknown error')}{RESET}\n")

        elif etype == "cancelled":
            self._end_streaming()
            print(f"\n{YELLOW}Cancelled.{RESET}\n")

    async def run(self):
        await self.connect()

        loop = asyncio.get_event_loop()

        while self.running:
            try:
                user_input = await loop.run_in_executor(
                    None, lambda: input(f"{GREEN}You:{RESET} ")
                )
            except (EOFError, KeyboardInterrupt):
                print(f"\n{DIM}🥔 Potato out. See ya!{RESET}")
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.lower() in ("/quit", "/exit", "/q"):
                print(f"{DIM}🥔 *rolls off desk* Bye!{RESET}")
                break

            if user_input.lower() == "/cancel":
                await self.ws.send(json.dumps({"type": "cancel"}))
                continue

            if user_input.lower() == "/clear":
                print("\033[2J\033[H")  # clear terminal
                continue

            await self.send_message(user_input)
            await self.receive_events()

        if self.ws:
            await self.ws.close()


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════╗
║  🥔  PixelPotato                                 ║
║  A suspiciously productive couch potato          ║
║  Local AI · MCP · Claude Code vibes              ║
╚══════════════════════════════════════════════════╝{RESET}
""")

    client = AgentCLI(url)
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print(f"\n{DIM}🥔 Interrupted. Bye!{RESET}")


if __name__ == "__main__":
    main()
