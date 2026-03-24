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

### Using OpenAI or Anthropic instead of Ollama

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-your-key-here
```

```env
LLM_PROVIDER=anthropic
LLM_BASE_URL=https://api.anthropic.com
LLM_MODEL=claude-sonnet-4-20250514
LLM_API_KEY=sk-ant-your-key-here
```

When using a cloud provider you can skip the Ollama service:
```bash
docker compose up agent -d
```

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
│   ├── cli.py             # Terminal CLI client
│   └── web.py             # Browser-based chat UI
├── config/
│   ├── settings.py        # Environment-based config
│   └── mcp_servers.json   # MCP server definitions
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

No GPU? No problem. Remove the `deploy.resources` section from the `ollama` service in `docker-compose.yml` and use a smaller model:

```env
LLM_MODEL=qwen2.5-coder:7b
```

The potato will be a bit slower but still gets the job done. Like a baked potato vs. a fried one — different vibes, same delicious result.

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
