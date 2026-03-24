# ── PixelPotato 🥔 Agent Server ──────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ripgrep tree nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Install common MCP servers globally
RUN npm install -g @modelcontextprotocol/server-filesystem

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /workspace

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV WORKSPACE_DIR=/workspace

CMD ["python", "main.py"]
