#!/usr/bin/env python3
"""
PixelPotato 🥔 Network Client — RPC wrapper for remote connections.
Allows other users/machines on the same network to access the PixelPotato agent.

Usage:
    python clients/network_client.py --host 192.168.1.100 --port 8000
    python clients/network_client.py --host pixel-potato-agent (if on same Docker network)
"""

import asyncio
import json
import sys
import argparse
from typing import Optional

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets


class NetworkClient:
    def __init__(self, host: str, port: int, scheme: str = "ws"):
        self.host = host
        self.port = port
        self.url = f"{scheme}://{host}:{port}/ws"
        self.ws = None
        self.session_id = None
        self.running = True
        self._streaming_text = False

    async def connect(self):
        """Connect to remote PixelPotato server."""
        print(f"🥔 Connecting to {self.host}:{self.port}...")
        try:
            self.ws = await websockets.connect(self.url, max_size=2**22)
            msg = json.loads(await self.ws.recv())
            
            if msg["type"] == "error":
                print(f"❌ Error: {msg['message']}")
                sys.exit(1)
            
            self.session_id = msg.get("session_id", "unknown")
            print(f"✅ Connected! Session: {self.session_id[:8]}")
            print("Type messages. Press Ctrl+C to exit.\n")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            sys.exit(1)

    async def send_message(self, message: str):
        """Send chat message to agent."""
        if not self.ws:
            return
        
        await self.ws.send(json.dumps({"type": "chat", "message": message}))

    async def receive_events(self):
        """Stream events from server."""
        while True:
            try:
                raw = await self.ws.recv()
                event = json.loads(raw)
                self._render_event(event)

                if event.get("type") in ("done", "error", "cancelled"):
                    break
            except websockets.ConnectionClosed:
                print("\n⚠️ Connection lost.")
                self.running = False
                break

    def _render_event(self, event: dict):
        """Pretty-print server events."""
        etype = event.get("type", "")

        if etype == "text_delta":
            if not self._streaming_text:
                print("🥔 ", end="", flush=True)
                self._streaming_text = True
            print(event.get("text", ""), end="", flush=True)

        elif etype == "tool_call_start":
            if self._streaming_text:
                print("\n")
                self._streaming_text = False
            tool_name = event.get("tool_name", "unknown")
            print(f"\n🔧 Calling tool: {tool_name}")

        elif etype == "tool_call_result":
            result = event.get("result", "")
            if len(result) > 500:
                print(f"  └─ Result: {result[:500]}...\n")
            else:
                print(f"  └─ Result: {result}\n")

        elif etype == "done":
            if self._streaming_text:
                print("\n")
                self._streaming_text = False
            print("\n✅ Done\n")

        elif etype == "error":
            if self._streaming_text:
                print("\n")
                self._streaming_text = False
            print(f"❌ Error: {event.get('message', 'unknown')}\n")

    async def interactive_loop(self):
        """Interactive chat loop."""
        await self.connect()
        
        try:
            while self.running:
                try:
                    user_input = input("You: ").strip()
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ("/quit", "/exit"):
                        break
                    
                    await self.send_message(user_input)
                    await self.receive_events()
                
                except KeyboardInterrupt:
                    break
        finally:
            if self.ws:
                await self.ws.close()
            print("\nGoodbye! 🥔")

    async def chat(self, message: str) -> str:
        """Single message → response (non-interactive)."""
        await self.connect()
        await self.send_message(message)
        
        response_text = ""
        try:
            while True:
                raw = await self.ws.recv()
                event = json.loads(raw)
                
                if event.get("type") == "text_delta":
                    response_text += event.get("text", "")
                
                if event.get("type") in ("done", "error", "cancelled"):
                    break
        finally:
            if self.ws:
                await self.ws.close()
        
        return response_text


async def main():
    parser = argparse.ArgumentParser(description="PixelPotato Network Client")
    parser.add_argument("--host", default="localhost", help="Agent server host")
    parser.add_argument("--port", type=int, default=8000, help="Agent server port")
    parser.add_argument("--message", help="Single message mode (non-interactive)")
    parser.add_argument("--secure", action="store_true", help="Use WSS (secure WebSocket)")
    
    args = parser.parse_args()
    
    scheme = "wss" if args.secure else "ws"
    client = NetworkClient(args.host, args.port, scheme=scheme)
    
    if args.message:
        # Single message mode
        response = await client.chat(args.message)
        print(response)
    else:
        # Interactive mode
        await client.interactive_loop()


if __name__ == "__main__":
    asyncio.run(main())
