DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Bridge Dashboard</title>
<style>
  :root {
    --bg: #0d1117;
    --bg2: #161b22;
    --bg3: #21262d;
    --border: #30363d;
    --text: #c9d1d9;
    --text-dim: #8b949e;
    --text-bright: #f0f6fc;
    --blue: #388bfd;
    --blue-dim: #1f3d6e;
    --green: #3fb950;
    --green-dim: #1a3d26;
    --yellow: #d29922;
    --yellow-dim: #3d2c00;
    --red: #f85149;
    --red-dim: #3d1a19;
    --purple: #bc8cff;
    --purple-dim: #2e1f5e;
    --gray: #6e7681;
    --radius: 6px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: grid;
    grid-template-rows: 56px 1fr 64px;
    grid-template-columns: 1fr;
    overflow: hidden;
  }

  /* ── Header ── */
  header {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 20px;
    gap: 12px;
    position: relative;
  }
  header h1 {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-bright);
    letter-spacing: 0.5px;
  }
  .logo { font-size: 20px; }
  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 6px var(--green);
    animation: pulse 2s ease-in-out infinite;
    flex-shrink: 0;
  }
  .status-dot.disconnected { background: var(--red); box-shadow: 0 0 6px var(--red); }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  .header-status {
    font-size: 12px;
    color: var(--text-dim);
  }
  .header-right {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .agent-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid var(--border);
  }
  .agent-pill.copilot { background: var(--blue-dim); color: var(--blue); border-color: var(--blue-dim); }
  .agent-pill.gemini  { background: var(--green-dim); color: var(--green); border-color: var(--green-dim); }
  .agent-pill .agent-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

  /* ── Main layout ── */
  main {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
    overflow: hidden;
    min-height: 0;
  }

  /* ── Panels ── */
  .panel {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
  }
  .panel:first-child { border-right: 1px solid var(--border); }

  .panel-header {
    padding: 12px 16px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  .panel-header h2 {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-bright);
    text-transform: uppercase;
    letter-spacing: 0.8px;
  }
  .badge {
    font-size: 11px;
    padding: 1px 7px;
    border-radius: 20px;
    background: var(--bg3);
    color: var(--text-dim);
    border: 1px solid var(--border);
  }

  /* ── Feed ── */
  #feed {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
    scroll-behavior: smooth;
    min-height: 0;
  }
  #feed::-webkit-scrollbar { width: 6px; }
  #feed::-webkit-scrollbar-track { background: transparent; }
  #feed::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

  .msg-item {
    padding: 8px 16px;
    border-bottom: 1px solid transparent;
    transition: background 0.1s;
    animation: slideIn 0.2s ease-out;
  }
  .msg-item:hover { background: var(--bg2); }
  @keyframes slideIn {
    from { opacity: 0; transform: translateY(-4px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .msg-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }
  .sender-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .sender-badge.copilot { background: var(--blue-dim); color: var(--blue); }
  .sender-badge.gemini  { background: var(--green-dim); color: var(--green); }
  .sender-badge.system  { background: var(--bg3); color: var(--gray); }
  .channel-tag {
    font-size: 11px;
    color: var(--purple);
    font-weight: 500;
  }
  .msg-time {
    font-size: 11px;
    color: var(--text-dim);
    margin-left: auto;
  }
  .msg-content {
    font-size: 13px;
    color: var(--text);
    line-height: 1.5;
    word-break: break-word;
  }

  /* ── Task Board ── */
  #taskboard {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  #taskboard::-webkit-scrollbar { width: 6px; }
  #taskboard::-webkit-scrollbar-track { background: transparent; }
  #taskboard::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

  .kanban-cols {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .kanban-col {}
  .col-header {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    padding: 6px 10px;
    border-radius: var(--radius) var(--radius) 0 0;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .col-header.pending    { background: var(--bg3); color: var(--text-dim); }
  .col-header.in_progress{ background: var(--blue-dim); color: var(--blue); }
  .col-header.done       { background: var(--green-dim); color: var(--green); }
  .col-header.failed     { background: var(--red-dim); color: var(--red); }
  .col-count {
    background: rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 1px 6px;
    font-size: 10px;
    margin-left: auto;
  }

  .task-cards { display: flex; flex-direction: column; gap: 6px; }
  .task-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 12px;
    transition: border-color 0.15s, transform 0.1s;
    animation: slideIn 0.2s ease-out;
  }
  .task-card:hover {
    border-color: var(--blue);
    transform: translateY(-1px);
  }
  .task-card-header {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    margin-bottom: 5px;
  }
  .task-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-bright);
    flex: 1;
    line-height: 1.4;
  }
  .priority-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
    flex-shrink: 0;
  }
  .priority-badge.p0 { background: var(--bg3); color: var(--gray); }
  .priority-badge.p1 { background: var(--yellow-dim); color: var(--yellow); }
  .priority-badge.phigh { background: var(--red-dim); color: var(--red); }
  .task-desc {
    font-size: 11px;
    color: var(--text-dim);
    line-height: 1.4;
    margin-bottom: 6px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .task-footer {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 10px;
    color: var(--text-dim);
  }
  .task-id { font-family: monospace; color: var(--purple); }
  .task-agent {
    padding: 1px 5px;
    border-radius: 3px;
    font-weight: 600;
    font-size: 10px;
  }
  .task-agent.copilot { background: var(--blue-dim); color: var(--blue); }
  .task-agent.gemini  { background: var(--green-dim); color: var(--green); }

  /* ── Bottom bar ── */
  footer {
    background: var(--bg2);
    border-top: 1px solid var(--border);
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  select, input[type="text"] {
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: var(--radius);
    padding: 6px 10px;
    font-size: 13px;
    outline: none;
    transition: border-color 0.15s;
  }
  select:focus, input[type="text"]:focus { border-color: var(--blue); }
  select { cursor: pointer; }
  #msg-input { flex: 1; }
  #msg-input::placeholder { color: var(--text-dim); }
  button {
    background: var(--blue);
    color: #fff;
    border: none;
    border-radius: var(--radius);
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s;
  }
  button:hover { background: #58a6ff; transform: translateY(-1px); }
  button:active { transform: translateY(0); }
  button:disabled { background: var(--bg3); color: var(--text-dim); cursor: not-allowed; transform: none; }

  .empty-state {
    text-align: center;
    padding: 24px 12px;
    color: var(--text-dim);
    font-size: 12px;
  }
  .empty-icon { font-size: 24px; margin-bottom: 6px; }
</style>
</head>
<body>

<header>
  <span class="logo">🌉</span>
  <h1>AI Bridge</h1>
  <div class="status-dot" id="status-dot"></div>
  <span class="header-status" id="conn-status">Connecting...</span>
  <div class="header-right">
    <div id="agents-panel" style="display:flex;gap:8px;"></div>
    <div id="uptime-badge" class="badge">--</div>
  </div>
</header>

<main>
  <!-- LEFT: Live Feed -->
  <div class="panel">
    <div class="panel-header">
      <h2>📡 Live Feed</h2>
      <span class="badge" id="msg-count">0</span>
    </div>
    <div id="feed"></div>
  </div>

  <!-- RIGHT: Task Board -->
  <div class="panel">
    <div class="panel-header">
      <h2>📋 Task Board</h2>
      <span class="badge" id="task-count">0</span>
    </div>
    <div id="taskboard">
      <div class="kanban-cols">
        <div class="kanban-col">
          <div class="col-header pending">⏳ Pending <span class="col-count" id="cnt-pending">0</span></div>
          <div class="task-cards" id="col-pending"></div>
        </div>
        <div class="kanban-col">
          <div class="col-header in_progress">⚡ In Progress <span class="col-count" id="cnt-in_progress">0</span></div>
          <div class="task-cards" id="col-in_progress"></div>
        </div>
        <div class="kanban-col">
          <div class="col-header done">✅ Done <span class="col-count" id="cnt-done">0</span></div>
          <div class="task-cards" id="col-done"></div>
        </div>
        <div class="kanban-col">
          <div class="col-header failed">❌ Failed <span class="col-count" id="cnt-failed">0</span></div>
          <div class="task-cards" id="col-failed"></div>
        </div>
      </div>
    </div>
  </div>
</main>

<footer>
  <select id="sender-sel">
    <option value="copilot">🤖 Copilot</option>
    <option value="gemini">✨ Gemini</option>
    <option value="system">⚙️ System</option>
  </select>
  <select id="channel-sel">
    <option value="broadcast">broadcast</option>
    <option value="copilot">copilot</option>
    <option value="gemini">gemini</option>
    <option value="system">system</option>
  </select>
  <input type="text" id="msg-input" placeholder="Send a message to the bridge..." autocomplete="off" />
  <button id="send-btn" onclick="sendMessage()">Send</button>
</footer>

<script>
const SERVER = window.location.origin;
let ws = null;
let reconnectTimer = null;
let msgCount = 0;
let taskCount = 0;
let allTasks = {};
let agentActivity = {};  // agent -> last seen timestamp

function timeAgo(ts) {
  const diff = (Date.now() / 1000) - ts;
  if (diff < 5)   return 'just now';
  if (diff < 60)  return Math.floor(diff) + 's ago';
  if (diff < 3600) return Math.floor(diff/60) + 'm ago';
  if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
  return Math.floor(diff/86400) + 'd ago';
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function priorityBadge(p) {
  if (p === 0) return `<span class="priority-badge p0">P${p}</span>`;
  if (p <= 1)  return `<span class="priority-badge p1">P${p}</span>`;
  return `<span class="priority-badge phigh">P${p}</span>`;
}

function agentBadge(name) {
  if (!name) return '';
  const cls = ['copilot','gemini'].includes(name) ? name : '';
  return `<span class="task-agent ${cls}">${escapeHtml(name)}</span>`;
}

function renderMessage(msg) {
  const senderCls = ['copilot','gemini'].includes(msg.sender) ? msg.sender : 'system';
  return `
    <div class="msg-item">
      <div class="msg-meta">
        <span class="sender-badge ${senderCls}">${escapeHtml(msg.sender)}</span>
        <span class="channel-tag">#${escapeHtml(msg.channel)}</span>
        <span class="msg-time" data-ts="${msg.timestamp}">${timeAgo(msg.timestamp)}</span>
      </div>
      <div class="msg-content">${escapeHtml(msg.content)}</div>
    </div>`;
}

function renderTaskCard(task) {
  const assignee = task.assigned_to ? `→ ${agentBadge(task.assigned_to)}` : '';
  return `
    <div class="task-card" data-id="${task.id}">
      <div class="task-card-header">
        <span class="task-title">${escapeHtml(task.title)}</span>
        ${priorityBadge(task.priority)}
      </div>
      <div class="task-desc">${escapeHtml(task.description)}</div>
      <div class="task-footer">
        <span class="task-id">#${task.id}</span>
        ${agentBadge(task.created_by)}
        ${assignee}
      </div>
    </div>`;
}

function rebuildBoard() {
  const cols = { pending: [], in_progress: [], done: [], failed: [] };
  for (const t of Object.values(allTasks)) {
    if (cols[t.status] !== undefined) cols[t.status].push(t);
  }
  for (const [status, tasks] of Object.entries(cols)) {
    const el = document.getElementById('col-' + status);
    const cnt = document.getElementById('cnt-' + status);
    if (tasks.length === 0) {
      el.innerHTML = '<div class="empty-state"><div class="empty-icon">—</div>No tasks</div>';
    } else {
      // sort by priority desc then created_at asc
      tasks.sort((a,b) => b.priority - a.priority || a.created_at - b.created_at);
      el.innerHTML = tasks.map(renderTaskCard).join('');
    }
    cnt.textContent = tasks.length;
  }
  taskCount = Object.keys(allTasks).length;
  document.getElementById('task-count').textContent = taskCount;
}

function addMessage(msg) {
  agentActivity[msg.sender] = Date.now() / 1000;
  const feed = document.getElementById('feed');
  const atBottom = feed.scrollHeight - feed.clientHeight - feed.scrollTop < 80;
  feed.insertAdjacentHTML('beforeend', renderMessage(msg));
  msgCount++;
  document.getElementById('msg-count').textContent = msgCount;
  if (atBottom) feed.scrollTop = feed.scrollHeight;
  // prune old messages in DOM (keep last 200)
  const items = feed.querySelectorAll('.msg-item');
  if (items.length > 200) {
    for (let i = 0; i < items.length - 200; i++) items[i].remove();
  }
}

function loadHistory(messages) {
  const feed = document.getElementById('feed');
  feed.innerHTML = '';
  msgCount = messages.length;
  document.getElementById('msg-count').textContent = msgCount;
  for (const msg of messages) {
    feed.insertAdjacentHTML('beforeend', renderMessage(msg));
    agentActivity[msg.sender] = Math.max(agentActivity[msg.sender] || 0, msg.timestamp);
  }
  feed.scrollTop = feed.scrollHeight;
}

function updateAgentsPanel() {
  const panel = document.getElementById('agents-panel');
  const now = Date.now() / 1000;
  const agents = ['copilot', 'gemini'];
  panel.innerHTML = agents.map(a => {
    const lastSeen = agentActivity[a];
    const active = lastSeen && (now - lastSeen) < 60;
    return `<div class="agent-pill ${a}">
      <span class="agent-dot" style="opacity:${active ? 1 : 0.3}"></span>
      ${a} ${active ? '' : '<span style="opacity:0.5;font-weight:400">idle</span>'}
    </div>`;
  }).join('');
}

async function fetchTasks() {
  try {
    const res = await fetch(SERVER + '/tasks');
    if (res.ok) {
      const tasks = await res.json();
      allTasks = {};
      for (const t of tasks) allTasks[t.id] = t;
      rebuildBoard();
    }
  } catch(e) {}
}

async function fetchStatus() {
  try {
    const res = await fetch(SERVER + '/status');
    if (res.ok) {
      const s = await res.json();
      const up = s.uptime;
      let upStr;
      if (up < 60) upStr = Math.floor(up) + 's';
      else if (up < 3600) upStr = Math.floor(up/60) + 'm';
      else upStr = Math.floor(up/3600) + 'h ' + Math.floor((up%3600)/60) + 'm';
      document.getElementById('uptime-badge').textContent = '↑ ' + upStr;
    }
  } catch(e) {}
}

function connectWebSocket() {
  if (ws) { try { ws.close(); } catch(e) {} }
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws/all`);

  ws.onopen = () => {
    clearTimeout(reconnectTimer);
    document.getElementById('status-dot').className = 'status-dot';
    document.getElementById('conn-status').textContent = 'Connected';
  };

  ws.onmessage = (evt) => {
    try {
      const pkt = JSON.parse(evt.data);
      if (pkt.type === 'history') {
        loadHistory(pkt.messages);
      } else if (pkt.type === 'message') {
        addMessage(pkt.data);
        updateAgentsPanel();
      } else if (pkt.type === 'task_update') {
        allTasks[pkt.data.id] = pkt.data;
        rebuildBoard();
      }
    } catch(e) {}
  };

  ws.onclose = () => {
    document.getElementById('status-dot').className = 'status-dot disconnected';
    document.getElementById('conn-status').textContent = 'Disconnected – reconnecting…';
    reconnectTimer = setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = () => ws.close();
}

async function sendMessage() {
  const sender  = document.getElementById('sender-sel').value;
  const channel = document.getElementById('channel-sel').value;
  const content = document.getElementById('msg-input').value.trim();
  if (!content) return;
  const btn = document.getElementById('send-btn');
  btn.disabled = true;
  try {
    await fetch(SERVER + '/messages', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ sender, channel, content })
    });
    document.getElementById('msg-input').value = '';
  } catch(e) {
    alert('Failed to send: ' + e);
  }
  btn.disabled = false;
}

document.getElementById('msg-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

// Refresh timestamps every 15s
setInterval(() => {
  document.querySelectorAll('.msg-time[data-ts]').forEach(el => {
    el.textContent = timeAgo(parseFloat(el.dataset.ts));
  });
  updateAgentsPanel();
}, 15000);

// Refresh status every 30s, tasks every 10s
setInterval(fetchStatus, 30000);
setInterval(fetchTasks, 10000);

// Init
connectWebSocket();
fetchTasks();
fetchStatus();
updateAgentsPanel();
</script>
</body>
</html>"""


def get_dashboard() -> str:
    return DASHBOARD_HTML
