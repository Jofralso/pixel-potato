#!/usr/bin/env python3
"""
Interactive CLI client for the Local AI Agent.
Connects via WebSocket and provides a Claude Code-like terminal experience.
"""

import asyncio
import json
import sys
import signal

import websockets


DEFAULT_URL = "ws://localhost:8000/ws"

# ANSI colors
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


class AgentCLI:
    def __init__(self, url: str = DEFAULT_URL):
        self.url = url
        self.ws = None
        self.session_id = None
        self.running = True

    async def connect(self):
        print(f"{DIM}Connecting to {self.url}...{RESET}")
        self.ws = await websockets.connect(self.url)

        # Wait for session start
        msg = json.loads(await self.ws.recv())
        if msg["type"] == "error":
            print(f"{RED}Error: {msg['message']}{RESET}")
            sys.exit(1)

        self.session_id = msg.get("session_id", "unknown")
        print(f"{GREEN}Connected!{RESET} Session: {DIM}{self.session_id}{RESET}")
        print(f"{DIM}Type your message and press Enter. Use /quit to exit.{RESET}\n")

    async def send_message(self, message: str):
        await self.ws.send(json.dumps({"type": "chat", "message": message}))

    async def receive_events(self):
        while True:
            try:
                raw = await self.ws.recv()
                event = json.loads(raw)
                self._render_event(event)

                if event["type"] in ("done", "error", "cancelled"):
                    break
            except websockets.ConnectionClosed:
                print(f"\n{RED}Connection lost.{RESET}")
                self.running = False
                break

    def _render_event(self, event: dict):
        etype = event.get("type", "")

        if etype == "thinking":
            round_num = event.get("round", "?")
            print(f"{DIM}  [round {round_num}]{RESET}", end="", flush=True)

        elif etype == "text":
            print(f"\n{CYAN}{BOLD}Agent:{RESET} {event['content']}\n")

        elif etype == "tool_call":
            tool = event.get("tool", "?")
            args = event.get("arguments", {})
            print(f"\n{YELLOW}  ▶ {tool}{RESET}", end="")
            # Show key arguments
            for k, v in args.items():
                val = str(v)[:80]
                print(f"\n{DIM}    {k}: {val}{RESET}", end="")
            print()

        elif etype == "tool_result":
            result = event.get("result", "")
            lines = result.split("\n")
            preview = "\n".join(lines[:5])
            if len(lines) > 5:
                preview += f"\n    ... ({len(lines) - 5} more lines)"
            print(f"{DIM}  ✓ {preview}{RESET}")

        elif etype == "done":
            pass

        elif etype == "error":
            print(f"\n{RED}Error: {event.get('message', 'Unknown error')}{RESET}")

        elif etype == "cancelled":
            print(f"\n{YELLOW}Cancelled.{RESET}")

    async def run(self):
        await self.connect()

        loop = asyncio.get_event_loop()

        while self.running:
            try:
                user_input = await loop.run_in_executor(
                    None, lambda: input(f"{GREEN}You:{RESET} ")
                )
            except (EOFError, KeyboardInterrupt):
                print(f"\n{DIM}Goodbye!{RESET}")
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.lower() in ("/quit", "/exit", "/q"):
                print(f"{DIM}Goodbye!{RESET}")
                break

            if user_input.lower() == "/cancel":
                await self.ws.send(json.dumps({"type": "cancel"}))
                continue

            await self.send_message(user_input)
            await self.receive_events()

        if self.ws:
            await self.ws.close()


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════╗
║       Local AI Agent CLI             ║
║   Claude Code-like experience        ║
╚══════════════════════════════════════╝{RESET}
""")

    client = AgentCLI(url)
    asyncio.run(client.run())


if __name__ == "__main__":
    main()
