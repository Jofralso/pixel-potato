# ── Agent server ──────────────────────
FROM python:3.12-slim AS agent

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl nodejs npm grep \
    && rm -rf /var/lib/apt/lists/*

# Install MCP filesystem server globally (most common MCP server)
RUN npm install -g @modelcontextprotocol/server-filesystem

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default workspace mount point
RUN mkdir -p /workspace

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV WORKSPACE_DIR=/workspace

CMD ["python", "main.py"]
