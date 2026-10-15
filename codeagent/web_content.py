# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

# Remote 模式的 Web 前端 HTML（DSH 风格现代 GUI）。

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeAgent</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg: #0f1115;
  --bg-sidebar: #15181e;
  --bg-surface: #1a1e26;
  --bg-hover: #21262f;
  --bg-input: #1a1e26;
  --text: #dfe3ea;
  --text-dim: #7d8590;
  --text-bright: #f2f4f8;
  --accent: #8b7cf6;
  --accent-hover: #9d90f8;
  --accent-soft: rgba(139,124,246,0.12);
  --green: #4ade80;
  --red: #f87171;
  --yellow: #fbbf24;
  --blue: #6ea8fe;
  --border: #262c36;
  --code-bg: #12151b;
  --radius: 12px;
  --shadow: 0 4px 16px rgba(0,0,0,0.35);
}

html, body {
  height: 100%; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-size: 14.5px; -webkit-font-smoothing: antialiased;
}

#app { display: flex; height: 100vh; overflow: hidden; }

/* ══════════ 左侧边栏 ══════════ */
#sidebar {
  width: 264px; flex-shrink: 0; background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column; overflow: hidden;
}
.sidebar-logo {
  padding: 20px 20px 16px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px;
}
.sidebar-logo .logo-icon {
  width: 34px; height: 34px; border-radius: 9px;
  background: linear-gradient(135deg, #8b7cf6, #6ea8fe);
  display: flex; align-items: center; justify-content: center;
  font-size: 17px; box-shadow: 0 2px 8px rgba(139,124,246,0.35);
}
.sidebar-logo .logo-name { font-size: 16px; font-weight: 700; color: var(--text-bright); letter-spacing: 0.2px; }
.sidebar-logo .logo-sub { font-size: 11px; color: var(--text-dim); margin-top: 1px; }

.sidebar-section { padding: 14px 16px 6px; }
.sidebar-section-title {
  font-size: 10.5px; font-weight: 700; letter-spacing: 1.2px;
  color: var(--text-dim); text-transform: uppercase; margin-bottom: 8px; padding: 0 4px;
}
.sidebar-card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 10px 12px; font-size: 12.5px;
}
.sidebar-card .row { display: flex; justify-content: space-between; gap: 8px; padding: 3px 0; }
.sidebar-card .k { color: var(--text-dim); flex-shrink: 0; }
.sidebar-card .v {
  color: var(--text); font-family: "SF Mono", "Fira Code", Consolas, monospace;
  font-size: 11.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

#command-list { flex: 1; overflow-y: auto; padding: 0 16px 16px; }
#command-list::-webkit-scrollbar { width: 4px; }
#command-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
.cmd-item {
  padding: 7px 10px; border-radius: 8px; cursor: pointer;
  display: flex; flex-direction: column; gap: 1px; transition: background 0.15s;
}
.cmd-item:hover { background: var(--bg-hover); }
.cmd-item .cmd-name { color: var(--accent); font-weight: 600; font-size: 12.5px; font-family: "SF Mono", Consolas, monospace; }
.cmd-item .cmd-desc { color: var(--text-dim); font-size: 11.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ══════════ 右侧主区 ══════════ */
#main { flex: 1; display: flex; flex-direction: column; min-width: 0; }

#topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 24px; border-bottom: 1px solid var(--border);
  font-size: 12.5px; color: var(--text-dim); flex-shrink: 0;
  background: rgba(15,17,21,0.85); backdrop-filter: blur(8px);
}
#topbar .crumb { color: var(--text-dim); }
#topbar .crumb b { color: var(--text); font-weight: 600; }
#topbar .info { display: flex; gap: 18px; align-items: center; }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; }
.dot.connected { background: var(--green); box-shadow: 0 0 6px rgba(74,222,128,0.6); }
.dot.disconnected { background: var(--red); }
#conn-status { display: flex; align-items: center; }
#token-info { font-family: "SF Mono", Consolas, monospace; font-size: 11.5px; }

/* 消息流 */
#messages {
  flex: 1; overflow-y: auto; padding: 28px 24px 16px;
  scroll-behavior: smooth;
}
#messages::-webkit-scrollbar { width: 8px; }
#messages::-webkit-scrollbar-track { background: transparent; }
#messages::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
#messages::-webkit-scrollbar-thumb:hover { background: #333a46; }

.msg-column { max-width: 820px; margin: 0 auto; }

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.msg { margin-bottom: 20px; line-height: 1.7; animation: fadeUp 0.25s ease; }

/* 用户气泡（右侧） */
.msg-user { display: flex; justify-content: flex-end; }
.msg-user .bubble {
  max-width: 75%; background: linear-gradient(135deg, #7c6af0, #6857e0);
  color: #fff; padding: 10px 16px; border-radius: 16px 16px 4px 16px;
  white-space: pre-wrap; word-break: break-word; box-shadow: 0 2px 10px rgba(124,106,240,0.25);
}

/* 助手消息（左侧，带头像） */
.msg-assistant { display: flex; gap: 12px; }
.msg-assistant .avatar {
  width: 30px; height: 30px; border-radius: 8px; flex-shrink: 0; margin-top: 2px;
  background: linear-gradient(135deg, #8b7cf6, #6ea8fe);
  display: flex; align-items: center; justify-content: center; font-size: 14px;
}
.msg-assistant .content { flex: 1; min-width: 0; color: var(--text); padding-top: 3px; }
.msg-assistant .content p { margin-bottom: 10px; }
.msg-assistant .content p:last-child { margin-bottom: 0; }
.msg-assistant .content code {
  background: var(--code-bg); padding: 2px 7px; border-radius: 5px;
  font-size: 13px; font-family: "SF Mono", "Fira Code", Consolas, monospace;
  color: #e6b673; border: 1px solid var(--border);
}
.msg-assistant .content pre {
  background: var(--code-bg); padding: 14px 16px; border-radius: 10px;
  margin: 10px 0; overflow-x: auto; border: 1px solid var(--border);
}
.msg-assistant .content pre code { background: none; padding: 0; border: none; color: var(--text); }
.msg-assistant .content ul, .msg-assistant .content ol { padding-left: 22px; margin: 8px 0; }
.msg-assistant .content li { margin: 4px 0; }
.msg-assistant .content h1, .msg-assistant .content h2, .msg-assistant .content h3 {
  color: var(--text-bright); margin: 16px 0 8px; }
.msg-assistant .content blockquote {
  border-left: 3px solid var(--accent); padding-left: 14px;
  color: var(--text-dim); margin: 10px 0;
}
.msg-assistant .content table { border-collapse: collapse; margin: 10px 0; font-size: 13.5px; }
.msg-assistant .content th, .msg-assistant .content td {
  border: 1px solid var(--border); padding: 7px 14px; text-align: left; }
.msg-assistant .content th { background: var(--bg-surface); color: var(--text-bright); }
.msg-assistant .content a { color: var(--blue); }

/* 系统 / 错误消息（居中胶囊） */
.msg-system {
  text-align: center; color: var(--text-dim); font-size: 12px;
  white-space: pre-wrap; word-break: break-all;
}
.msg-error {
  max-width: 820px; margin: 0 auto 20px; color: var(--red);
  background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.25);
  border-radius: 10px; padding: 10px 16px; font-size: 13px; animation: fadeUp 0.25s ease;
}

/* 工具调用卡片 */
.tool-block {
  max-width: 820px; margin: 0 auto 12px;
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius); overflow: hidden; animation: fadeUp 0.25s ease;
}
.tool-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; cursor: pointer; user-select: none;
  font-size: 13px; transition: background 0.15s;
}
.tool-header:hover { background: var(--bg-hover); }
.tool-header .chevron { font-size: 10px; color: var(--text-dim); transition: transform 0.2s; width: 12px; }
.tool-header .chevron.expanded { transform: rotate(90deg); }
.tool-header .tool-icon { font-size: 14px; }
.tool-header .name { color: var(--blue); font-weight: 600; font-family: "SF Mono", Consolas, monospace; font-size: 12.5px; }
.tool-header .args-preview {
  color: var(--text-dim); font-size: 12px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0;
  font-family: "SF Mono", Consolas, monospace;
}
.tool-header .status {
  margin-left: auto; font-size: 11px; font-weight: 600;
  padding: 3px 10px; border-radius: 20px; flex-shrink: 0;
}
.tool-header .status.ok { color: var(--green); background: rgba(74,222,128,0.1); }
.tool-header .status.err { color: var(--red); background: rgba(248,113,113,0.1); }
.tool-header .status.loading { color: var(--yellow); background: rgba(251,191,36,0.1); }
.tool-header .status.loading::before {
  content: ""; display: inline-block; width: 8px; height: 8px; margin-right: 6px;
  border: 1.5px solid var(--yellow); border-top-color: transparent;
  border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: -1px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.tool-body {
  display: none; padding: 12px 14px; border-top: 1px solid var(--border);
  font-size: 12.5px; max-height: 320px; overflow-y: auto; white-space: pre-wrap;
  word-break: break-all; color: var(--text-dim);
  font-family: "SF Mono", Consolas, monospace;
}
.tool-body.show { display: block; }
.tool-body .args-block { color: var(--blue); margin-bottom: 10px; }

/* 思考过程（折叠） */
.thinking-block {
  max-width: 820px; margin: 0 auto 12px;
  background: rgba(139,124,246,0.05); border: 1px solid rgba(139,124,246,0.18);
  border-radius: var(--radius); overflow: hidden; animation: fadeUp 0.25s ease;
}
.thinking-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; cursor: pointer; user-select: none;
  font-size: 13px; color: var(--accent); transition: background 0.15s;
}
.thinking-header:hover { background: var(--accent-soft); }
.thinking-header .chevron { font-size: 10px; color: var(--text-dim); transition: transform 0.2s; width: 12px; }
.thinking-header .chevron.expanded { transform: rotate(90deg); }
.thinking-body {
  display: none; padding: 12px 14px; border-top: 1px solid rgba(139,124,246,0.15);
  font-size: 12.5px; max-height: 300px; overflow-y: auto; white-space: pre-wrap;
  color: var(--text-dim); font-style: italic;
}
.thinking-body.show { display: block; }

/* 权限弹窗 */
.perm-dialog {
  max-width: 820px; margin: 0 auto 16px;
  background: var(--bg-surface); border: 1px solid rgba(251,191,36,0.4);
  border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow);
  animation: fadeUp 0.25s ease;
}
.perm-dialog .title { color: var(--yellow); font-weight: 700; margin-bottom: 8px; font-size: 14px; }
.perm-dialog .desc { color: var(--text); margin-bottom: 14px; font-size: 13px; white-space: pre-wrap; line-height: 1.6; }
.perm-dialog .actions { display: flex; gap: 10px; }
.perm-dialog button {
  padding: 8px 18px; border-radius: 8px; border: 1px solid var(--border);
  cursor: pointer; font-family: inherit; font-size: 13px; font-weight: 600;
  transition: all 0.15s;
}
.btn-allow { background: var(--green); color: #0b2013; border-color: var(--green); }
.btn-allow:hover { filter: brightness(1.1); }
.btn-deny { background: transparent; color: var(--red); border-color: rgba(248,113,113,0.5); }
.btn-deny:hover { background: rgba(248,113,113,0.1); }
.btn-always { background: transparent; color: var(--blue); border-color: rgba(110,168,254,0.5); }
.btn-always:hover { background: rgba(110,168,254,0.1); }
.perm-dialog label { display: block; margin: 6px 0; cursor: pointer; }
.perm-dialog input[type="text"] {
  background: var(--bg-input); color: var(--text); border: 1px solid var(--border);
  border-radius: 6px; padding: 6px 10px; font-family: inherit; font-size: 13px; width: 320px;
}
.perm-dialog .answered { color: var(--text-dim); font-size: 13px; }

/* 斜杠命令菜单 */
#slash-menu {
  display: none; position: absolute; bottom: calc(100% + 8px); left: 0; right: 0;
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius); max-height: 260px;
  overflow-y: auto; box-shadow: var(--shadow); z-index: 10;
}
#slash-menu.show { display: block; }
.slash-item {
  padding: 10px 14px; cursor: pointer; display: flex; gap: 10px; align-items: baseline;
}
.slash-item:hover, .slash-item.active { background: var(--accent-soft); }
.slash-item .cmd-name { color: var(--accent); font-weight: 600; white-space: nowrap; font-family: "SF Mono", Consolas, monospace; font-size: 13px; }
.slash-item .cmd-desc { color: var(--text-dim); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 输入区域 */
#input-wrap { flex-shrink: 0; padding: 12px 24px 20px; }
#input-box {
  max-width: 820px; margin: 0 auto; position: relative;
  background: var(--bg-input); border: 1px solid var(--border);
  border-radius: 16px; display: flex; gap: 10px; align-items: flex-end;
  padding: 10px 10px 10px 18px; transition: border-color 0.2s, box-shadow 0.2s;
}
#input-box:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(139,124,246,0.15);
}
#input-box textarea {
  flex: 1; background: none; color: var(--text-bright); border: none; outline: none;
  font-family: inherit; font-size: 14.5px; resize: none;
  min-height: 24px; max-height: 200px; line-height: 1.6; padding: 4px 0;
}
#input-box textarea::placeholder { color: var(--text-dim); }
#input-box textarea:disabled { opacity: 0.5; }
#send-btn {
  width: 38px; height: 38px; border-radius: 11px; border: none; flex-shrink: 0;
  background: var(--accent); color: #fff; cursor: pointer;
  font-size: 17px; display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
#send-btn:hover:not(:disabled) { background: var(--accent-hover); transform: translateY(-1px); }
#send-btn:disabled { opacity: 0.35; cursor: not-allowed; }
#input-hint {
  max-width: 820px; margin: 8px auto 0; text-align: center;
  font-size: 11px; color: var(--text-dim);
}

/* 流式光标 */
.cursor { display: inline-block; width: 8px; height: 16px; background: var(--accent); border-radius: 2px; vertical-align: -2px; animation: blink 1s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }

/* 完成指示 */
.done-indicator {
  max-width: 820px; margin: 4px auto 20px; color: var(--text-dim);
  font-size: 12px; display: flex; align-items: center; gap: 6px;
}
.done-indicator::before { content: "✻"; color: var(--accent); }

/* 窄屏适配：隐藏侧边栏 */
@media (max-width: 860px) {
  #sidebar { display: none; }
}
</style>
</head>
<body>
<div id="app">
  <aside id="sidebar">
    <div class="sidebar-logo">
      <div class="logo-icon">⚡</div>
      <div>
        <div class="logo-name">CodeAgent</div>
        <div class="logo-sub">Remote Console</div>
      </div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-section-title">Session</div>
      <div class="sidebar-card">
        <div class="row"><span class="k">ID</span><span class="v" id="session-id">—</span></div>
        <div class="row"><span class="k">CWD</span><span class="v" id="session-cwd" title="">—</span></div>
      </div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-section-title">Commands</div>
    </div>
    <div id="command-list"></div>
  </aside>

  <div id="main">
    <div id="topbar">
      <span class="crumb"><b>Chat</b></span>
      <div class="info">
        <span id="conn-status"><span class="dot disconnected"></span>Connecting...</span>
        <span id="token-info"></span>
      </div>
    </div>
    <div id="messages"><div class="msg-column" id="msg-column"></div></div>
    <div id="input-wrap">
      <div id="input-box">
        <div id="slash-menu"></div>
        <textarea id="input" placeholder="给 CodeAgent 发送消息…" rows="1"></textarea>
        <button id="send-btn" title="发送 (Enter)">↑</button>
      </div>
      <div id="input-hint">Enter 发送 · Shift+Enter 换行 · / 唤起命令</div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
const messagesEl = document.getElementById('messages');
const msgColumn = document.getElementById('msg-column');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('send-btn');
const connStatus = document.getElementById('conn-status');
const tokenInfo = document.getElementById('token-info');
const slashMenu = document.getElementById('slash-menu');
const sessionIdEl = document.getElementById('session-id');
const sessionCwdEl = document.getElementById('session-cwd');
const commandListEl = document.getElementById('command-list');

let ws = null;
let streaming = false;
let allCommands = [];
let slashCursor = 0;
let slashFiltered = [];
let currentAssistantEl = null;
let currentStreamText = '';
let currentThinkingEl = null;
let currentThinkingText = '';
let autoScroll = true;
let pingTimer = null;
let connectedOnce = false;

// Markdown 渲染配置
if (typeof marked !== 'undefined') {
  marked.setOptions({ breaks: true, gfm: true });
}

function renderMarkdown(text) {
  if (typeof marked !== 'undefined') {
    try { return marked.parse(text); } catch(e) {}
  }
  return escapeHtml(text);
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// 工具名 → 图标
function toolIcon(name) {
  const n = (name || '').toLowerCase();
  if (n.includes('bash') || n.includes('shell')) return '💻';
  if (n.includes('read')) return '📄';
  if (n.includes('write')) return '✏️';
  if (n.includes('edit')) return '✏️';
  if (n.includes('glob') || n.includes('search') || n.includes('grep')) return '🔍';
  if (n.includes('agent') || n.includes('task')) return '🤖';
  if (n.includes('web') || n.includes('fetch')) return '🌐';
  if (n.includes('skill')) return '⚡';
  return '🔧';
}

function connect() {
  if (pingTimer) { clearInterval(pingTimer); pingTimer = null; }
  if (ws) { try { ws.onclose = null; ws.close(); } catch(e) {} ws = null; }
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws');

  ws.onopen = () => {
    connStatus.innerHTML = '<span class="dot connected"></span>Connected';
    // 每 10 秒发一次应用层 ping，防止连接被中间件/浏览器回收
    pingTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping', data: {} }));
      }
    }, 10000);
  };

  ws.onclose = () => {
    connStatus.innerHTML = '<span class="dot disconnected"></span>Reconnecting...';
    if (pingTimer) { clearInterval(pingTimer); pingTimer = null; }
    setTimeout(connect, 3000);
  };

  ws.onerror = () => {};

  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    handleMessage(msg);
  };
}

function handleMessage(msg) {
  switch (msg.type) {
    case 'connected':
      sessionIdEl.textContent = msg.data.session || '—';
      sessionCwdEl.textContent = msg.data.cwd || '—';
      sessionCwdEl.title = msg.data.cwd || '';
      if (!connectedOnce) {
        addSystem('已连接 · Session ' + msg.data.session);
        connectedOnce = true;
      }
      break;

    case 'commands':
      allCommands = msg.data || [];
      renderCommandList();
      break;

    case 'system':
      addSystem(msg.data.message);
      break;

    case 'clear':
      msgColumn.innerHTML = '';
      addSystem('对话已清空');
      break;

    case 'command_done':
      streaming = false;
      updateUI();
      break;

    case 'replay_user':
      addUser(msg.data.content);
      break;

    case 'replay_assistant': {
      const el = addAssistant('');
      updateAssistant(el, msg.data.content, false);
      break;
    }

    case 'stream_text':
      if (currentThinkingEl) {
        currentThinkingEl.querySelector('.thinking-header span:last-child').textContent = '💭 思考过程';
        currentThinkingEl = null;
        currentThinkingText = '';
      }
      if (!currentAssistantEl) {
        currentAssistantEl = addAssistant('');
        currentStreamText = '';
      }
      currentStreamText += msg.data.text;
      updateAssistant(currentAssistantEl, currentStreamText, true);
      break;

    case 'stream_end':
      if (currentAssistantEl) {
        updateAssistant(currentAssistantEl, currentStreamText, false);
      }
      currentAssistantEl = null;
      currentStreamText = '';
      break;

    case 'thinking_text':
      if (!currentThinkingEl) {
        currentThinkingEl = addThinking();
        currentThinkingText = '';
      }
      currentThinkingText += msg.data.text;
      currentThinkingEl.querySelector('.thinking-body').textContent = currentThinkingText;
      break;

    case 'tool_use':
      if (currentThinkingEl) {
        currentThinkingEl.querySelector('.thinking-header span:last-child').textContent = '💭 思考过程';
        currentThinkingEl = null;
        currentThinkingText = '';
      }
      addToolUse(msg.data);
      break;

    case 'tool_result':
      updateToolResult(msg.data);
      break;

    case 'permission_request':
      addPermissionDialog(msg.data);
      break;

    case 'ask_user':
      addAskUserDialog(msg.data);
      break;

    case 'turn_complete':
      break;

    case 'loop_complete':
      if (currentAssistantEl) {
        updateAssistant(currentAssistantEl, currentStreamText, false);
        currentAssistantEl = null;
        currentStreamText = '';
      }
      currentThinkingEl = null;
      currentThinkingText = '';
      const el = document.createElement('div');
      el.className = 'done-indicator';
      el.textContent = 'Done in ' + msg.data.elapsed.toFixed(1) + 's';
      msgColumn.appendChild(el);
      streaming = false;
      updateUI();
      scrollToBottom();
      break;

    case 'usage':
      tokenInfo.textContent = 'In ' + formatTokens(msg.data.inputTokens) + ' · Out ' + formatTokens(msg.data.outputTokens);
      break;

    case 'error':
      addError(msg.data.message);
      streaming = false;
      updateUI();
      break;

    case 'compact':
      addSystem('⟳ ' + msg.data.message);
      break;

    case 'retry':
      addSystem('↻ 重试中: ' + msg.data.reason);
      break;
  }
}

function renderCommandList() {
  commandListEl.innerHTML = allCommands.map(c =>
    '<div class="cmd-item" data-cmd="/' + escapeHtml(c.name) + '">' +
      '<span class="cmd-name">/' + escapeHtml(c.name) + '</span>' +
      '<span class="cmd-desc">' + escapeHtml(c.description) + '</span>' +
    '</div>'
  ).join('');
  commandListEl.querySelectorAll('.cmd-item').forEach(el => {
    el.addEventListener('click', () => {
      inputEl.value = el.dataset.cmd + ' ';
      inputEl.focus();
      inputEl.dispatchEvent(new Event('input'));
    });
  });
}

function formatTokens(n) {
  if (n > 1000000) return (n/1000000).toFixed(1) + 'M';
  if (n > 1000) return (n/1000).toFixed(1) + 'K';
  return '' + n;
}

function addUser(text) {
  const div = document.createElement('div');
  div.className = 'msg msg-user';
  div.innerHTML = '<div class="bubble"></div>';
  div.querySelector('.bubble').textContent = text;
  msgColumn.appendChild(div);
  scrollToBottom();
}

function addAssistant(text) {
  const div = document.createElement('div');
  div.className = 'msg msg-assistant';
  div.innerHTML = '<div class="avatar">⚡</div><div class="content"></div>';
  msgColumn.appendChild(div);
  scrollToBottom();
  return div;
}

function updateAssistant(el, text, isStreaming) {
  const contentEl = el.querySelector('.content');
  // 检测 <think>...</think> 标签，分离思考内容和正文
  const thinkMatch = text.match(/^<think>([\s\S]*?)<\/think>\s*([\s\S]*)$/);
  if (thinkMatch) {
    const thinkText = thinkMatch[1].trim();
    const bodyText = thinkMatch[2].trim();
    let html = '';
    if (thinkText) {
      html += '<div class="thinking-block">' +
        '<div class="thinking-header" onclick="toggleThinking(this)">' +
          '<span class="chevron">▶</span>' +
          '<span>💭 思考过程</span>' +
        '</div>' +
        '<div class="thinking-body">' + escapeHtml(thinkText) + '</div>' +
      '</div>';
    }
    if (bodyText) {
      html += renderMarkdown(bodyText);
    }
    if (isStreaming) html += '<span class="cursor"></span>';
    contentEl.innerHTML = html;
  } else if (text.startsWith('<think>') && isStreaming) {
    // 思考还没结束，显示为折叠的 thinking 块 + 光标
    const thinkBody = text.replace(/^<think>\s*/, '');
    let html = '<div class="thinking-block">' +
      '<div class="thinking-header" onclick="toggleThinking(this)">' +
        '<span class="chevron">▶</span>' +
        '<span>💭 思考中...</span>' +
      '</div>' +
      '<div class="thinking-body">' + escapeHtml(thinkBody) + '</div>' +
    '</div>';
    html += '<span class="cursor"></span>';
    contentEl.innerHTML = html;
  } else {
    let html = renderMarkdown(text);
    if (isStreaming) html += '<span class="cursor"></span>';
    contentEl.innerHTML = html;
  }
  scrollToBottom();
}

function addThinking() {
  const div = document.createElement('div');
  div.className = 'thinking-block';
  div.innerHTML =
    '<div class="thinking-header" onclick="toggleThinking(this)">' +
      '<span class="chevron">▶</span>' +
      '<span>💭 思考中...</span>' +
    '</div>' +
    '<div class="thinking-body"></div>';
  msgColumn.appendChild(div);
  scrollToBottom();
  return div;
}

function toggleThinking(header) {
  header.querySelector('.chevron').classList.toggle('expanded');
  header.nextElementSibling.classList.toggle('show');
}

function addSystem(text) {
  const div = document.createElement('div');
  div.className = 'msg msg-system';
  div.textContent = text;
  msgColumn.appendChild(div);
  scrollToBottom();
}

function addError(text) {
  const div = document.createElement('div');
  div.className = 'msg-error';
  div.textContent = '✖ ' + text;
  msgColumn.appendChild(div);
  scrollToBottom();
}

// 工具调用
const toolElements = {};

function addToolUse(data) {
  const div = document.createElement('div');
  div.className = 'tool-block';

  const argsStr = data.args ? JSON.stringify(data.args, null, 2) : '';
  let argsPreview = '';
  if (data.args) {
    if (data.args.command) argsPreview = data.args.command;
    else if (data.args.file_path) argsPreview = data.args.file_path;
    else if (data.args.pattern) argsPreview = data.args.pattern;
    else if (data.args.path) argsPreview = data.args.path;
  }

  div.innerHTML =
    '<div class="tool-header" onclick="toggleTool(this)">' +
      '<span class="chevron">▶</span>' +
      '<span class="tool-icon">' + toolIcon(data.toolName) + '</span>' +
      '<span class="name">' + escapeHtml(data.toolName) + '</span>' +
      (argsPreview ? '<span class="args-preview">' + escapeHtml(argsPreview) + '</span>' : '') +
      '<span class="status loading">running</span>' +
    '</div>' +
    '<div class="tool-body">' +
      (argsStr ? '<div class="args-block">Args:\n' + escapeHtml(argsStr) + '</div>' : '') +
      '<div class="tool-output"></div>' +
    '</div>';

  msgColumn.appendChild(div);
  toolElements[data.toolName + '_' + (data.toolId || '')] = div;
  scrollToBottom();
}

function updateToolResult(data) {
  const key = data.toolName + '_' + (data.toolId || '');
  const div = toolElements[key];
  if (div) {
    const statusEl = div.querySelector('.status');
    if (data.isError) {
      statusEl.className = 'status err';
      statusEl.textContent = '✗ ' + data.elapsed.toFixed(1) + 's';
    } else {
      statusEl.className = 'status ok';
      statusEl.textContent = '✓ ' + data.elapsed.toFixed(1) + 's';
    }
    const outputEl = div.querySelector('.tool-output');
    if (data.output) {
      const truncated = data.output.length > 5000 ? data.output.substring(0, 5000) + '\n... (truncated)' : data.output;
      outputEl.textContent = truncated;
    }
    delete toolElements[key];
  } else {
    // 如果没有匹配到，直接创建一个完成的 tool block
    const block = document.createElement('div');
    block.className = 'tool-block';
    const status = data.isError ? '✗' : '✓';
    const statusClass = data.isError ? 'err' : 'ok';
    block.innerHTML =
      '<div class="tool-header" onclick="toggleTool(this)">' +
        '<span class="chevron">▶</span>' +
        '<span class="tool-icon">' + toolIcon(data.toolName) + '</span>' +
        '<span class="name">' + escapeHtml(data.toolName) + '</span>' +
        '<span class="status ' + statusClass + '">' + status + ' ' + data.elapsed.toFixed(1) + 's</span>' +
      '</div>' +
      '<div class="tool-body">' + escapeHtml(data.output || '') + '</div>';
    msgColumn.appendChild(block);
  }
  scrollToBottom();
}

function toggleTool(header) {
  const icon = header.querySelector('.chevron');
  const body = header.nextElementSibling;
  icon.classList.toggle('expanded');
  body.classList.toggle('show');
}

// 权限弹窗
function addPermissionDialog(data) {
  const div = document.createElement('div');
  div.className = 'perm-dialog';
  div.id = 'perm-' + data.id;
  div.innerHTML =
    '<div class="title">🔒 需要授权: ' + escapeHtml(data.toolName) + '</div>' +
    '<div class="desc">' + escapeHtml(data.description) + '</div>' +
    '<div class="actions">' +
      '<button class="btn-allow" onclick="respondPerm(\'' + data.id + '\', \'allow\')">允许</button>' +
      '<button class="btn-always" onclick="respondPerm(\'' + data.id + '\', \'allowAlways\')">始终允许</button>' +
      '<button class="btn-deny" onclick="respondPerm(\'' + data.id + '\', \'deny\')">拒绝</button>' +
    '</div>';
  msgColumn.appendChild(div);
  scrollToBottom();
}

function respondPerm(id, response) {
  ws.send(JSON.stringify({ type: 'permission_response', data: { id, response } }));
  const el = document.getElementById('perm-' + id);
  if (el) {
    const label = { allow: '已允许', allowAlways: '已始终允许', deny: '已拒绝' }[response] || response;
    el.innerHTML = '<div class="answered">🔒 授权结果: ' + label + '</div>';
  }
}

// Ask User 弹窗
function addAskUserDialog(data) {
  const div = document.createElement('div');
  div.className = 'perm-dialog';
  div.id = 'ask-' + data.id;

  let html = '<div class="title">❓ 请回答以下问题</div>';
  const questions = data.questions || [];
  questions.forEach((q, qi) => {
    html += '<div style="margin-bottom:14px;">';
    html += '<div style="margin-bottom:8px;color:var(--text-bright);font-weight:600;">' + escapeHtml(q.question || q.Text || '') + '</div>';
    const options = q.options || q.Options || [];
    options.forEach((opt, oi) => {
      const label = opt.label || opt.Label || '';
      const desc = opt.description || opt.Description || '';
      html += '<label>' +
        '<input type="radio" name="ask_' + data.id + '_' + qi + '" value="' + escapeHtml(label) + '"> ' +
        '<span style="color:var(--blue)">' + escapeHtml(label) + '</span>' +
        (desc ? ' <span style="color:var(--text-dim);font-size:12px;">— ' + escapeHtml(desc) + '</span>' : '') +
        '</label>';
    });
    // Other 选项
    html += '<label>' +
      '<input type="radio" name="ask_' + data.id + '_' + qi + '" value="__other__"> ' +
      '<span style="color:var(--text-dim)">其他: </span>' +
      '<input type="text" id="ask_other_' + data.id + '_' + qi + '">' +
      '</label>';
    html += '</div>';
  });
  html += '<div class="actions"><button class="btn-allow" onclick="respondAsk(\'' + data.id + '\',' + questions.length + ')">提交</button></div>';

  div.innerHTML = html;
  msgColumn.appendChild(div);
  scrollToBottom();
}

function respondAsk(id, qCount) {
  const answers = {};
  for (let i = 0; i < qCount; i++) {
    const radios = document.querySelectorAll('input[name="ask_' + id + '_' + i + '"]');
    let val = '';
    radios.forEach(r => {
      if (r.checked) {
        if (r.value === '__other__') {
          val = document.getElementById('ask_other_' + id + '_' + i).value;
        } else {
          val = r.value;
        }
      }
    });
    answers['question_' + i] = val;
  }
  ws.send(JSON.stringify({ type: 'ask_user_response', data: { id, answers } }));
  const el = document.getElementById('ask-' + id);
  if (el) {
    el.innerHTML = '<div class="answered">✓ 已提交</div>';
  }
}

// 滚动控制
messagesEl.addEventListener('scroll', () => {
  const { scrollTop, scrollHeight, clientHeight } = messagesEl;
  autoScroll = scrollHeight - scrollTop - clientHeight < 60;
});

function scrollToBottom() {
  if (autoScroll) {
    requestAnimationFrame(() => {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }
}

// 输入处理
function sendMessage() {
  if (slashMenu.classList.contains('show')) { hideSlashMenu(); }
  const text = inputEl.value.trim();
  if (!text || streaming) return;
  addUser(text);
  ws.send(JSON.stringify({ type: 'user_message', data: { content: text } }));
  inputEl.value = '';
  inputEl.style.height = 'auto';
  streaming = true;
  updateUI();
}

function updateUI() {
  sendBtn.disabled = streaming;
  inputEl.disabled = streaming;
  if (!streaming) inputEl.focus();
}

// ── 斜杠命令菜单 ──

function showSlashMenu(filter) {
  const prefix = filter.toLowerCase();
  slashFiltered = allCommands.filter(c => c.name.startsWith(prefix));
  if (slashFiltered.length === 0) { hideSlashMenu(); return; }
  slashCursor = 0;
  renderSlashMenu();
  slashMenu.classList.add('show');
}

function hideSlashMenu() {
  slashMenu.classList.remove('show');
  slashFiltered = [];
  slashCursor = 0;
}

function renderSlashMenu() {
  slashMenu.innerHTML = slashFiltered.map((c, i) =>
    '<div class="slash-item' + (i === slashCursor ? ' active' : '') + '" data-idx="' + i + '">' +
      '<span class="cmd-name">/' + escapeHtml(c.name) + '</span>' +
      '<span class="cmd-desc">' + escapeHtml(c.description) + '</span>' +
    '</div>'
  ).join('');
  // 点击选中
  slashMenu.querySelectorAll('.slash-item').forEach(el => {
    el.addEventListener('mousedown', (e) => {
      e.preventDefault();
      const idx = parseInt(el.dataset.idx);
      selectSlashItem(idx);
    });
  });
  // 滚动到当前高亮项
  const activeEl = slashMenu.querySelector('.active');
  if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
}

function selectSlashItem(idx) {
  const cmd = slashFiltered[idx];
  if (!cmd) return;
  inputEl.value = '/' + cmd.name + ' ';
  hideSlashMenu();
  inputEl.focus();
}

inputEl.addEventListener('keydown', (e) => {
  if (slashMenu.classList.contains('show')) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      slashCursor = Math.min(slashCursor + 1, slashFiltered.length - 1);
      renderSlashMenu();
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      slashCursor = Math.max(slashCursor - 1, 0);
      renderSlashMenu();
      return;
    }
    if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) {
      e.preventDefault();
      selectSlashItem(slashCursor);
      return;
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      hideSlashMenu();
      return;
    }
  }
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px';

  const val = inputEl.value;
  // 检测是否在输入斜杠命令
  if (val.startsWith('/') && !val.includes('\n')) {
    const prefix = val.substring(1).split(' ')[0];
    if (!val.includes(' ')) {
      showSlashMenu(prefix);
    } else {
      hideSlashMenu();
    }
  } else {
    hideSlashMenu();
  }
});

sendBtn.addEventListener('click', sendMessage);

// 启动
connect();
inputEl.focus();
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
# 架构/流程展示页（/arch 路由）：用于演示与简历展示
# ─────────────────────────────────────────────────────────────

ARCH_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeAgent · 系统架构</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg: #0f1115; --bg-surface: #15181e; --bg-card: #1a1e26; --bg-hover: #21262f;
  --text: #dfe3ea; --text-dim: #7d8590; --text-bright: #f2f4f8;
  --accent: #8b7cf6; --accent-soft: rgba(139,124,246,0.12);
  --green: #4ade80; --yellow: #fbbf24; --blue: #6ea8fe; --red: #f87171;
  --border: #262c36; --mono: "SF Mono", "Fira Code", Consolas, monospace;
}
html { scroll-behavior: smooth; }
body {
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Hiragino Sans GB", sans-serif;
  line-height: 1.7; -webkit-font-smoothing: antialiased;
}

/* 顶部导航 */
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 40px; height: 60px;
  background: rgba(15,17,21,0.82); backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}
nav .brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 16px; color: var(--text-bright); text-decoration: none; }
nav .brand .logo {
  width: 30px; height: 30px; border-radius: 8px; font-size: 15px;
  background: linear-gradient(135deg, #8b7cf6, #6ea8fe);
  display: flex; align-items: center; justify-content: center;
}
nav .links { display: flex; gap: 28px; align-items: center; }
nav .links a { color: var(--text-dim); text-decoration: none; font-size: 13.5px; transition: color 0.15s; }
nav .links a:hover { color: var(--text-bright); }
nav .links .cta {
  background: var(--accent); color: #fff !important; padding: 7px 16px;
  border-radius: 8px; font-weight: 600;
}
nav .links .cta:hover { background: #9d90f8; }

section { max-width: 1080px; margin: 0 auto; padding: 90px 40px 30px; }
.section-tag {
  display: inline-block; font-size: 11.5px; font-weight: 700; letter-spacing: 1.5px;
  color: var(--accent); background: var(--accent-soft);
  padding: 4px 12px; border-radius: 20px; margin-bottom: 14px; text-transform: uppercase;
}
h2 { font-size: 26px; color: var(--text-bright); margin-bottom: 12px; }
.section-desc { color: var(--text-dim); font-size: 14.5px; max-width: 720px; margin-bottom: 28px; }

/* Hero */
#hero { text-align: center; padding-top: 150px; padding-bottom: 60px; }
#hero .hero-logo {
  width: 72px; height: 72px; border-radius: 18px; margin: 0 auto 22px;
  background: linear-gradient(135deg, #8b7cf6, #6ea8fe); font-size: 34px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 32px rgba(139,124,246,0.4);
}
#hero h1 { font-size: 40px; color: var(--text-bright); letter-spacing: -0.5px; }
#hero .slogan { color: var(--text-dim); font-size: 16px; margin: 14px auto 26px; max-width: 560px; }
#hero .badges { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
#hero .badge {
  font-size: 12.5px; color: var(--text-dim); border: 1px solid var(--border);
  background: var(--bg-surface); padding: 5px 14px; border-radius: 20px; font-family: var(--mono);
}

/* 架构分层图 */
.layers { display: flex; flex-direction: column; gap: 10px; }
.layer {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px;
  padding: 16px 22px; display: flex; align-items: center; gap: 18px;
  transition: border-color 0.2s, transform 0.2s;
}
.layer:hover { border-color: var(--accent); transform: translateX(4px); }
.layer .layer-name {
  flex-shrink: 0; width: 130px; font-weight: 700; color: var(--text-bright); font-size: 14.5px;
}
.layer .layer-name .en { display: block; font-size: 11px; color: var(--text-dim); font-weight: 400; font-family: var(--mono); }
.layer .chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  font-size: 12.5px; padding: 4px 12px; border-radius: 8px;
  background: var(--bg-hover); color: var(--text); border: 1px solid var(--border);
  font-family: var(--mono);
}
.layer-arrow { text-align: center; color: var(--text-dim); font-size: 14px; line-height: 1; }

/* 卡片网格 */
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px;
  padding: 22px; transition: border-color 0.2s, transform 0.2s;
}
.card:hover { border-color: var(--accent); transform: translateY(-3px); }
.card .card-icon {
  width: 40px; height: 40px; border-radius: 10px; font-size: 19px; margin-bottom: 14px;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent-soft);
}
.card h3 { font-size: 15.5px; color: var(--text-bright); margin-bottom: 8px; }
.card p { font-size: 13.5px; color: var(--text-dim); }
.card code {
  font-family: var(--mono); font-size: 12px; color: #e6b673;
  background: #12151b; padding: 1px 6px; border-radius: 4px; border: 1px solid var(--border);
}
.card ul { padding-left: 18px; margin-top: 8px; }
.card li { font-size: 13px; color: var(--text-dim); margin: 5px 0; }
.card li b { color: var(--text); font-weight: 600; }

/* 流程步骤（Agent Loop） */
.flow { display: flex; flex-direction: column; gap: 0; }
.step { display: flex; gap: 18px; }
.step .rail { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; width: 36px; }
.step .num {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  background: var(--accent-soft); border: 1.5px solid var(--accent);
  color: var(--accent); font-weight: 700; font-size: 14px;
  display: flex; align-items: center; justify-content: center;
}
.step .line { flex: 1; width: 1.5px; background: var(--border); margin: 4px 0; }
.step:last-child .line { display: none; }
.step .step-body { padding-bottom: 26px; flex: 1; }
.step .step-body h3 { font-size: 15.5px; color: var(--text-bright); margin-bottom: 4px; }
.step .step-body h3 .hl { color: var(--accent); }
.step .step-body p { font-size: 13.5px; color: var(--text-dim); }
.step code {
  font-family: var(--mono); font-size: 12px; color: #e6b673;
  background: #12151b; padding: 1px 6px; border-radius: 4px; border: 1px solid var(--border);
}
.loop-hint {
  margin: 0 0 26px 54px; padding: 10px 16px; border: 1px dashed var(--accent);
  border-radius: 10px; color: var(--accent); font-size: 13px; background: var(--accent-soft);
}

/* 权限模式表格 */
table { width: 100%; border-collapse: collapse; font-size: 13.5px; background: var(--bg-card); border-radius: 14px; overflow: hidden; border: 1px solid var(--border); }
th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }
th { background: var(--bg-hover); color: var(--text-bright); font-size: 12.5px; letter-spacing: 0.5px; }
tr:last-child td { border-bottom: none; }
td.mode { font-family: var(--mono); color: var(--accent); font-weight: 600; }
td .ok { color: var(--green); } td .ask { color: var(--yellow); } td .no { color: var(--red); }

footer {
  text-align: center; color: var(--text-dim); font-size: 12.5px;
  padding: 40px; border-top: 1px solid var(--border); margin-top: 60px;
}
footer a { color: var(--accent); text-decoration: none; }
</style>
</head>
<body>

<nav>
  <a class="brand" href="#hero"><span class="logo">⚡</span>CodeAgent</a>
  <div class="links">
    <a href="#arch">系统架构</a>
    <a href="#loop">核心流程</a>
    <a href="#memory">记忆机制</a>
    <a href="#security">权限沙箱</a>
    <a class="cta" href="/">▸ 在线演示</a>
  </div>
</nav>

<section id="hero">
  <div class="hero-logo">⚡</div>
  <h1>CodeAgent</h1>
  <p class="slogan">运行在终端里的 AI 编程助手 —— Agent 主循环 · 工具调用 · 记忆系统 · 权限沙箱 · MCP 生态</p>
  <div class="badges">
    <span class="badge">Python 3.11+</span>
    <span class="badge">Anthropic / OpenAI 兼容协议</span>
    <span class="badge">WebSocket Remote</span>
    <span class="badge">Textual TUI</span>
    <span class="badge">MCP</span>
  </div>
</section>

<section id="arch">
  <div class="section-tag">Architecture</div>
  <h2>系统架构 · 六层设计</h2>
  <p class="section-desc">从接入层到模型层的完整分层：Web / TUI / 管道三种接入方式共享同一个 Agent 内核，能力层与安全层正交解耦。</p>
  <div class="layers">
    <div class="layer">
      <div class="layer-name">接入层<span class="en">Interface</span></div>
      <div class="chips"><span class="chip">Terminal TUI (Textual)</span><span class="chip">Web Remote (WebSocket)</span><span class="chip">Pipeline (-p / NDJSON)</span></div>
    </div>
    <div class="layer-arrow">↓</div>
    <div class="layer">
      <div class="layer-name">Agent 核心<span class="en">Core Loop</span></div>
      <div class="chips"><span class="chip">主循环 + 事件流</span><span class="chip">上下文管理</span><span class="chip">自动压缩 Compact</span><span class="chip">重试与恢复</span></div>
    </div>
    <div class="layer-arrow">↓</div>
    <div class="layer">
      <div class="layer-name">能力层<span class="en">Capabilities</span></div>
      <div class="chips"><span class="chip">工具注册表 (文件/Bash/搜索/子Agent)</span><span class="chip">斜杠命令</span><span class="chip">Skills 技能包</span><span class="chip">Hooks</span><span class="chip">Worktree 隔离</span></div>
    </div>
    <div class="layer-arrow">↓</div>
    <div class="layer">
      <div class="layer-name">安全层<span class="en">Security</span></div>
      <div class="chips"><span class="chip">四级权限模式</span><span class="chip">路径沙箱</span><span class="chip">危险命令检测</span><span class="chip">seatbelt / bwrap</span></div>
    </div>
    <div class="layer-arrow">↓</div>
    <div class="layer">
      <div class="layer-name">持久层<span class="en">Persistence</span></div>
      <div class="chips"><span class="chip">会话存储</span><span class="chip">记忆系统 (MEMORY.md)</span><span class="chip">指令加载</span><span class="chip">文件历史</span></div>
    </div>
    <div class="layer-arrow">↓</div>
    <div class="layer">
      <div class="layer-name">模型层<span class="en">LLM</span></div>
      <div class="chips"><span class="chip">Anthropic</span><span class="chip">OpenAI 兼容 (DeepSeek 等)</span><span class="chip">MCP 服务器</span></div>
    </div>
  </div>
</section>

<section id="loop">
  <div class="section-tag">Core Loop</div>
  <h2>Agent 主循环 · 一次提问的完整旅程</h2>
  <p class="section-desc">ReAct 式循环：推理 → 工具调用 → 观察 → 再推理，直到任务完成。每一步都带权限校验与流式反馈。</p>
  <div class="flow">
    <div class="step">
      <div class="rail"><div class="num">1</div><div class="line"></div></div>
      <div class="step-body">
        <h3><span class="hl">用户输入</span></h3>
        <p>来自 Web 界面 / 终端 TUI / 管道模式，经 WebSocket 或标准输入进入 Agent。</p>
      </div>
    </div>
    <div class="step">
      <div class="rail"><div class="num">2</div><div class="line"></div></div>
      <div class="step-body">
        <h3><span class="hl">上下文组装</span></h3>
        <p>系统提示词 + 指令文件（<code>CODEAGENT.md</code> / <code>AGENTS.md</code>）+ 记忆召回（LLM 从 <code>MEMORY.md</code> 索引挑选 ≤5 条相关记忆）+ 会话历史。超长时自动触发 <code>/compact</code> 压缩。</p>
      </div>
    </div>
    <div class="step">
      <div class="rail"><div class="num">3</div><div class="line"></div></div>
      <div class="step-body">
        <h3><span class="hl">LLM 流式推理</span></h3>
        <p>模型边生成边推送 <code>StreamText</code> / <code>ThinkingText</code> 事件，前端实时渲染气泡与思考折叠卡片。</p>
      </div>
    </div>
    <div class="step">
      <div class="rail"><div class="num">4</div><div class="line"></div></div>
      <div class="step-body">
        <h3><span class="hl">工具调用 · 权限校验</span></h3>
        <p>模型请求工具（读写文件 / Bash / 搜索 / 子 Agent…）→ 权限模式矩阵 + 规则引擎 + 危险命令检测 → 未授权操作弹窗询问用户。</p>
      </div>
    </div>
    <div class="step">
      <div class="rail"><div class="num">5</div><div class="line"></div></div>
      <div class="step-body">
        <h3><span class="hl">沙箱执行</span></h3>
        <p>文件操作限制在项目根目录 + 系统临时目录，realpath 防符号链接逃逸，配置目录禁写；macOS seatbelt 提供系统级隔离。</p>
      </div>
    </div>
    <div class="loop-hint">↻ 工具结果回注上下文，回到第 3 步继续推理，直到模型不再请求工具</div>
    <div class="step">
      <div class="rail"><div class="num">6</div><div class="line"></div></div>
      <div class="step-body">
        <h3><span class="hl">完成 · 沉淀</span></h3>
        <p>输出最终答复与 Token 用量；后台 MemoryConsolidator 将会话要点固化进记忆库，供后续会话召回。</p>
      </div>
    </div>
  </div>
</section>

<section id="memory">
  <div class="section-tag">Memory</div>
  <h2>记忆机制 · 四层设计</h2>
  <p class="section-desc">对齐 Claude Code 的记忆架构：指令注入、文件化记忆、LLM 智能召回、后台固化，跨会话持续学习。</p>
  <div class="grid">
    <div class="card">
      <div class="card-icon">📜</div>
      <h3>L1 · 指令注入</h3>
      <p>启动时加载项目级与用户级的 <code>CODEAGENT.md</code> / <code>AGENTS.md</code>，直接并入系统提示词，定义项目规范与偏好。</p>
    </div>
    <div class="card">
      <div class="card-icon">🗂️</div>
      <h3>L2 · 文件化记忆</h3>
      <p>每条记忆一个 <code>.md</code> 文件 + frontmatter 元数据，<code>MEMORY.md</code> 仅存索引（200 行 / 25KB 上限）。</p>
      <ul>
        <li><b>user / feedback</b> → 用户级目录，跨项目跟随</li>
        <li><b>project / reference</b> → 项目级 <code>.codeagent/memory/</code></li>
      </ul>
    </div>
    <div class="card">
      <div class="card-icon">🎯</div>
      <h3>L3 · 智能召回</h3>
      <p>每次提问时，用一次 LLM side-query 从索引中精选最多 5 条相关记忆注入上下文，避免全量塞入浪费 Token。</p>
    </div>
    <div class="card">
      <div class="card-icon">💾</div>
      <h3>L4 · 后台固化</h3>
      <p>MemoryConsolidator 定期将近期会话提炼为记忆条目；文件锁 + 时间戳防多实例并发写入冲突。</p>
    </div>
  </div>
</section>

<section id="security">
  <div class="section-tag">Security</div>
  <h2>权限沙箱 · 四级模式</h2>
  <p class="section-desc">工具按类别（读 / 写 / 命令）匹配不同决策，配合路径沙箱与危险命令检测，让 Agent 安全地在真实项目中工作。</p>
  <table>
    <tr><th>权限模式</th><th>读操作</th><th>文件写入</th><th>命令执行</th><th>适用场景</th></tr>
    <tr><td class="mode">default</td><td><span class="ok">✓ 允许</span></td><td><span class="ask">? 询问</span></td><td><span class="ask">? 询问</span></td><td>日常使用（默认）</td></tr>
    <tr><td class="mode">acceptEdits</td><td><span class="ok">✓ 允许</span></td><td><span class="ok">✓ 允许</span></td><td><span class="ask">? 询问</span></td><td>信任编辑、谨慎跑命令</td></tr>
    <tr><td class="mode">plan</td><td><span class="ok">✓ 允许</span></td><td><span class="no">✗ 拒绝</span></td><td><span class="no">✗ 拒绝</span></td><td>只读规划、方案评审</td></tr>
    <tr><td class="mode">bypassPermissions</td><td><span class="ok">✓ 允许</span></td><td><span class="ok">✓ 允许</span></td><td><span class="ok">✓ 允许</span></td><td>全自动化（慎用）</td></tr>
  </table>
</section>

<footer>
  ⚡ CodeAgent · <a href="https://github.com/g164765280-netizen/codeagent">github.com/g164765280-netizen/codeagent</a> · <a href="/">在线演示 →</a>
</footer>

</body>
</html>"""
