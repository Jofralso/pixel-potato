"""
Main FastAPI server with WebSocket support for multi-client AI agent.
Supports up to 2 concurrent client sessions.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agent.session import SessionManager
from agent.orchestrator import AgentOrchestrator
from mcp.registry import MCPRegistry
from config.settings import settings


session_manager = SessionManager(max_sessions=settings.max_clients)
mcp_registry = MCPRegistry()
orchestrator: AgentOrchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    await mcp_registry.load_from_config(settings.mcp_config_path)
    orchestrator = AgentOrchestrator(mcp_registry=mcp_registry, settings=settings)
    yield
    await mcp_registry.shutdown_all()


app = FastAPI(title="Local AI Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_sessions": session_manager.active_count,
        "max_sessions": settings.max_clients,
        "mcp_servers": list(mcp_registry.servers.keys()),
    }


@app.get("/mcp/servers")
async def list_mcp_servers():
    return {
        name: {
            "status": srv.status,
            "tools": [t.model_dump() for t in srv.tools],
        }
        for name, srv in mcp_registry.servers.items()
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = str(uuid.uuid4())

    if not session_manager.can_accept():
        await ws.send_json({
            "type": "error",
            "message": f"Max clients ({settings.max_clients}) reached. Try again later.",
        })
        await ws.close()
        return

    session = session_manager.create_session(session_id)
    await ws.send_json({"type": "session_start", "session_id": session_id})

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "chat":
                user_message = data.get("message", "")
                if not user_message:
                    continue

                session.add_message("user", user_message)

                async for event in orchestrator.run(session):
                    await ws.send_json(event)

            elif msg_type == "cancel":
                session.cancel_current()
                await ws.send_json({"type": "cancelled"})

            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        session_manager.remove_session(session_id)
