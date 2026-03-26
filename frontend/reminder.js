/**
 * reminder.js - リマインダー機能
 *
 * localStorage にリマインダーを保存し、毎分チェックして通知する。
 * 通知時: チャイム音 + 通知ポップアップ + rin_speak で TTS 発話。
 */

const _RM_KEY  = 'cafe_reminders';
const _RM_MAX  = 5;
const _fired   = new Set(); // 同分内の二重発火防止

// ============================================================
// ストレージ
// ============================================================
function _load() {
  try { return JSON.parse(localStorage.getItem(_RM_KEY)) || []; }
  catch { return []; }
}
function _save(list) {
  localStorage.setItem(_RM_KEY, JSON.stringify(list));
}

// ============================================================
// チャイム音（Web Audio API）
// ============================================================
function _playChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    // C5 → E5 → G5 の3音
    [523.25, 659.25, 783.99].forEach((freq, i) => {
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.value = freq;
      const t = ctx.currentTime + i * 0.35;
      gain.gain.setValueAtTime(0, t);
      gain.gain.linearRampToValueAtTime(0.35, t + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.9);
      osc.start(t);
      osc.stop(t + 0.9);
    });
  } catch (e) {
    console.warn('チャイム再生エラー:', e);
  }
}

// ============================================================
// 通知ポップアップ
// ============================================================
let _notifyTimer = null;

function _showNotify(name) {
  const box  = document.getElementById('rm-notify');
  const text = document.getElementById('rm-notify-name');
  if (!box || !text) return;
  text.textContent = name;
  box.style.display = 'flex';
  clearTimeout(_notifyTimer);
  _notifyTimer = setTimeout(() => _dismissNotify(), 15000); // 15秒で自動消去
}

function _dismissNotify() {
  clearTimeout(_notifyTimer);
  const box = document.getElementById('rm-notify');
  if (box) box.style.display = 'none';
}

// ============================================================
// リマインダー発火
// ============================================================
function _fire(r) {
  _playChime();
  _showNotify(r.name);

  // chara1（Mia）がセリフで通知
  if (typeof sendWS === 'function') {
    sendWS({ type: 'rin_speak', text: `${r.name}の時間だよ！`, emotion: 'happy' });
  }
}

// ============================================================
// 毎分チェック
// ============================================================
function _check() {
  const now   = new Date();
  const hhmm  = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  const today = now.toISOString().slice(0, 10);

  const list = _load();
  let changed = false;

  list.forEach(r => {
    if (!r.enabled || r.time !== hhmm) return;
    const key = `${r.id}-${today}-${hhmm}`;
    if (_fired.has(key)) return;
    _fired.add(key);
    _fire(r);
    if (r.repeat === 'once') {
      r.enabled = false;
      changed = true;
    }
  });

  if (changed) {
    _save(list);
    _renderList();
  }
}

// 起動直後に1回チェック、以降30秒ごと（分跨ぎを確実に拾う）
setTimeout(_check, 3000);
setInterval(_check, 30000);

// ============================================================
// パネルUI
// ============================================================
function _renderList() {
  const container = document.getElementById('rm-list');
  if (!container) return;
  const list = _load();

  if (list.length === 0) {
    container.innerHTML = '<p class="rm-empty">リマインダーなし</p>';
    return;
  }

  container.innerHTML = list.map(r => `
    <div class="rm-item${r.enabled ? '' : ' rm-disabled'}">
      <span class="rm-time">${r.time}</span>
      <span class="rm-name">${_esc(r.name)}</span>
      <span class="rm-repeat">${r.repeat === 'daily' ? '毎日' : '1度のみ'}</span>
      <button class="rm-del" onclick="ReminderPanel.remove('${r.id}')">✕</button>
    </div>
  `).join('');

  // 追加ボタンの表示制御（上限チェック）
  const addBtn = document.getElementById('rm-add-btn');
  if (addBtn) addBtn.disabled = list.filter(r => r.enabled).length >= _RM_MAX;
}

function _esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function _openPanel() {
  _renderList();
  const panel = document.getElementById('rm-overlay');
  if (panel) panel.style.display = 'flex';
}

function _closePanel() {
  const panel = document.getElementById('rm-overlay');
  if (panel) panel.style.display = 'none';
}

function _addReminder() {
  const name   = document.getElementById('rm-input-name')?.value.trim();
  const time   = document.getElementById('rm-input-time')?.value;
  const repeat = document.getElementById('rm-input-repeat')?.value;

  if (!name)  { alert('イベント名を入力してください'); return; }
  if (!time)  { alert('時刻を設定してください'); return; }

  const list = _load();
  if (list.filter(r => r.enabled).length >= _RM_MAX) {
    alert(`リマインダーは最大 ${_RM_MAX} 件までです`);
    return;
  }

  list.push({
    id:     Date.now().toString(36),
    name:   name.slice(0, 20),
    time,
    repeat: repeat || 'daily',
    enabled: true,
  });
  _save(list);

  // 入力欄リセット
  document.getElementById('rm-input-name').value = '';
  _renderList();
}

function _removeReminder(id) {
  const list = _load().filter(r => r.id !== id);
  _save(list);
  _renderList();
}

// ============================================================
// 公開 API
// ============================================================
window.ReminderPanel = {
  open:          _openPanel,
  close:         _closePanel,
  add:           _addReminder,
  remove:        _removeReminder,
  dismissNotify: _dismissNotify,
};
