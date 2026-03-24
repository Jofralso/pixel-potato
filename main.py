"""
Application entry point — runs the FastAPI server with the web UI mounted.
"""

import uvicorn
from agent.server import app
from clients.web import web_app
from config.settings import settings

# Mount web client at root
app.mount("/ui", web_app)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )
