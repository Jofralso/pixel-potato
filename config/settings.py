"""
Settings loaded from environment variables and .env file.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    # LLM config
    llm_provider: str = "ollama"          # ollama | openai | anthropic
    llm_base_url: str = "http://ollama:11434"
    llm_model: str = "qwen2.5-coder:14b"
    llm_api_key: str = ""

    # Server config
    host: str = "0.0.0.0"
    port: int = 8000
    max_clients: int = 2

    # MCP config
    mcp_config_path: str = "/app/config/mcp_servers.json"

    # Workspace
    workspace_dir: str = "/workspace"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
            llm_base_url=os.getenv("LLM_BASE_URL", "http://ollama:11434"),
            llm_model=os.getenv("LLM_MODEL", "qwen2.5-coder:14b"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            max_clients=int(os.getenv("MAX_CLIENTS", "2")),
            mcp_config_path=os.getenv("MCP_CONFIG_PATH", "/app/config/mcp_servers.json"),
            workspace_dir=os.getenv("WORKSPACE_DIR", "/workspace"),
        )


settings = Settings.from_env()
