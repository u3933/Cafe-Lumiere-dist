"""
MemoryServer - 記憶管理 Web ツール (FastAPI / port 8767, 本編と同一)
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cafe Lumiere - 記憶管理</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: sans-serif; background: #1a0f0a; color: #d4a87a; min-height: 100vh; }
  header { background: #2d1a0e; padding: 14px 24px; border-bottom: 1px solid #5c3a1e; }
  header h1 { font-size: 1.2rem; }
  .tabs { display: flex; gap: 0; border-bottom: 1px solid #5c3a1e; background: #2d1a0e; }
  .tab { padding: 10px 24px; cursor: pointer; font-size: 0.9rem; border-bottom: 3px solid transparent; }
  .tab.active { border-bottom-color: #c8903a; color: #f0c060; }
  .panel { display: none; padding: 20px; }
  .panel.active { display: block; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { background: #2d1a0e; padding: 8px 10px; text-align: left; border-bottom: 1px solid #5c3a1e; }
  td { padding: 7px 10px; border-bottom: 1px solid #3a2010; vertical-align: top; }
  tr:hover td { background: #251408; }
  tr.deleted td { opacity: 0.45; }
  .badge { display: inline-block; padding: 2px 7px; border-radius: 10px; font-size: 0.72rem; font-weight: bold; }
  .badge-preference { background: #3a5c2e; color: #8fd870; }
  .badge-fact       { background: #2e3a5c; color: #70a8d8; }
  .badge-topic      { background: #5c4a2e; color: #d8b870; }
  .badge-event      { background: #5c2e3a; color: #d87090; }
  .btn { padding: 4px 10px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.78rem; }
  .btn-del  { background: #7a2020; color: #fff; }
  .btn-rest { background: #3a6030; color: #fff; }
  .btn-save { background: #c8903a; color: #fff; }
  .add-form { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
  .add-form select, .add-form input { background: #2d1a0e; color: #d4a87a; border: 1px solid #5c3a1e; border-radius: 4px; padding: 6px 10px; font-size: 0.85rem; }
  .add-form input { flex: 1; min-width: 240px; }
  .filter-bar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
  .filter-bar select { background: #2d1a0e; color: #d4a87a; border: 1px solid #5c3a1e; border-radius: 4px; padding: 5px 8px; font-size: 0.82rem; }
  .editable { cursor: text; }
  .editable:focus { outline: 1px solid #c8903a; background: #251408; }
  .conf { font-size: 0.75rem; color: #888; }
  .log-entry { font-size: 0.82rem; padding: 4px 0; border-bottom: 1px solid #3a2010; }
  .log-entry .sp { font-weight: bold; min-width: 60px; display: inline-block; }
  .sp-user   { color: #70a8d8; }
  .sp-mia    { color: #d87090; }
  .sp-master { color: #8fd870; }
  .visit-row td { cursor: pointer; }
  #log-container { margin-top: 12px; max-height: 320px; overflow-y: auto; background: #200e06; padding: 10px; border-radius: 6px; }
</style>
</head>
<body>
<header><h1>☕ Cafe Lumiere — 記憶管理</h1></header>
<div class="tabs">
  <div class="tab active" onclick="showTab('memories')">記憶一覧</div>
  <div class="tab" onclick="showTab('visits')">来訪履歴</div>
</div>
<div id="tab-memories" class="panel active">
  <div class="add-form">
    <select id="add-cat">
      <option value="preference">preference</option>
      <option value="fact">fact</option>
      <option value="topic">topic</option>
      <option value="event">event</option>
    </select>
    <input id="add-content" type="text" placeholder="記憶の内容を入力...">
    <button class="btn btn-save" onclick="addMemory()">追加</button>
  </div>
  <div class="filter-bar">
    <label>カテゴリ:</label>
    <select onchange="filterCat(this.value)">
      <option value="">すべて</option>
      <option value="preference">preference</option>
      <option value="fact">fact</option>
      <option value="topic">topic</option>
      <option value="event">event</option>
    </select>
  </div>
  <table>
    <thead><tr><th>カテゴリ</th><th>内容</th><th>信頼度</th><th>作成日</th><th>操作</th></tr></thead>
    <tbody id="mem-body"></tbody>
  </table>
</div>
<div id="tab-visits" class="panel">
  <table>
    <thead><tr><th>来訪日時</th><th>滞在(分)</th><th>発言数</th><th>ログ</th></tr></thead>
    <tbody id="visit-body"></tbody>
  </table>
  <div id="log-container" style="display:none">
    <div id="log-title" style="margin-bottom:8px;font-weight:bold;"></div>
    <div id="log-entries"></div>
  </div>
</div>
<script>
let allMemories = [], currentCat = '';
function showTab(name) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', ['memories','visits'][i]===name));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  if (name === 'memories') loadMemories();
  if (name === 'visits') loadVisits();
}
async function loadMemories() { const res = await fetch('/api/memories'); allMemories = await res.json(); renderMemories(); }
function filterCat(val) { currentCat = val; renderMemories(); }
function renderMemories() {
  const rows = allMemories.filter(m => !currentCat || m.category === currentCat);
  document.getElementById('mem-body').innerHTML = rows.map(m => `
    <tr class="${m.is_active ? '' : 'deleted'}" data-id="${m.id}">
      <td><span class="badge badge-${m.category}">${m.category}</span></td>
      <td><span class="editable" contenteditable="true" onblur="saveContent(${m.id}, this)">${m.content}</span></td>
      <td><span class="conf">${m.confidence.toFixed(1)}</span></td>
      <td style="font-size:0.75rem;color:#888">${m.created_at ? m.created_at.slice(0,16) : ''}</td>
      <td>${m.is_active
        ? `<button class="btn btn-del" onclick="delMem(${m.id})">削除</button>`
        : `<button class="btn btn-rest" onclick="restMem(${m.id})">復元</button>`}</td>
    </tr>`).join('');
}
async function saveContent(id, el) {
  const row = allMemories.find(m => m.id === id);
  if (!row) return;
  await fetch(`/api/memories/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({content: el.innerText.trim(), category: row.category}) });
  loadMemories();
}
async function delMem(id) { await fetch(`/api/memories/${id}`, {method:'DELETE'}); loadMemories(); }
async function restMem(id) { await fetch(`/api/memories/${id}/restore`, {method:'POST'}); loadMemories(); }
async function addMemory() {
  const cat = document.getElementById('add-cat').value;
  const content = document.getElementById('add-content').value.trim();
  if (!content) return;
  await fetch('/api/memories', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({category: cat, content}) });
  document.getElementById('add-content').value = '';
  loadMemories();
}
async function loadVisits() {
  const visits = await (await fetch('/api/visits')).json();
  document.getElementById('visit-body').innerHTML = visits.map(v => `
    <tr class="visit-row" onclick="loadLog(${v.id}, '${v.visited_at}')">
      <td>${v.visited_at ? v.visited_at.slice(0,16) : ''}</td>
      <td>${v.duration_min}</td><td>${v.message_count}</td>
      <td style="font-size:0.75rem;color:#888">クリックでログ展開</td>
    </tr>`).join('');
}
async function loadLog(visitId, date) {
  const logs = await (await fetch(`/api/visits/${visitId}/log`)).json();
  document.getElementById('log-title').textContent = `来訪ログ: ${date.slice(0,16)}`;
  document.getElementById('log-entries').innerHTML = logs.map(l =>
    `<div class="log-entry"><span class="sp sp-${l.speaker}">${l.speaker}</span>${l.message}</div>`
  ).join('') || '<div style="color:#888">ログなし</div>';
  document.getElementById('log-container').style.display = 'block';
}
loadMemories();
</script>
</body>
</html>"""


class MemoryServer:

    def __init__(self, config: dict, memory_manager):
        self._port = config.get("memory_server", {}).get("port", 8767)
        self._mm   = memory_manager
        self._server = None

    async def run(self):
        try:
            from fastapi import FastAPI
            from fastapi.responses import HTMLResponse, JSONResponse
            from fastapi.middleware.cors import CORSMiddleware
            import uvicorn
        except ImportError:
            logger.error("❌ FastAPI / uvicorn が未インストールです: pip install fastapi uvicorn")
            return

        app = FastAPI()
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
        mm = self._mm

        @app.get("/", response_class=HTMLResponse)
        async def index(): return _HTML

        @app.get("/api/memories")
        async def get_memories(): return JSONResponse(mm.get_all_memories())

        @app.post("/api/memories")
        async def add_memory(body: dict):
            mm.add_memory_manual(body.get("category", "fact"), body.get("content", ""))
            return {"ok": True}

        @app.put("/api/memories/{memory_id}")
        async def update_memory(memory_id: int, body: dict):
            mm.update_memory(memory_id, body.get("content", ""), body.get("category", "fact"))
            return {"ok": True}

        @app.delete("/api/memories/{memory_id}")
        async def delete_memory(memory_id: int):
            mm.delete_memory(memory_id)
            return {"ok": True}

        @app.post("/api/memories/{memory_id}/restore")
        async def restore_memory(memory_id: int):
            mm.restore_memory(memory_id)
            return {"ok": True}

        @app.get("/api/visits")
        async def get_visits(): return JSONResponse(mm.get_visits())

        @app.get("/api/visits/{visit_id}/log")
        async def get_log(visit_id: int): return JSONResponse(mm.get_conversation_log(visit_id))

        config_uv = uvicorn.Config(app, host="0.0.0.0", port=self._port, log_level="warning", loop="asyncio")
        self._server = uvicorn.Server(config_uv)
        logger.info(f"🌐 MemoryServer 起動: http://0.0.0.0:{self._port}/")
        await self._server.serve()

    def stop(self):
        if self._server:
            self._server.should_exit = True
