# Multi-User Setup Guide 🥔

Connect multiple users/clients to the same PixelPotato agent over a network. Perfect for teams or remote development.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│             Server Machine (Your Setup)              │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │     PixelPotato Agent (Docker)               │   │
│  │     Port 8000                                │   │
│  │     Max 2 concurrent clients                 │   │
│  │     (supports CLI, Web UI, RPC clients)      │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  IP: 192.168.1.100 (example)                       │
└─────────────────────────────────────────────────────┘
        ▲              ▲              ▲
        │              │              │
    ┌───┴──┐      ┌────┴────┐   ┌────┴──────┐
    │      │      │         │   │           │
┌───▼──┐ ┌─┴──┐ ┌─┴──────┐ │ ┌──┴──┐   ┌──┴────┐
│User1 │ │U2  │ │User 3  │ │ │Dev4 │   │Claude│
│(CLI) │ │Web │ │(RPC)   │ │ │Team │   │Code  │
└──────┘ └────┘ └────────┘ │ └─────┘   └──────┘
                            └── "Max 2 connected"
```

## Setup Steps

### 1️⃣ Server Side — Expose PixelPotato on Network

The agent is already accessible on the network! Just note the server's IP:

```bash
# Find server IP
hostname -I
# Output: 192.168.1.100 (example)
```

**Docker Container:** Accessible internally at `pixel-potato-agent:8000`  
**Host Network:** Accessible at `<your-ip>:8000` (e.g., `192.168.1.100:8000`)

### 2️⃣ Client Side — Connect Using Python RPC Client

**On another machine (same network):**

**For detailed OS-specific setup (macOS, Windows, Linux) see [CLIENT_SETUP.md](CLIENT_SETUP.md)**

Quick version:
```bash
# Get the network client script
git clone https://github.com/Jofralso/pixel-potato.git
cd pixel-potato

# Install dependencies
pip install websockets

# Connect to server
python clients/network_client.py --host 192.168.1.100 --port 8000
```

Replace `192.168.1.100` with your server's actual IP.

**Interactive example:**
```bash
$ python clients/network_client.py --host 192.168.1.100

🥔 Connecting to 192.168.1.100:8000...
✅ Connected! Session: a1b2c3d4
Type messages. Press Ctrl+C to exit.

You: Write a Python function to reverse a string
🥔 Here's a simple Python function...
[response streams back]

You: /quit
```

**Single-message mode:**
```bash
python clients/network_client.py \
  --host 192.168.1.100 \
  --message "What's 2+2?"
```

### 3️⃣ Docker Network Access

If both are in the same Docker network:

```bash
# From another container
python clients/network_client.py --host pixel-potato-agent --port 8000
```

---

## Claude Code (VS Code) Integration

### Option A: Use Python Client in Terminal

```bash
# Install the network client locally
pip install websockets

# Terminal within VS Code
python clients/network_client.py --host <server-ip> --port 8000
```

Then interact with Claude Code's terminal integration:
1. Open VS Code terminal
2. Run the network client
3. Chat with the potato directly from terminal

### Option B: Custom RPC Wrapper (for direct Claude Code integration)

Create a simple wrapper that Claude Code can call as a tool:

```python
# tools/claude_rpc.py
import asyncio
import json
from clients.network_client import NetworkClient

async def ask_potato(question: str, server_host: str = "localhost") -> str:
    """Call PixelPotato remotely and get response."""
    client = NetworkClient(server_host, 8000)
    response = await client.chat(question)
    return response

# Usage from Claude Code:
# result = ask_potato("Write Python code to read a CSV file", server_host="192.168.1.100")
```

---

## Connection Methods

| Method | Command | Best For |
|--------|---------|----------|
| **Python CLI** | `python clients/network_client.py --host <ip>` | Local development |
| **Web Browser** | `http://<server-ip>:8000/ui` | Designer/non-technical users |
| **Docker container** | `network_client.py --host pixel-potato-agent` | Multi-container setups |
| **RPC/Programmatic** | Python `NetworkClient` class | Automation, tool integration |

---

## Network Configuration

### Same Local Network (LAN)

```bash
# Find your server IP
ifconfig | grep "inet "  # Linux/Mac
ipconfig               # Windows WSL

# Use that IP from any machine on the network
python clients/network_client.py --host 192.168.1.100
```

### Docker Compose Network

If running multiple services in docker-compose:

```yaml
# docker-compose.yml
services:
  agent:
    ports:
      - "8000:8000"
    networks:
      - potato_net
  
  other_service:
    networks:
      - potato_net
    environment:
      - POTATO_URL=ws://pixel-potato-agent:8000/ws

networks:
  potato_net:
    driver: bridge
```

Then from other_service:
```python
# Access via container hostname
client = NetworkClient("pixel-potato-agent", 8000)
```

### Remote Network (via SSH tunnel)

If server is on a different network:

```bash
# Create SSH tunnel
ssh -L 8000:localhost:8000 user@server-ip

# Then connect locally
python clients/network_client.py --host localhost --port 8000
```

---

## Troubleshooting

### "Connection refused"
```bash
# Check if agent is running
docker compose ps

# Check port is exposed
netstat -tlnp | grep 8000  # Linux
lsof -i :8000              # Mac

# Check firewall
sudo ufw allow 8000  # Ubuntu
```

### "Max clients reached"
The potato only supports 2 concurrent clients. Wait for one to disconnect:
```bash
# Check active sessions
curl http://<server-ip>:8000/health | jq .active_sessions
```

### "Host not reachable"
```bash
# Verify connectivity
ping 192.168.1.100

# Check if port is listening
telnet 192.168.1.100 8000

# Test WebSocket connection
python -c "import websockets; asyncio.run(websockets.connect('ws://192.168.1.100:8000/ws'))"
```

---

## Security Notes

⚠️ **Current setup:**
- CORS is enabled (`allow_origins=["*"]`)
- No authentication required
- Anyone on the network can access

🔒 **For production, consider:**
- Adding API key authentication
- Using WSS (WebSocket Secure) with SSL certificates
- Firewall rules to restrict access
- Network segmentation

---

## API Protocol (Raw WebSocket)

For custom integrations:

```python
import json
import websockets

async def custom_client():
    async with websockets.connect("ws://192.168.1.100:8000/ws") as ws:
        # Receive session start
        msg = await ws.recv()
        print(json.loads(msg))  # {"type": "session_start", "session_id": "..."}
        
        # Send message
        await ws.send(json.dumps({
            "type": "chat",
            "message": "Hello potato!"
        }))
        
        # Receive events
        while True:
            event = json.loads(await ws.recv())
            print(event)
            
            # Stop on terminal event
            if event["type"] in ("done", "error", "cancelled"):
                break
```

**Event types:**
- `text_delta` — LLM token ✊
- `tool_call_start/end` — Tool execution
- `tool_call_result` — Tool output
- `done` — Conversation complete
- `error` — Error occurred
- `cancelled` — User cancelled

---

## Example: Multi-User Team Setup

**Server machine (192.168.1.100):**
```bash
docker compose up
# MAX_CLIENTS=2 allows 2 users at once
```

**User 1 (Designer):**
```bash
# Opens web UI in browser
open http://192.168.1.100:8000/ui
```

**User 2 (Developer, VS Code terminal):**
```bash
python clients/network_client.py --host 192.168.1.100

# Interactive coding session
You: Help me debug this error...
🥔 I see the issue. Let me check the logs...
```

**User 3 (arrives while users 1-2 are connected):**
```bash
python clients/network_client.py --host 192.168.1.100
# ❌ "Max clients (2) reached. Try again later."
# 👉 Waits for user 1 or 2 to disconnect
```

---

## See Also

- [README.md](../README.md) — Main documentation
- [clients/cli.py](cli.py) — Local CLI client
- [clients/web.py](web.py) — Web UI
- [agent/server.py](../agent/server.py) — Server implementation
