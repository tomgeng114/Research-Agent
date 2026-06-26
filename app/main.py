"""
Research-Agent — Multi-Agent Collaborative Research System
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Research-Agent",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# ── Frontend ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return FRONTEND_HTML


@app.get("/health")
def health() -> dict:
    return {"status": "healthy"}


@app.on_event("startup")
def on_startup() -> None:
    from app.memory.memory_manager import MemoryManager
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "research_history.db",
    )
    MemoryManager(db_path)
    logger.info("Research-Agent started — http://127.0.0.1:8001")


# ── HTML (inline to avoid static file complexity) ─────────────
# Uses marked.js + highlight.js from CDN for markdown rendering

FRONTEND_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Research-Agent | 多智能体协作研究系统</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11/styles/github-dark.min.css">
<script src="https://cdn.jsdelivr.net/npm/highlight.js@11/lib/core.min.js"></script>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --text: #e1e4e8;
    --text2: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --orange: #d2991d;
    --red: #f85149;
    --radius: 10px;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg); color: var(--text); min-height:100vh;
  }
  .layout { display:flex; height:100vh; }
  .sidebar {
    width:300px; min-width:300px; background:var(--surface);
    border-right:1px solid var(--border); display:flex; flex-direction:column;
  }
  .sidebar-header {
    padding:20px; border-bottom:1px solid var(--border);
    font-size:16px; font-weight:700; display:flex; align-items:center; gap:8px;
  }
  .sidebar-header .dot { width:8px; height:8px; border-radius:50%; background:var(--green); }
  .history-list { flex:1; overflow-y:auto; padding:8px; }
  .history-item {
    padding:12px; border-radius:8px; cursor:pointer; margin-bottom:4px;
    transition: background .15s; border:1px solid transparent;
  }
  .history-item:hover { background:rgba(255,255,255,0.04); }
  .history-item.active { background:rgba(88,166,255,0.1); border-color:var(--accent); }
  .history-item .topic { font-size:13px; font-weight:600; margin-bottom:4px; line-height:1.4; }
  .history-item .meta { font-size:11px; color:var(--text2); }
  .main {
    flex:1; display:flex; flex-direction:column; overflow:hidden;
  }
  .main-header {
    padding:16px 24px; border-bottom:1px solid var(--border);
    font-size:15px; font-weight:600; display:flex; align-items:center; gap:8px;
  }
  .input-area {
    padding:16px 24px; border-bottom:1px solid var(--border);
  }
  .input-row { display:flex; gap:10px; }
  .input-row input {
    flex:1; padding:12px 16px; background:var(--bg); border:1px solid var(--border);
    border-radius:var(--radius); color:var(--text); font-size:14px; outline:none;
  }
  .input-row input:focus { border-color:var(--accent); }
  .input-row input::placeholder { color:var(--text2); }
  .input-row button {
    padding:12px 24px; background:var(--accent); color:#fff; border:none;
    border-radius:var(--radius); font-size:14px; font-weight:600; cursor:pointer;
    white-space:nowrap; transition:opacity .15s;
  }
  .input-row button:hover { opacity:0.85; }
  .input-row button:disabled { opacity:0.4; cursor:not-allowed; }
  .steps-row { display:flex; gap:16px; margin-top:8px; align-items:center; }
  .steps-row label { font-size:12px; color:var(--text2); display:flex; align-items:center; gap:4px; }
  .steps-row select {
    padding:4px 8px; background:var(--bg); color:var(--text);
    border:1px solid var(--border); border-radius:6px; font-size:12px;
  }
  .content-area {
    flex:1; overflow-y:auto; padding:24px;
  }
  /* Progress */
  .progress-bar {
    display:flex; gap:0; margin-bottom:20px;
  }
  .progress-step {
    flex:1; text-align:center; padding:10px 8px; font-size:12px; font-weight:600;
    color:var(--text2); border-bottom:3px solid var(--border); transition:all .3s;
  }
  .progress-step.done { color:var(--green); border-color:var(--green); }
  .progress-step.active { color:var(--accent); border-color:var(--accent); }
  .status-msg {
    padding:12px 16px; background:var(--surface); border-radius:8px;
    margin-bottom:16px; font-size:13px; display:flex; align-items:center; gap:8px;
  }
  .spinner {
    width:16px; height:16px; border:2px solid var(--border);
    border-top-color:var(--accent); border-radius:50%; animation:spin .8s linear infinite;
  }
  @keyframes spin { to { transform:rotate(360deg); } }
  /* Report */
  .report {
    background:var(--surface); border:1px solid var(--border);
    border-radius:var(--radius); padding:32px; line-height:1.8;
  }
  .report h1 { font-size:24px; margin:24px 0 16px; border-bottom:1px solid var(--border); padding-bottom:12px; }
  .report h2 { font-size:20px; margin:24px 0 12px; color:var(--accent); }
  .report h3 { font-size:16px; margin:16px 0 8px; }
  .report p { margin:8px 0; color:#c9d1d9; }
  .report ul, .report ol { margin:8px 0 8px 24px; color:#c9d1d9; }
  .report li { margin:4px 0; }
  .report table { width:100%; border-collapse:collapse; margin:16px 0; }
  .report th { background:rgba(88,166,255,0.1); padding:8px 12px; text-align:left; border:1px solid var(--border); font-size:13px; }
  .report td { padding:8px 12px; border:1px solid var(--border); font-size:13px; }
  .report code { background:rgba(255,255,255,0.08); padding:2px 6px; border-radius:4px; font-size:13px; }
  .report pre { background:rgba(0,0,0,0.3); padding:16px; border-radius:8px; overflow-x:auto; margin:12px 0; }
  .report blockquote { border-left:3px solid var(--accent); padding:8px 16px; margin:12px 0; color:var(--text2); }
  .report strong { color:var(--text); }
  .report hr { border:none; border-top:1px solid var(--border); margin:24px 0; }
  /* Empty state */
  .empty-state {
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    height:100%; color:var(--text2); text-align:center; gap:12px;
  }
  .empty-state .icon { font-size:48px; opacity:0.4; }
  .empty-state h2 { font-size:18px; color:var(--text); }
  .empty-state p { font-size:13px; max-width:400px; line-height:1.6; }
  /* Plan display */
  .plan-list { margin-bottom:16px; }
  .plan-item {
    padding:8px 12px; background:var(--bg); border-radius:6px;
    margin-bottom:4px; font-size:13px; display:flex; align-items:center; gap:8px;
  }
  .plan-item .num {
    width:22px; height:22px; border-radius:50%; background:var(--accent);
    color:#fff; font-size:11px; font-weight:700; display:flex;
    align-items:center; justify-content:center; flex-shrink:0;
  }
  .step-findings {
    margin:8px 0; padding:8px 12px; background:var(--bg);
    border-radius:6px; font-size:12px; color:var(--text2);
  }
  .step-findings strong { color:var(--text); }
  /* Toast */
  .toast {
    position:fixed; bottom:20px; right:20px; padding:12px 20px;
    background:var(--green); color:#000; border-radius:8px; font-size:13px;
    font-weight:600; opacity:0; transform:translateY(20px); transition:all .3s;
    z-index:100;
  }
  .toast.show { opacity:1; transform:translateY(0); }
  /* Responsive */
  @media (max-width:768px) {
    .layout { flex-direction:column; }
    .sidebar { width:100%; min-width:unset; max-height:200px; }
    .main-header { font-size:13px; }
    .input-row { flex-direction:column; }
    .report { padding:16px; }
  }
</style>
</head>
<body>
<div class="layout">
  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <span class="dot"></span> Research-Agent
    </div>
    <div class="history-list" id="historyList">
      <div style="padding:20px;text-align:center;color:var(--text2);font-size:13px;">
        暂无历史记录
      </div>
    </div>
  </aside>

  <!-- Main -->
  <main class="main">
    <div class="main-header">🚀 开始新的研究</div>
    <div class="input-area">
      <div class="input-row">
        <input id="topicInput" type="text" placeholder="输入研究主题，例如：分析 2026 年 AI Agent 的发展趋势..."
               autocomplete="off">
        <button id="startBtn" onclick="startResearch()">开始研究</button>
      </div>
      <div class="steps-row">
        <label>研究深度：
          <select id="stepsSelect">
            <option value="2">快速 (2步)</option>
            <option value="3">标准 (3步)</option>
            <option value="4" selected>深入 (4步)</option>
            <option value="5">全面 (5步)</option>
          </select>
        </label>
      </div>
    </div>
    <div class="content-area" id="contentArea">
      <div class="empty-state">
        <div class="icon">🔬</div>
        <h2>Research-Agent</h2>
        <p>输入研究主题，AI 将自动规划研究步骤、收集信息、生成专业研究报告。整个过程实时可见。</p>
      </div>
    </div>
  </main>
</div>
<div class="toast" id="toast"></div>

<script>
// ── State ──
let currentReport = null;
let currentPlan = null;
let isResearching = false;
const $topic = document.getElementById('topicInput');
const $btn = document.getElementById('startBtn');
const $steps = document.getElementById('stepsSelect');
const $content = document.getElementById('contentArea');
const $history = document.getElementById('historyList');
const $toast = document.getElementById('toast');

// ── Toast ──
function toast(msg) {
  const t = $toast;
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}

// ── History ──
async function loadHistory() {
  try {
    const r = await fetch('/api/history');
    const d = await r.json();
    if (!d.items || !d.items.length) {
      $history.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2);font-size:13px;">暂无历史记录</div>';
      return;
    }
    $history.innerHTML = d.items.map(item => `
      <div class="history-item" data-id="${item.id}" onclick="viewHistory(${item.id})">
        <div class="topic">${esc(item.topic)}</div>
        <div class="meta">${item.created_at?.slice(0,16) || ''} · ${item.report_length || 0} 字</div>
      </div>
    `).join('');
  } catch(e) { /* ignore */ }
}

async function viewHistory(id) {
  try {
    const r = await fetch('/api/research/' + id);
    const d = await r.json();
    document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
    const el = document.querySelector(`[data-id="${id}"]`);
    if (el) el.classList.add('active');
    currentReport = d.report;
    currentPlan = d.plan;
    $content.innerHTML = `
      <div class="status-msg" style="background:rgba(63,185,80,0.1);color:var(--green);">
        ✓ 已加载历史研究: ${esc(d.topic)}
      </div>
      ${renderPlan(d.plan)}
      <div class="report">${marked.parse(d.report || '')}</div>
    `;
  } catch(e) {
    toast('加载失败');
  }
}

// ── Research ──
function renderPlan(plan) {
  if (!plan || !plan.length) return '';
  return `
    <div class="plan-list" style="margin-bottom:16px;">
      ${plan.map(s => `
        <div class="plan-item">
          <span class="num">${s.step}</span>
          <span>${esc(s.title)}</span>
        </div>
      `).join('')}
    </div>
  `;
}

function renderProgress(p, plan) {
  const phases = ['planning', 'researching', 'writing', 'done'];
  const names = ['📋 制定计划', '🔍 信息收集', '✍️ 撰写报告', '✅ 完成'];
  const currentIdx = phases.indexOf(p);

  let html = '<div class="progress-bar">';
  names.forEach((name, i) => {
    let cls = '';
    if (i < currentIdx) cls = 'done';
    else if (i === currentIdx) cls = 'active';
    html += `<div class="progress-step ${cls}">${name}</div>`;
  });
  html += '</div>';
  return html;
}

async function startResearch() {
  const topic = $topic.value.trim();
  if (topic.length < 3) { toast('请输入至少3个字符的研究主题'); return; }
  if (isResearching) return;

  isResearching = true;
  $btn.disabled = true;
  $btn.textContent = '研究中...';

  const maxSteps = parseInt($steps.value);
  const url = `/api/research/stream?topic=${encodeURIComponent(topic)}&max_steps=${maxSteps}`;

  try {
    const response = await fetch(url);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let currentPhase = 'planning';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));

          if (data.phase === 'planning' || data.phase === 'plan_done') {
            currentPhase = 'planning';
            if (data.plan) currentPlan = data.plan;
            $content.innerHTML = `
              ${renderProgress('planning')}
              <div class="status-msg">
                <div class="spinner"></div> ${esc(data.message)}
              </div>
              ${data.plan ? renderPlan(data.plan) : ''}
            `;
          } else if (data.phase === 'researching' || data.phase === 'step_done') {
            currentPhase = 'researching';
            let planHtml = currentPlan ? renderPlan(currentPlan) : '';
            let stepsInfo = '';
            if (data.step) {
              stepsInfo = `
                <div class="step-findings">
                  <strong>✓ ${esc(data.step.title || '')}</strong>
                  — ${data.step.findings_count || 0} 条发现，${data.step.content_length || 0} 字符
                </div>`;
            }
            $content.innerHTML = `
              ${renderProgress(data.phase === 'step_done' && data.step?.step === data.step?.total_steps ? 'researching' : 'researching')}
              ${planHtml}
              <div class="status-msg">
                <div class="spinner"></div> ${esc(data.message)}
              </div>
              ${stepsInfo}
            `;
          } else if (data.phase === 'writing') {
            currentPhase = 'writing';
            $content.innerHTML = `
              ${renderProgress('writing')}
              ${currentPlan ? renderPlan(currentPlan) : ''}
              <div class="status-msg">
                <div class="spinner"></div> ${esc(data.message)}
              </div>
            `;
          } else if (data.phase === 'done') {
            currentPhase = 'done';
            currentReport = data.result.report;
            $content.innerHTML = `
              ${renderProgress('done')}
              ${renderPlan(data.result.plan || currentPlan)}
              <div class="status-msg" style="background:rgba(63,185,80,0.1);color:var(--green);">
                ✓ 研究完成 — 已保存到数据库
              </div>
              <div class="report">${marked.parse(data.result.report || '')}</div>
            `;
            toast('研究完成！报告已保存');
            loadHistory();
          } else if (data.phase === 'error') {
            $content.innerHTML = `
              <div class="status-msg" style="background:rgba(248,81,73,0.1);color:var(--red);">
                ✗ ${esc(data.message)}
              </div>
            `;
          }
        } catch(e) { /* skip bad JSON lines */ }
      }
    }
  } catch(e) {
    $content.innerHTML = `
      <div class="status-msg" style="background:rgba(248,81,73,0.1);color:var(--red);">
        ✗ 连接失败: ${esc(e.message)}
      </div>
    `;
  } finally {
    isResearching = false;
    $btn.disabled = false;
    $btn.textContent = '开始研究';
  }
}

// ── Utils ──
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// ── Init ──
$topic.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !isResearching) startResearch();
});
loadHistory();
</script>
</body>
</html>
"""
