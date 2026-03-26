# Claude Code Integration Guide 🥔

Connect Claude Code (Anthropic's Claude in VS Code) to PixelPotato for local AI development.

## Overview

**What:** Claude Code (VS Code extension) running locally on your machine, communicating with PixelPotato on the same network or Docker setup.

**Why:** 
- Use Claude 3.5 Sonnet (the best AI for coding) to control your machine
- Your code stays local, only instructions go to Anthropic
- PixelPotato provides tool execution (file ops, shell commands, MCP servers)

```
┌──────────────────────┐        ┌──────────────────────┐
│  VS Code + Claude    │        │  PixelPotato Server  │
│  Code Extension      │───────→│  (Same machine or    │
│  (Anthropic API)     │        │   same network)      │
└──────────────────────┘        └──────────────────────┘
       Your Laptop                  8000:8000
```

---

## Quick Start

### 1️⃣ Install Claude Code in VS Code

```bash
# VS Code Extensions marketplace
# Search: "Claude Code"
# By: Anthropic
```

Or install via CLI:
```bash
code --install-extension Anthropic.claude-dev
```

### 2️⃣ Get Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create API key
3. Paste in Claude Code settings

### 3️⃣ Install PixelPotato Network Client

For macOS, Windows, or Linux specific setup, see [CLIENT_SETUP.md](CLIENT_SETUP.md)

**Quick macOS example:**
```bash
git clone https://github.com/Jofralso/pixel-potato.git
cd pixel-potato
python3 -m venv venv
source venv/bin/activate
pip install websockets
```

### 4️⃣ Create `.claude_dev/instructions.md` in your project

```markdown
# PixelPotato Integration Instructions

You have access to PixelPotato, a local AI agent that can:
- Read/write files
- Run shell commands
- Search code
- Execute MCP servers

To use PixelPotato:
1. Open VS Code terminal
2. Run: `python clients/network_client.py --host localhost --port 8000`
3. Ask the potato to help with tasks

PixelPotato can handle complex file manipulations and command execution.
Use it for heavy lifting, while you focus on high-level direction.
```

### 4️⃣ Start PixelPotato

```bash
# Option A: Local Ollama
cd pixel-potato
docker compose up

# Option B: Remote Claude (no GPU needed)
LLM_PROVIDER=anthropic \
LLM_BASE_URL=https://api.anthropic.com \
LLM_MODEL=claude-3-5-sonnet-20241022 \
LLM_API_KEY=sk-ant-xxxxx \
docker compose up agent -d
```

### 5️⃣ Use in Claude Code

Within Claude Code, you can now tell it:

> "I need to debug a Python issue. Let me ask PixelPotato for help with the file operations."

Then in your VS Code terminal:
```bash
python clients/network_client.py --host localhost --port 8000

You: Read my config file and suggest improvements
🥔 [reads file]...
You: /quit
```

---

## Integration Patterns

### Pattern 1: Direct Terminal Usage

Claude Code opens VS Code terminal → You run the network client → Chat with both simultaneously.

```bash
# Terminal 1: Claude Code (your AI assistant)
# (VS Code running Anthropic's Claude)

# Terminal 2: PixelPotato (local execution)
$ python clients/network_client.py --host localhost --port 8000
You: Review the project structure and suggest optimizations
🥔 [analyzes files]...

# Copy potato's suggestions back to Claude Code for implementation
```

### Pattern 2: Programmatic Integration

Create a Claude Code tool that calls PixelPotato:

```python
# .vscode/claude_potato.py
import asyncio
import json
from clients.network_client import NetworkClient

class PotatoTool:
    """Integration layer between Claude Code and PixelPotato."""
    
    async def ask(self, question: str) -> str:
        """Ask PixelPotato a question."""
        client = NetworkClient("localhost", 8000)
        return await client.chat(question)
    
    async def run_command(self, cmd: str) -> str:
        """Run a shell command via PixelPotato."""
        return await self.ask(f"Run this command: {cmd}")

# From Claude Code:
# potato = PotatoTool()
# result = asyncio.run(potato.ask("Find all Python files with syntax errors"))
```

### Pattern 3: Hybrid AI

Use Claude Code for coding logic + PixelPotato for execution:

**Claude Code (in your head/VS Code):**
> "I want to refactor all TypeScript imports in this project"

**You type in PixelPotato terminal:**
```
You: Find all .ts files and show me the current imports
🥔 [searches]...
```

**Claude Code generates:**
```typescript
// Refactored imports
import { foo } from '@lib/index'
```

**You tell PixelPotato:**
```
You: Replace all imports matching the pattern shown with the new format
🥔 [applies changes]...
```

---

## Configuration

### Local Setup (Recommended for Learning)

```bash
# Terminal 1: Start PixelPotato with local model
cd pixel-potato
docker compose up
# Ollama pulls model, agent starts on 8000

# Terminal 2: Open VS Code and enable Claude Code
code .

# Terminal 3: Run network client when needed
python clients/network_client.py --host localhost --port 8000
```

### Remote Setup (Production)

```bash
# Server: Start PixelPotato with Claude backend (no GPU needed)
LLM_PROVIDER=anthropic \
LLM_API_KEY=sk-ant-xxxxx \
docker compose up agent -d

# Your machine: Use Claude Code + connect to server
# In VS Code terminal:
python clients/network_client.py --host <server-ip> --port 8000
```

### Docker Network Setup

For multiple developers:

```yaml
# docker-compose.yml
version: '3.9'
services:
  agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MAX_CLIENTS=10  # More concurrent users
    networks:
      - shared_network

networks:
  shared_network:
    driver: bridge
```

Then all developers can connect:
```bash
python clients/network_client.py --host pixel-potato-agent --port 8000
```

---

## Real-World Workflow Example

### Scenario: Code Review + Refactor

**Goal:** Review code quality and make improvements.

**Step 1: Claude Code Analysis**
```
Claude Code: "I'll help you review your codebase for improvements."
(Claude analyzes open files in VS Code)
```

**Step 2: PixelPotato Deep Dive**
```bash
$ python clients/network_client.py --host localhost

You: Analyze my entire project structure for code duplication
🥔 Searching through 45 files...
🥔 Found 7 instances of duplicated utility functions in:
   - src/utils/string.ts (lines 12-28)
   - src/helpers/text.ts (lines 5-21)
   - ...

You: Create a refactored version consolidating these into one module
🥔 [generates consolidated utils module]...

You: Show me the diff for implementing this change
🥔 [streams diff output]...

You: /quit
```

**Step 3: Claude Code Implementation**
```
Claude Code: "I see the consolidation. Let me update the imports across the codebase..."
(Claude generates proper import statements and refactoring)
```

---

## Tips & Best Practices

1. **Keep terminals organized:**
   - Terminal 1: PixelPotato CLI
   - Terminal 2: General shell
   - VS Code sidebar: Claude Code chat

2. **Use for different strengths:**
   - **Claude Code (Anthropic):** Coding logic, architecture, patterns
   - **PixelPotato (local):** File manipulation, complex searches, batch operations

3. **Leverage MCP servers:**
   Configure GitHub, filesystem, and other MCPs in PixelPotato for maximum power.

4. **Context management:**
   Ask PixelPotato to summarize large files before showing Claude Code:
   ```bash
   You: Summarize the main.py file in 100 words focusing on the architecture
   🥔 [produces summary for Claude Code context]...
   ```

---

## Troubleshooting

### Claude Code won't connect to VS Code terminal

Make sure Claude Code extension is installed and your API key is set correctly.

### Network client can't reach PixelPotato

```bash
# Check if PixelPotato is running
curl http://localhost:8000/health

# Check firewall
sudo ufw allow 8000

# Try explicit localhost
python clients/network_client.py --host 127.0.0.1 --port 8000
```

### "Max clients reached" error

PixelPotato defaults to 2 concurrent clients. Configure more:

```env
MAX_CLIENTS=5
```

Then restart:
```bash
docker compose up -d agent
```

---

## Advanced: Custom Tool Integration

Make PixelPotato accessible as a Claude Code "tool":

```javascript
// .vscode/potato.js
const WebSocket = require('ws');

class PotatoClient {
  async chat(message) {
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'chat', message }));
    };
    
    return new Promise((resolve) => {
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'done') {
          resolve(msg.response);
          ws.close();
        }
      };
    });
  }
}

module.exports = { PotatoClient };
```

---

## See Also

- [MULTI_USER.md](MULTI_USER.md) — Network client setup
- [README.md](../README.md) — Main documentation  
- [Anthropic Claude Docs](https://docs.anthropic.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
