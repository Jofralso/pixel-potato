"""
PixelPotato 🥔 — Main server with WebSocket support.
A suspiciously productive couch potato. Supports 2 concurrent sessions.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
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


app = FastAPI(title="PixelPotato 🥔", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


HTML_UI = """<!DOCTYPE html>
<html><head><title>PixelPotato 🥔</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Courier New',monospace;background:#0d1117;color:#f0f0f0;height:100vh;display:flex;flex-direction:column;line-height:1.5}
#header{padding:10px;background:#161b22;border-bottom:1px solid #30363d;display:flex;align-items:center;justify-content:space-between}
#header h1{font-size:14px;color:#58a6ff}
#status{font-size:11px;color:#f0f0f0}
#messages{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px}
.msg{padding:8px 10px;border-radius:6px;max-width:90%;word-wrap:break-word;white-space:pre-wrap}
.user{background:#1f6feb33;margin-left:auto;color:#f0f0f0}
.agent{background:#161b22;border:1px solid #30363d;color:#f0f0f0}
.code-block{background:#0d1117;border:1px solid #30363d;padding:10px;border-radius:4px;overflow-x:auto;color:#f0f0f0;margin:4px 0}
.code-lang{font-size:10px;color:#8b949e;margin-bottom:4px}
#footer{display:flex;gap:8px;padding:10px;background:#161b22;border-top:1px solid #30363d}
textarea{flex:1;background:#0d1117;border:1px solid #30363d;color:#f0f0f0;padding:8px;border-radius:4px;font-family:'Courier New',monospace;resize:none}
button{background:#238636;color:#fff;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;font-weight:bold}
button:disabled{background:#30363d;cursor:not-allowed}
.connected #status::before{content:'🟢 ';color:#10b981}
.disconnected #status::before{content:'🔴 '}
</style>
</head><body>
<div id=\"header\"><h1>🥔 PixelPotato</h1><div id=\"status\">Connecting...</div></div>
<div id=\"messages\"></div>
<div id=\"footer\">
<textarea id=\"msg\" placeholder=\"Your message...\" rows=\"2\" disabled></textarea>
<button id=\"send\" onclick=\"send()\" disabled>↳</button>
</div>
<script>
let ws;
let connected = false;
let currentBuffer = '';
const msgs = document.getElementById('messages');
const input = document.getElementById('msg');
const send_btn = document.getElementById('send');
const status = document.getElementById('status');
const header = document.getElementById('header');

function parseAndRenderContent(text) {
  const container = document.createElement('div');
  const codeBlockRegex = /```(\\w*)\\n([\\s\\S]*?)```/g;
  const lines = text.split('\\n');
  let inCodeBlock = false;
  let blockLang = '';
  let blockContent = '';
  
  let lastIndex = 0;
  let match;
  const regex = /```(\\w*)\\n([\\s\\S]*?)```/g;
  
  const matches = Array.from(text.matchAll(regex));
  
  if(matches.length === 0){
    container.textContent = text;
  } else {
    let pos = 0;
    matches.forEach(m => {
      if(pos < m.index){
        const el = document.createElement('span');
        el.textContent = text.substring(pos, m.index);
        container.appendChild(el);
      }
      
      const lang = m[1] || 'text';
      const code = m[2];
      const codeDiv = document.createElement('div');
      codeDiv.className = 'code-block';
      
      const langSpan = document.createElement('div');
      langSpan.className = 'code-lang';
      langSpan.textContent = lang;
      codeDiv.appendChild(langSpan);
      
      const codePre = document.createElement('pre');
      codePre.style.margin = '0';
      codePre.style.color = '#f0f0f0';
      codePre.textContent = code;
      codeDiv.appendChild(codePre);
      
      container.appendChild(codeDiv);
      pos = m.index + m[0].length;
    });
    
    if(pos < text.length){
      const el = document.createElement('span');
      el.textContent = text.substring(pos);
      container.appendChild(el);
    }
  }
  
  return container;
}

function connect(){
  try {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = proto + '//' + location.host + '/ws';
    console.log('Connecting to:', url);
    ws = new WebSocket(url);
    
    ws.onopen = () => {
      console.log('Connected');
      connected = true;
      input.disabled = false;
      send_btn.disabled = false;
      status.textContent = 'Connected';
      header.classList.remove('disconnected');
      header.classList.add('connected');
    };
    
    ws.onmessage = (e) => {
      console.log('Message:', e.data);
      const d = JSON.parse(e.data);
      
      if(d.type === 'text_delta'){
        currentBuffer += (d.text || d.content || '');
        let last = msgs.lastChild;
        if(!last || !last.classList.contains('agent')){
          last = document.createElement('div');
          last.classList.add('msg', 'agent');
          msgs.appendChild(last);
        }
        last.innerHTML = '';
        last.appendChild(parseAndRenderContent(currentBuffer));
      } else if(d.type === 'status' || d.type === 'tool_call_start' || d.type === 'tool_call_result'){
        currentBuffer = '';
        const status_msg = document.createElement('div');
        status_msg.classList.add('msg', 'agent');
        status_msg.style.fontSize = '12px';
        status_msg.style.color = '#8b949e';
        status_msg.style.opacity = '0.9';
        status_msg.textContent = d.message || (d.tool_name ? '🔧 ' + d.tool_name : JSON.stringify(d));
        msgs.appendChild(status_msg);
      } else if(d.type === 'done'){
        currentBuffer = '';
        const done_msg = document.createElement('div');
        done_msg.classList.add('msg', 'agent');
        done_msg.style.fontSize = '11px';
        done_msg.style.color = '#a0a0a0';
        done_msg.textContent = '✓ Done';
        msgs.appendChild(done_msg);
        send_btn.disabled = false;
        input.disabled = false;
      } else if(d.type === 'error'){
        currentBuffer = '';
        const err_msg = document.createElement('div');
        err_msg.classList.add('msg', 'agent');
        err_msg.style.borderLeft = '3px solid #da3633';
        err_msg.style.color = '#f0f0f0';
        err_msg.textContent = '❌ ' + (d.message || 'Error');
        msgs.appendChild(err_msg);
        send_btn.disabled = false;
        input.disabled = false;
      }
      
      msgs.scrollTop = msgs.scrollHeight;
    };
    
    ws.onerror = (e) => {
      console.error('WebSocket error:', e);
      status.textContent = 'Connection error';
      header.classList.remove('connected');
      header.classList.add('disconnected');
    };
    
    ws.onclose = () => {
      console.log('Disconnected');
      connected = false;
      input.disabled = true;
      send_btn.disabled = true;
      status.textContent = 'Disconnected';
      header.classList.remove('connected');
      header.classList.add('disconnected');
    };
  } catch(err) {
    console.error('Connection error:', err);
    status.textContent = 'Error: ' + err.message;
  }
}

function send(){
  const text = input.value.trim();
  if(!text || !ws || !connected) {
    console.log('Cannot send:', {text, ws: !!ws, connected});
    return;
  }
  console.log('Sending:', text);
  const div = document.createElement('div');
  div.classList.add('msg', 'user');
  div.textContent = text;
  msgs.appendChild(div);
  ws.send(JSON.stringify({type:'chat',message:text}));
  input.value = '';
  input.focus();
  send_btn.disabled = true;
  input.disabled = true;
  msgs.scrollTop = msgs.scrollHeight;
}

input.addEventListener('keypress', e => {
  if(e.key === 'Enter' && !e.shiftKey) { send(); e.preventDefault(); }
});

console.log('Initializing PixelPotato client...');
header.classList.add('disconnected');
connect();
</script>
</body></html>"""

@app.get("/")
@app.get("/ui")
async def ui():
    return HTMLResponse(HTML_UI)


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

                session.add_user(user_message)

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
