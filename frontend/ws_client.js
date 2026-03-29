/**
 * ws_client.js (vA1) - WebSocket受信 / 吹き出し制御 / 音声再生
 *
 * BGM・TTS ともに同一の AudioContext で再生することで
 * iOS のオーディオセッション競合によるダッキング（TTS音量低下）を解消する。
 *
 * 音量設定（config.yaml）:
 *   bgm.volume  : BGM音量（0.0〜1.0）デフォルト 0.3
 *   tts.volume  : TTS音量（0.0〜2.0）デフォルト 1.0（1.0超で増幅可）
 */

const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname}:8765`;

let ws = null;
let wsReady = false;
let reconnectTimer = null;

let _speakerIds = ['chara1', 'chara2'];
const bubbleTimers = {};

window.AppState = {
  speaking: false,
  micState: 'idle',
};

// ============================================================
// AudioContext（BGM・TTS 共通）— 最初に定義
// ============================================================
let audioCtx      = null;
let currentSource = null;

// ---- BGM ----
const BGM_BASE_GAIN  = 2.0;
const BGM_DUCK_RATIO = 0.4;
let _bgmVolume       = 0.3;
let _bgmGain         = null;
let _bgmMediaSource  = null;
let bgmRequested     = false;
let bgmStarted       = false;

// ---- TTS ----
let _ttsVolume = 1.0;

function _bgmEffectiveGain(v) { return Math.min(1.0, v * BGM_BASE_GAIN); }

function _setBgmDucking(duck) {
  if (!_bgmGain) return;
  const ctx = getAudioCtx();
  const now = ctx.currentTime;
  const target = duck
    ? _bgmEffectiveGain(_bgmVolume) * BGM_DUCK_RATIO
    : _bgmEffectiveGain(_bgmVolume);
  _bgmGain.gain.cancelScheduledValues(now);
  _bgmGain.gain.setValueAtTime(_bgmGain.gain.value, now);
  _bgmGain.gain.linearRampToValueAtTime(target, now + 0.3);
}

function getAudioCtx() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  return audioCtx;
}
window.getAudioCtx = getAudioCtx;

function unlockAudioCtx() {
  const ctx = getAudioCtx();
  if (ctx.state === 'suspended') ctx.resume().catch(() => {});
  if (bgmRequested) startBGM();
}
document.addEventListener('click',      unlockAudioCtx, { once: false });
document.addEventListener('touchstart', unlockAudioCtx, { once: false });

window.resumeAudioAfterMic = function () {
  const ctx = getAudioCtx();
  if (ctx.state === 'suspended') ctx.resume().catch(() => {});
  if (bgmRequested && _bgmAudioEl && _bgmAudioEl.paused) _bgmAudioEl.play().catch(() => {});
};

// ============================================================
// BGM
// ============================================================
const _bgmAudioEl = document.getElementById('bgm-audio');

let _bgmSchedules = [
  { file: '/assets/bgm/cafe_bgm_morning.mp3', start: 6  },
  { file: '/assets/bgm/cafe_bgm.mp3',         start: 13 },
  { file: '/assets/bgm/cafe_bgm_night.mp3',   start: 22 },
];

function _getBgmFile() {
  const h = new Date().getHours();
  const sorted = [..._bgmSchedules].sort((a, b) => a.start - b.start);
  let match = sorted.filter(s => s.start <= h).pop();
  if (!match) match = sorted[sorted.length - 1];
  return match ? match.file : '/assets/bgm/cafe_bgm.mp3';
}

function _updateBgmSource() {
  if (!_bgmAudioEl) return;
  const desired = _getBgmFile();
  const currentSrc = _bgmAudioEl.src ? new URL(_bgmAudioEl.src).pathname : '';
  if (currentSrc === desired) return;
  const wasPlaying = !_bgmAudioEl.paused;
  _bgmAudioEl.pause();
  _bgmAudioEl.src = desired;
  _bgmAudioEl.currentTime = 0;
  if (wasPlaying) _bgmAudioEl.play().catch(() => {});
}

function _connectBgmToCtx() {
  if (!_bgmAudioEl || _bgmMediaSource) return;
  try {
    const ctx = getAudioCtx();
    _bgmMediaSource = ctx.createMediaElementSource(_bgmAudioEl);
    _bgmGain = ctx.createGain();
    _bgmGain.gain.value = _bgmEffectiveGain(_bgmVolume);
    _bgmMediaSource.connect(_bgmGain);
    _bgmGain.connect(ctx.destination);
    console.log(`🎵 BGM → AudioContext 接続完了 (gain=${_bgmGain.gain.value.toFixed(2)})`);
  } catch (e) { console.warn('BGM AudioContext 接続エラー:', e); }
}

function startBGM() {
  if (!bgmRequested || !_bgmAudioEl) return;
  _updateBgmSource();
  _connectBgmToCtx();
  _bgmAudioEl.play().then(() => { bgmStarted = true; }).catch(() => {});
}

function stopBGM() {
  bgmRequested = false; bgmStarted = false;
  if (_bgmAudioEl) { _bgmAudioEl.pause(); _bgmAudioEl.currentTime = 0; }
}

if (_bgmAudioEl) {
  _bgmAudioEl.loop = true;
  _bgmAudioEl.volume = 1.0;
}
setInterval(_updateBgmSource, 60 * 1000);

// ============================================================
// /api/config 読み込み（BGM・TTS両方の音量を確実に取得）
// ============================================================
fetch('/api/config').then(r => r.json()).then(cfg => {
  // BGM音量
  if (cfg.bgm?.volume !== undefined) {
    _bgmVolume = cfg.bgm.volume;
    if (_bgmGain) _bgmGain.gain.value = _bgmEffectiveGain(_bgmVolume);
  }
  // TTS音量
  if (cfg.tts?.volume !== undefined) {
    _ttsVolume = cfg.tts.volume;
    console.log(`🔊 TTS音量: ${_ttsVolume}`);
  }
  // BGMスケジュール
  if (Array.isArray(cfg.bgm?.schedules) && cfg.bgm.schedules.length > 0)
    _bgmSchedules = cfg.bgm.schedules.map(s => ({ file: '/' + s.file, start: s.start }));
  // キャラクターID
  if (cfg.characters) _speakerIds = Object.keys(cfg.characters);

  _updateBgmSource();
}).catch(() => { _updateBgmSource(); });

// ============================================================
// TTS 音声再生（GainNode で音量制御）
// ============================================================
async function playAudio(audioB64, durationMs) {
  try {
    if (currentSource) { try { currentSource.stop(); } catch(e) {} currentSource = null; }
    const ctx = getAudioCtx();
    if (ctx.state === 'suspended') await ctx.resume();

    const binary = atob(audioB64);
    const bytes  = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const audioBuffer = await ctx.decodeAudioData(bytes.buffer);

    return new Promise((resolve) => {
      const source  = ctx.createBufferSource();
      const ttsGain = ctx.createGain();
      ttsGain.gain.value = _ttsVolume;
      console.log(`🔊 TTS再生 gain=${_ttsVolume}`);

      source.buffer = audioBuffer;
      source.connect(ttsGain);
      ttsGain.connect(ctx.destination);
      source.start();
      currentSource = source;
      startLipSync(source);
      source.addEventListener('ended', resolve);
    });
  } catch (e) { console.error('音声再生エラー:', e); await sleep(durationMs); }
}

function startLipSync(source) {
  const charaId = _speakerIds[0] || 'chara1';
  let open = true;
  const timer = setInterval(() => {
    if (window.SceneAPI) { SceneAPI.setMouthOpen(charaId, open); open = !open; }
  }, 80);
  source.addEventListener('ended', () => {
    clearInterval(timer);
    if (window.SceneAPI) SceneAPI.setMouthOpen(charaId, false);
  });
}

// ============================================================
// WebSocket
// ============================================================
function connectWS() {
  ws = new WebSocket(WS_URL);
  ws.addEventListener('open', () => { console.log('✅ WS接続完了'); wsReady = true; clearTimeout(reconnectTimer); });
  ws.addEventListener('close', () => { console.log('🔌 WS切断 → 再接続...'); wsReady = false; stopBGM(); reconnectTimer = setTimeout(connectWS, 3000); });
  ws.addEventListener('error', (e) => { console.error('❌ WSエラー:', e); });
  ws.addEventListener('message', (event) => {
    try { handleServerMessage(JSON.parse(event.data)); } catch (e) { console.error('JSON parse error:', e); }
  });
}

function handleServerMessage(data) {
  switch (data.type) {
    case 'speak':         handleSpeak(data); break;
    case 'emotion':       handleEmotion(data); break;
    case 'stop':          handleStop(); break;
    case 'theme_update':  handleThemeUpdate(data); break;
    case 'bgm_play':      bgmRequested = true; startBGM(); break;
    case 'bgm_stop':      stopBGM(); break;
    case 'weather_update':
      if (typeof currentWeather !== 'undefined' && typeof getSceneryKey === 'function') {
        currentWeather = data.weather;
        const newKey = getSceneryKey(currentWeather);
        if (layerState.scenery.key !== newKey) scheduleChange(layerState.scenery, newKey);
      }
      break;
    case 'user_text':
      if (data.text) addChatMessage('user', data.text);
      break;
  }
}

async function handleSpeak(data) {
  const speaker  = data.speaker || 'chara1';
  const summary  = data.summary || data.text || '';
  const emotion  = data.emotion || 'neutral';
  const duration = (data.duration || 2.0) * 1000;

  if (window.SceneAPI) { SceneAPI.setEmotion(speaker, emotion); SceneAPI.setSpeaking(speaker, true); }
  showBubble(speaker, summary, duration);
  addSpeakToChat(speaker, data.text || summary);

  _setBgmDucking(true);
  if (data.audio) { await playAudio(data.audio, duration); } else { await sleep(duration); }
  if (window.SceneAPI) { SceneAPI.setSpeaking(speaker, false); SceneAPI.setMouthOpen(speaker, false); }
  _setBgmDucking(false);

  AppState.speaking = false;
  updateMicState('idle');
}

function handleEmotion(data) {
  if (window.SceneAPI) SceneAPI.setEmotion(data.speaker || 'chara1', data.emotion || 'neutral');
}

function handleStop() {
  for (const id of _speakerIds) {
    if (window.SceneAPI) { SceneAPI.setSpeaking(id, false); SceneAPI.setMouthOpen(id, false); }
  }
  AppState.speaking = false; updateMicState('idle');
}

function handleThemeUpdate(data) {
  const themes = data.themes || [], idx = data.current_index || 0;
  const label = document.getElementById('theme-label');
  if (label && themes[idx]) label.textContent = `☕ ${themes[idx]}`;
}

const _SPEAKER_MAP = { mia: 'chara1', master: 'chara2' };

function showBubble(speaker, text, durationMs) {
  const charaId = _SPEAKER_MAP[speaker] || speaker;
  const el = document.getElementById(`bubble-${charaId}`);
  if (!el) return;
  if (bubbleTimers[speaker]) clearTimeout(bubbleTimers[speaker]);
  el.textContent = text;
  el.classList.add('visible');
  bubbleTimers[speaker] = setTimeout(() => el.classList.remove('visible'), durationMs + 1500);
}

// ============================================================
// マイクボタン状態
// ============================================================
window.updateMicState = function(newState) {
  AppState.micState = newState;
  if (newState === 'idle' && window._processingTimer) {
    clearTimeout(window._processingTimer);
    window._processingTimer = null;
  }
  const btn = document.getElementById('mic-btn'), label = document.getElementById('status-label');
  if (!btn) return;
  btn.className = '';
  switch (newState) {
    case 'idle':       btn.textContent = '🎤'; if (label) label.textContent = 'タップして話す'; AppState.speaking = false; break;
    case 'recording':  btn.classList.add('recording'); btn.textContent = '⏹'; if (label) label.textContent = '録音中 — 再タップで停止'; break;
    case 'processing': btn.classList.add('processing'); btn.textContent = '⟳'; if (label) label.textContent = '処理中...'; break;
    case 'speaking':   btn.classList.add('speaking'); btn.textContent = '🔊'; if (label) label.textContent = '再生中 — タップで割り込み'; AppState.speaking = true; break;
  }
};

// ============================================================
// WS送信
// ============================================================
window.sendVoiceInput = function(audioB64, username) {
  if (!wsReady || !ws) { console.warn('WS未接続'); return false; }
  ws.send(JSON.stringify({ type: 'voice_input', audio: audioB64, username: username || 'user' }));
  return true;
};

window.sendWS = function(data) {
  if (!wsReady || !ws) return false;
  ws.send(JSON.stringify(data));
  return true;
};

// ============================================================
// チャットパネル
// ============================================================
const chatPanel   = document.getElementById('chat-panel');
const chatToggle  = document.getElementById('chat-toggle');
const chatInput   = document.getElementById('chat-input');
const chatSend    = document.getElementById('chat-send');
const chatHistory = document.getElementById('chat-history');
const CHAT_MAX_TURNS = 5;

chatToggle.addEventListener('click', () => {
  const isOpen = chatPanel.classList.toggle('open');
  chatToggle.classList.toggle('active', isOpen);
  if (isOpen) { chatInput.focus(); chatHistory.scrollTop = chatHistory.scrollHeight; }
});

function addChatMessage(role, text) {
  const el = document.createElement('div');
  el.className = `chat-msg ${role}`; el.textContent = text;
  chatHistory.appendChild(el);
  const msgs = chatHistory.querySelectorAll('.chat-msg');
  if (msgs.length > CHAT_MAX_TURNS * 2) msgs[0].remove();
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

function sendChatText() {
  const text = chatInput.value.trim();
  if (!text || !wsReady || !ws) return;
  chatInput.value = '';
  ws.send(JSON.stringify({ type: 'text_input', message: text, username: 'user' }));
}

chatSend.addEventListener('click', sendChatText);
chatInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatText(); } });

function addSpeakToChat(speaker, text) { if (text) addChatMessage(speaker, text); }

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

connectWS();
