"""
Web-based client – serves a minimal chat UI for browser access.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

web_app = FastAPI()

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PixelPotato 🥔</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'SF Mono', 'Fira Code', monospace; background: #1a1a2e; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }
  #header { padding: 12px 20px; background: #16213e; border-bottom: 1px solid #0f3460; }
  #header h1 { font-size: 16px; color: #00d4ff; }
  #header .status { font-size: 12px; color: #666; }
  #messages { flex: 1; overflow-y: auto; padding: 20px; }
  .msg { margin-bottom: 16px; max-width: 85%; }
  .msg.user { margin-left: auto; }
  .msg.user .bubble { background: #0f3460; border-radius: 12px 12px 0 12px; padding: 10px 14px; }
  .msg.agent .bubble { background: #1a1a2e; border: 1px solid #333; border-radius: 12px 12px 12px 0; padding: 10px 14px; }
  .msg.tool .bubble { background: #0d1117; border-left: 3px solid #f0c040; padding: 8px 12px; font-size: 13px; border-radius: 4px; }
  .msg .label { font-size: 11px; color: #666; margin-bottom: 4px; }
  pre { white-space: pre-wrap; word-break: break-word; }
  #input-area { display: flex; padding: 12px 20px; background: #16213e; border-top: 1px solid #0f3460; gap: 10px; }
  #user-input { flex: 1; background: #1a1a2e; border: 1px solid #333; color: #e0e0e0; padding: 10px 14px; border-radius: 8px; font-family: inherit; font-size: 14px; outline: none; }
  #user-input:focus { border-color: #00d4ff; }
  #send-btn { background: #00d4ff; color: #000; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; }
  #send-btn:disabled { opacity: 0.4; cursor: default; }
</style>
</head>
<body>
<div id="header">
  <h1>&#x1F954; PixelPotato</h1>
  <div class="status" id="status">Connecting...</div>
</div>
<div id="messages"></div>
<div id="input-area">
  <input id="user-input" placeholder="Hey potato, help me with..." autocomplete="off" />
  <button id="send-btn" onclick="send()">Send</button>
</div>
<script>
const messages = document.getElementById('messages');
const input = document.getElementById('user-input');
const btn = document.getElementById('send-btn');
const status = document.getElementById('status');
let ws;
let busy = false;

function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws');

  ws.onopen = () => status.textContent = 'Connected';

  ws.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    handleEvent(ev);
  };

  ws.onclose = () => {
    status.textContent = 'Disconnected — refreshing...';
    setTimeout(connect, 2000);
  };
}

function handleEvent(ev) {
  if (ev.type === 'session_start') {
    status.textContent = 'Connected — Session: ' + ev.session_id.slice(0, 8);
  } else if (ev.type === 'text') {
    addMsg('agent', ev.content);
  } else if (ev.type === 'tool_call') {
    addMsg('tool', '▶ ' + ev.tool + '\\n' + JSON.stringify(ev.arguments, null, 2));
  } else if (ev.type === 'tool_result') {
    addMsg('tool', '✓ ' + ev.result);
  } else if (ev.type === 'done' || ev.type === 'error' || ev.type === 'cancelled') {
    busy = false;
    btn.disabled = false;
    if (ev.type === 'error') addMsg('agent', '⚠ Error: ' + ev.message);
  }
}

function addMsg(role, text) {
  const d = document.createElement('div');
  d.className = 'msg ' + role;
  const label = document.createElement('div');
  label.className = 'label';
  label.textContent = role === 'user' ? 'You' : role === 'agent' ? '🥔 Potato' : 'Tool';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  const pre = document.createElement('pre');
  pre.textContent = text;
  bubble.appendChild(pre);
  d.appendChild(label);
  d.appendChild(bubble);
  messages.appendChild(d);
  messages.scrollTop = messages.scrollHeight;
}

function send() {
  const text = input.value.trim();
  if (!text || busy) return;
  addMsg('user', text);
  ws.send(JSON.stringify({ type: 'chat', message: text }));
  input.value = '';
  busy = true;
  btn.disabled = true;
}

input.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
connect();
</script>
</body>
</html>"""


@web_app.get("/")
async def index():
    return HTMLResponse(HTML_PAGE)
