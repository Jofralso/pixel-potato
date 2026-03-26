# 🥔 PixelPotato

**A suspiciously productive couch potato that codes, designs, and handles your UI needs.**

Self-hosted AI agent for your home setup — dev, Figma-to-code, UI/UX, and whatever else you throw at it. Runs locally with Ollama or connects to cloud LLMs. Supports MCP servers, 2 simultaneous clients, and deploys with a single Docker command.

> *"I may look like a potato, but I pixel-push harder than your entire design team."* — PixelPotato

## Features

- 🧠 **Agentic tool loop** — LLM ↔ tool execution cycle (read, write, edit, search, shell, MCP)
- 🔌 **MCP server support** — Plug in any [Model Context Protocol](https://modelcontextprotocol.io/) server
- 👥 **2 concurrent clients** — Two people can talk to the potato at the same time
- 🏠 **Fully local option** — Ollama by default, your data never leaves home
- ☁️ **Cloud LLMs too** — OpenAI or Anthropic if the potato needs a bigger brain
- 🖥️ **CLI + Web UI** — Terminal for devs, browser for designers
- 🐳 **One command deploy** — `docker compose up` and the potato is baked and ready

## Architecture

```
┌──────────────────────────────────────────────────┐
│              Docker Compose (The Oven)            │
│                                                   │
│  ┌───────────┐    ┌────────────────────────────┐ │
│  │  Ollama   │◀──▶│    🥔 PixelPotato Server    │ │
│  │  (Brain)  │    │  ┌──────────┐ ┌──────────┐ │ │
│  └───────────┘    │  │ Session  │ │  Tools   │ │ │
│                   │  │ Manager  │ │ (built-in│ │ │
│  ┌───────────┐    │  │ (max: 2) │ │  + MCP)  │ │ │
│  │   MCP     │◀──▶│  └──────────┘ └──────────┘ │ │
│  │  Servers  │    │  ┌──────────────────────┐  │ │
│  └───────────┘    │  │  WebSocket Endpoint   │  │ │
│                   │  └──────────┬───────────┘  │ │
│                   └─────────────┼──────────────┘ │
└─────────────────────────────────┼────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                ┌───▼───┐   ┌───▼───┐   ┌────▼────┐
                │  CLI  │   │ Web UI│   │ Custom  │
                │  🖥️   │   │  🌐   │   │  🔧    │
                └───────┘   └───────┘   └─────────┘
```

## Quick Start

### 1. Clone & configure

```bash
git clone git@github.com:Jofralso/pixel-potato.git
cd pixel-potato
cp .env.example .env
# Edit .env to your needs
```

### 2. Launch with Docker Compose

```bash
docker compose up -d
```

This will:
- Start **Ollama** with GPU support (the potato needs its brain)
- Auto-pull the configured model (default: `qwen2.5-coder:14b`)
- Start **PixelPotato** on port 8000

### 3. Talk to the Potato

**Web UI** — Open [http://localhost:8000/ui](http://localhost:8000/ui) 🌐

**CLI (for terminal enjoyers):**
```bash
pip install websockets
python clients/cli.py
# or specify a custom URL:
python clients/cli.py ws://localhost:8000/ws
```

**Health check (is the potato alive?):**
```bash
curl http://localhost:8000/health
```

## Configuration

### LLM Provider Options

**PixelPotato supports 3 LLM backends:**

#### 1. 🏠 **Ollama (Local + Free)** — Default

Runs entirely on your machine. No API fees, no data leaves home.

```bash
# Default setup—already configured!
docker compose up
```

**Pros:** Free, private, fast, offline  
**Cons:** Needs GPU for good performance, uses local compute  
**Models:** qwen2.5-coder (14b/7b), llama2, mistral, etc.

---

#### 2. 🧠 **Claude (Anthropic) — Most Capable**

Uses Claude 3.5 Sonnet, the most powerful AI for coding tasks.

```env
LLM_PROVIDER=anthropic
LLM_BASE_URL=https://api.anthropic.com
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_API_KEY=sk-ant-your-api-key-here
```

Get your API key from [console.anthropic.com](https://console.anthropic.com)

**Pros:** Most intelligent, handles complex code tasks, works on CPU  
**Cons:** Costs money (~$0.003 per 1K input tokens, $0.015 per 1K output tokens)  
**Best for:** Production work, complex projects

---

#### 3. 🤖 **OpenAI (GPT) — Alternative Cloud**

Use GPT-4o or GPT-4 Turbo from OpenAI.

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-your-openai-key
```

Get your API key from [platform.openai.com](https://platform.openai.com/api-keys)

**Pros:** Capable, large ecosystem  
**Cons:** Costs money, less specialized for building  
**Best for:** General-purpose AI tasks

---

### Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama`, `openai`, or `anthropic` |
| `LLM_BASE_URL` | `http://ollama:11434` | LLM API endpoint |
| `LLM_MODEL` | `qwen2.5-coder:14b` | Model name |
| `LLM_API_KEY` | _(empty)_ | API key (OpenAI/Anthropic only) |
| `PORT` | `8000` | Agent server port |
| `MAX_CLIENTS` | `2` | Max concurrent WebSocket sessions |
| `WORKSPACE_PATH` | `./../workspace` | Host path mounted as `/workspace` |

### Quick Switch: Ollama → Anthropic

1. Get your API key: [console.anthropic.com](https://console.anthropic.com)
2. Update `.env`:
```bash
LLM_PROVIDER=anthropic
LLM_BASE_URL=https://api.anthropic.com
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_API_KEY=sk-ant-xxxxx
```
3. **Skip Ollama (saves resources!):**
```bash
docker compose up agent -d
```

That's it! No GPU needed. The potato now uses Claude locally.

---

### Estimated Costs (Claude)

Using Claude Sonnet 3.5 for a typical coding session:

| Task | Tokens | Cost |
|------|--------|------|
| Small bugfix (5 exchanges) | ~50K | ~$0.10 |
| Medium feature (10 exchanges) | ~100K | ~$0.20 |
| Large project (20 exchanges) | ~200K | ~$0.40 |

**Free tier:** $5/month of API credits (usually covers light usage)  
**Details:** [Anthropic pricing](https://www.anthropic.com/pricing)

---

## Comparison: Local vs Cloud

| Feature | Ollama Local | Claude (Anthropic) | GPT (OpenAI) |
|---------|--------------|-------------------|--------------|
| **Cost** | Free ✅ | ~$0.003-0.02/1K tokens | ~$0.015-0.20/1K tokens |
| **Speed** | Fast (local) | Fast (API) | Fast (API) |
| **Privacy** | 100% local ✅ | Sent to Anthropic | Sent to OpenAI |
| **Intelligence** | Very good | Best (3.5 Sonnet) | Good (GPT-4o) |
| **GPU needed** | Yes (16GB+) | No | No |
| **Works offline** | Yes ✅ | No (needs internet) | No (needs internet) |
| **Setup time** | ~10-20 min | ~2 min | ~2 min |
| **Coding ability** | Excellent | Excellent (best) | Very good |

**For home projects:** Start with Ollama (free, local).  
**For professional work:** Switch to Claude (best quality, reasonable cost).

---

## MCP Servers

MCP servers are configured in `config/mcp_servers.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
      "env": {}
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token"
      }
    }
  }
}
```

Any MCP-compatible server that uses **stdio transport** will work. The agent discovers tools at startup and makes them available to the LLM.

**Available MCP servers:** [https://github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)

## Built-in Tools

The potato comes loaded with these out of the box:

| Tool | Description |
|---|---|
| `read_file` | Read file contents (with optional line range) |
| `write_file` | Create or overwrite files |
| `edit_file` | Find-and-replace within a file |
| `list_directory` | List directory contents |
| `search_files` | Grep search across files |
| `run_command` | Execute shell commands |
| `glob_search` | Find files by glob pattern |

## Multi-Client Support

The potato can talk to **2 people at the same time** (configurable via `MAX_CLIENTS`). Each client gets an independent session with its own conversation history. If a third person tries to connect, the potato politely tells them to wait.

## Multi-User & Remote Access

**Another user on your network wants to use the potato?**

```bash
# On another machine (same network)
python clients/network_client.py --host 192.168.1.100 --port 8000
```

📖 **[Client Setup Guide](docs/CLIENT_SETUP.md)** — OS-specific instructions for macOS, Windows, Linux (VSCode, terminal, virtual environments)

📖 **[Multi-User Setup Guide](docs/MULTI_USER.md)** — Detailed setup for teams, Docker networks, SSH tunnels, and RPC integration.

🧠 **[Claude Code Integration](docs/CLAUDE_CODE.md)** — Use Anthropic's Claude 3.5 Sonnet in VS Code with PixelPotato for execution.

## Project Structure

```
pixel-potato/
├── agent/
│   ├── server.py          # FastAPI + WebSocket server
│   ├── orchestrator.py    # Agent loop (LLM ↔ tools)
│   ├── session.py         # Session management
│   └── llm.py             # Multi-provider LLM client
├── mcp/
│   ├── registry.py        # MCP server lifecycle manager
│   └── client.py          # MCP stdio protocol client
├── tools/
│   └── builtin.py         # Built-in file/shell tools
├── clients/
│   ├── cli.py             # Local terminal CLI client
│   ├── network_client.py  # Remote RPC client (same network)
│   └── web.py             # Browser-based chat UI
├── docs/
│   ├── MULTI_USER.md      # Multi-user & network setup guide
│   └── CLAUDE_CODE.md     # Claude Code (VS Code) integration
├── config/
│   ├── settings.py        # Environment-based config
│   └── mcp_servers.json   # MCP server definitions
├── scripts/
│   └── init-ollama.sh     # Ollama model bootstrap
├── main.py                # Wake the potato
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Development

Run locally without Docker:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start Ollama separately
ollama serve &
ollama pull qwen2.5-coder:14b

# Set env for local dev
export LLM_BASE_URL=http://localhost:11434
export WORKSPACE_DIR=$PWD
export MCP_CONFIG_PATH=$PWD/config/mcp_servers.json

python main.py
```

## Without GPU (Potato on a Budget)

### Option 1: Smaller Ollama Model (Still Free, Still Local)

No GPU? Use a smaller quantized model. Still runs, just a bit slower:

```env
LLM_MODEL=qwen2.5-coder:7b
```

This fits easily on CPU. Like a baked potato vs. a fried one — different vibes, same delicious result.

### Option 2: Use Claude Instead (No GPU Needed)

Skip GPU entirely and fly to the cloud:

```env
LLM_PROVIDER=anthropic
LLM_BASE_URL=https://api.anthropic.com
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_API_KEY=sk-ant-xxxxx
```

Then start without Ollama:
```bash
docker compose up agent -d
```

**Best approach:** Use Claude for coding work (super smart) and save GPU for other tasks.

## What Can the Potato Do?

- 💻 **Dev** — Write code, debug, refactor, run tests, git operations
- 🎨 **Figma/UI** — Translate designs to code, review UI components, generate CSS/Tailwind
- 📁 **File ops** — Read, write, search, edit any file in your workspace
- 🔧 **Shell** — Run any command, install packages, build projects
- 🔌 **MCP servers** — Extend with GitHub, databases, APIs, whatever you need
- 🏠 **Fully local** — Your code stays on your machine. The potato doesn't gossip.

## License

MIT

---

*Made with 🥔 by [Jofralso](https://github.com/Jofralso)*
