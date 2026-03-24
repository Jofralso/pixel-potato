"""
Web-based client – serves a streaming chat UI for PixelPotato 🥔.
Handles text_delta, tool_call, tool_result, status, done, error events.
"""

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
  body { font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace; background: #0d1117; color: #c9d1d9; height: 100vh; display: flex; flex-direction: column; }
  #header { padding: 10px 20px; background: #161b22; border-bottom: 1px solid #30363d; display: flex; align-items: center; justify-content: space-between; }
  #header h1 { font-size: 15px; color: #58a6ff; }
  #header .status { font-size: 12px; color: #484f58; }
  #messages { flex: 1; overflow-y: auto; padding: 16px 20px; }
  .msg { margin-bottom: 12px; max-width: 90%; }
  .msg.user { margin-left: auto; }
  .msg.user .bubble { background: #1f6feb33; border: 1px solid #1f6feb55; border-radius: 12px 12px 0 12px; padding: 10px 14px; }
  .msg.agent .bubble { background: #161b22; border: 1px solid #30363d; border-radius: 12px 12px 12px 0; padding: 10px 14px; white-space: pre-wrap; word-break: break-word; }
  .msg.tool .bubble { background: #0d1117; border-left: 3px solid #d29922; padding: 6px 12px; font-size: 12px; border-radius: 4px; color: #8b949e; }
  .msg.status .bubble { background: transparent; color: #484f58; font-size: 12px; padding: 2px 0; }
  .msg.plan { max-width: 95%; }
  .plan-bubble { background: #161b22; border: 1px solid #8b5cf6; border-radius: 8px; padding: 12px 16px; }
  .plan-title { font-weight: 600; color: #c4b5fd; font-size: 14px; margin-bottom: 4px; }
  .plan-progress { font-size: 11px; color: #484f58; margin-bottom: 8px; }
  .plan-steps { display: flex; flex-direction: column; gap: 3px; }
  .plan-step { font-size: 13px; padding: 2px 0; }
  .msg .label { font-size: 11px; color: #484f58; margin-bottom: 3px; }
  pre { white-space: pre-wrap; word-break: break-word; margin: 0; font-family: inherit; }
  code { background: #1c2128; padding: 1px 4px; border-radius: 3px; font-size: 13px; }
  #input-area { display: flex; padding: 12px 20px; background: #161b22; border-top: 1px solid #30363d; gap: 10px; }
  #user-input { flex: 1; background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 10px 14px; border-radius: 8px; font-family: inherit; font-size: 14px; outline: none; resize: none; min-height: 42px; max-height: 200px; }
  #user-input:focus { border-color: #58a6ff; }
  #send-btn { background: #238636; color: #fff; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; }
  #send-btn:hover { background: #2ea043; }
  #send-btn:disabled { opacity: 0.3; cursor: default; }
  .spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid #484f58; border-top-color: #58a6ff; border-radius: 50%; animation: spin 0.8s linear infinite; margin-left: 6px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div id="header">
  <h1>&#x1F954; PixelPotato</h1>
  <div class="status" id="status">Connecting...</div>
</div>
<div id="messages" id="messages"></div>
<div id="input-area">
  <textarea id="user-input" placeholder="Ask the potato anything..." rows="1"></textarea>
  <button id="send-btn" onclick="send()">Send</button>
</div>
<script>
const messages = document.getElementById('messages');
const input = document.getElementById('user-input');
const btn = document.getElementById('send-btn');
const statusEl = document.getElementById('status');
let ws;
let busy = false;
let currentAgentBubble = null; // Active streaming bubble

function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws');
  ws.onopen = () => statusEl.textContent = 'Connected';
  ws.onmessage = (e) => handleEvent(JSON.parse(e.data));
  ws.onclose = () => {
    statusEl.textContent = 'Disconnected — reconnecting...';
    currentAgentBubble = null;
    setTimeout(connect, 2000);
  };
}

function handleEvent(ev) {
  switch(ev.type) {
    case 'session_start':
      statusEl.textContent = 'Session: ' + ev.session_id.slice(0, 8);
      break;

    case 'text_delta':
      // Stream tokens into current agent bubble
      if (!currentAgentBubble) {
        currentAgentBubble = addMsg('agent', '', true);
      }
      currentAgentBubble.querySelector('pre').textContent += ev.content;
      scrollDown();
      break;

    case 'text':
      // Full text (fallback)
      if (currentAgentBubble) {
        currentAgentBubble.querySelector('pre').textContent += ev.content;
      } else {
        addMsg('agent', ev.content);
      }
      currentAgentBubble = null;
      break;

    case 'status':
      addMsg('status', ev.message + (ev.round ? ' [round ' + ev.round + ']' : ''));
      break;

    case 'thinking':
      addMsg('status', '💭 ' + (ev.content || '').slice(0, 150));
      break;

    case 'plan':
      currentAgentBubble = null;
      renderPlan(ev.plan);
      break;

    case 'tool_call':
      currentAgentBubble = null;
      // Hide internal tools from verbose display
      if (['think', 'plan', 'memory'].includes(ev.tool)) break;
      const argStr = JSON.stringify(ev.arguments, null, 2);
      const truncated = argStr.length > 300 ? argStr.slice(0, 300) + '...' : argStr;
      addMsg('tool', '▶ ' + ev.tool + '\\n' + truncated);
      break;

    case 'tool_result':
      if (['think', 'plan', 'memory'].includes(ev.tool)) break;
      const result = ev.result || '';
      const lines = result.split('\\n');
      const preview = lines.slice(0, 10).join('\\n') + (lines.length > 10 ? '\\n... (' + (lines.length - 10) + ' more lines)' : '');
      addMsg('tool', '✓ ' + (ev.tool ? ev.tool + ': ' : '') + preview);
      break;

    case 'done':
      currentAgentBubble = null;
      busy = false;
      btn.disabled = false;
      statusEl.innerHTML = statusEl.textContent.replace(/<span.*<\\/span>/, '');
      break;

    case 'error':
      currentAgentBubble = null;
      addMsg('agent', '⚠ ' + ev.message);
      busy = false;
      btn.disabled = false;
      break;

    case 'cancelled':
      currentAgentBubble = null;
      addMsg('status', 'Cancelled');
      busy = false;
      btn.disabled = false;
      break;
  }
}

function addMsg(role, text, returnEl) {
  const d = document.createElement('div');
  d.className = 'msg ' + role;
  if (role !== 'status') {
    const label = document.createElement('div');
    label.className = 'label';
    label.textContent = role === 'user' ? 'You' : role === 'agent' ? '🥔 Potato' : 'Tool';
    d.appendChild(label);
  }
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  const pre = document.createElement('pre');
  pre.textContent = text;
  bubble.appendChild(pre);
  d.appendChild(bubble);
  messages.appendChild(d);
  scrollDown();
  if (returnEl) return d;
}

function renderPlan(plan) {
  // Remove previous plan display if exists
  const prev = document.getElementById('plan-display');
  if (prev) prev.remove();

  const d = document.createElement('div');
  d.id = 'plan-display';
  d.className = 'msg plan';
  const statusIcons = { 'pending': '○', 'in-progress': '◐', 'done': '●', 'skipped': '⊘' };
  const statusColors = { 'pending': '#484f58', 'in-progress': '#d29922', 'done': '#3fb950', 'skipped': '#484f58' };

  let html = '<div class=\"bubble plan-bubble\"><div class=\"plan-title\">📋 ' + (plan.title || 'Plan') + '</div>';
  const steps = plan.steps || [];
  const done = steps.filter(s => s.status === 'done').length;
  html += '<div class=\"plan-progress\">' + done + '/' + steps.length + ' complete</div>';
  html += '<div class=\"plan-steps\">';
  for (const s of steps) {
    const icon = statusIcons[s.status] || '○';
    const color = statusColors[s.status] || '#484f58';
    html += '<div class=\"plan-step\" style=\"color:' + color + '\">' + icon + ' ' + (s.title || '?') + '</div>';
  }
  html += '</div></div>';
  d.innerHTML = html;
  messages.appendChild(d);
  scrollDown();
}

function scrollDown() {
  messages.scrollTop = messages.scrollHeight;
}

function send() {
  const text = input.value.trim();
  if (!text || busy) return;
  addMsg('user', text);
  ws.send(JSON.stringify({ type: 'chat', message: text }));
  input.value = '';
  input.style.height = 'auto';
  busy = true;
  btn.disabled = true;
  statusEl.innerHTML += '<span class="spinner"></span>';
  currentAgentBubble = null;
}

// Auto-resize textarea
input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 200) + 'px';
});

// Enter to send, Shift+Enter for newline
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});

connect();
</script>
</body>
</html>"""


@web_app.get("/")
async def index():
    return HTMLResponse(HTML_PAGE)
