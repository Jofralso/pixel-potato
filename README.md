# Local AI Agent

A self-hosted AI coding agent that works like Claude Code — with tool use, MCP server support, and multi-client WebSocket connections. Fully containerized with Docker for one-command deployment.

## Features

- **Claude Code-like agent loop** — LLM ↔ tool execution cycle with file ops, shell commands, and search
- **MCP server support** — Connect any [Model Context Protocol](https://modelcontextprotocol.io/) server
- **2 concurrent clients** — WebSocket-based sessions, configurable limit
- **Multi-LLM backend** — Ollama (default, fully local), OpenAI, or Anthropic
- **CLI + Web UI** — Terminal client and browser-based chat interface
- **One-command deploy** — `docker compose up` pulls model + starts everything

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  Docker Compose                   │
│                                                   │
│  ┌───────────┐    ┌────────────────────────────┐ │
│  │  Ollama   │◀──▶│      Agent Server           │ │
│  │  (LLM)    │    │  ┌──────────┐ ┌──────────┐ │ │
│  └───────────┘    │  │ Session  │ │  Tools   │ │ │
│                   │  │ Manager  │ │ (built-in│ │ │
│  ┌───────────┐    │  │ (max: 2) │ │  + MCP)  │ │ │
│  │  MCP      │◀──▶│  └──────────┘ └──────────┘ │ │
│  │  Servers   │    │  ┌──────────────────────┐  │ │
│  └───────────┘    │  │  WebSocket Endpoint   │  │ │
│                   │  └──────────┬───────────┘  │ │
│                   └─────────────┼──────────────┘ │
└─────────────────────────────────┼────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                ┌───▼───┐   ┌───▼───┐   ┌────▼────┐
                │  CLI  │   │ Web UI│   │ Custom  │
                │Client │   │Client │   │ Client  │
                └───────┘   └───────┘   └─────────┘
```

## Quick Start

### 1. Clone & configure

```bash
git clone git@github.com:Jofralso/local-ai-agent.git
cd local-ai-agent
cp .env.example .env
# Edit .env to your needs
```

### 2. Launch with Docker Compose

```bash
docker compose up -d
```

This will:
- Start **Ollama** with GPU support
- Auto-pull the configured model (default: `qwen2.5-coder:14b`)
- Start the **Agent server** on port 8000

### 3. Connect

**Web UI** — Open [http://localhost:8000/ui](http://localhost:8000/ui)

**CLI client:**
```bash
pip install websockets
python clients/cli.py
# or specify a custom URL:
python clients/cli.py ws://localhost:8000/ws
```

**Health check:**
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

The agent comes with core tools out of the box:

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

The server accepts up to **2 concurrent WebSocket connections** (configurable via `MAX_CLIENTS`). Each client gets an independent session with its own conversation history. Excess connections are rejected with an error message.

## Project Structure

```
local-ai-agent/
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
├── main.py                # Entry point
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

## Without GPU

If you don't have a GPU, remove the `deploy.resources` section from the `ollama` service in `docker-compose.yml` and use a smaller model:

```env
LLM_MODEL=qwen2.5-coder:7b
```

## License

MIT
