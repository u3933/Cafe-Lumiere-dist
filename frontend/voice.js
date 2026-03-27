/**
 * voice.js (vA1) - マイクボタン制御
 *
 * stt.provider に応じて動作を切り替え:
 *   browser → Web Speech API（ブラウザ内蔵STT）
 *   whisper → MediaRecorder + base64送信（本編互換）
 */

const USERNAME = 'user';
const MAX_RECORD_MS       = 8000;
const SILENCE_THRESHOLD   = 0.01;
const SILENCE_DURATION_MS = 1500;
const PROCESSING_TIMEOUT_MS = 12000; // STT/LLM 無応答時に processing を解除するタイムアウト

let mediaRecorder    = null;
let silenceCtx       = null; // 録音間で使い回す（close しないことで iOS マイク再許可を防ぐ）
let silenceSource    = null; // 毎回 disconnect して差し替える
let audioChunks      = [];
let recordTimer      = null;
let silenceCheckTimer = null;
let analyser         = null;
let micStream        = null;

// Web Speech API の recognition インスタンスをスコープ外に保持（abort用）
let _recognition = null;

// STTプロバイダー（/api/config から取得）
let sttProvider = 'browser';
let sttLanguage = 'ja-JP';

// 設定取得
fetch('/api/config').then(r => r.json()).then(cfg => {
  sttProvider = cfg.stt?.provider || 'browser';
  sttLanguage = cfg.stt?.language || 'ja-JP';
}).catch(() => {});

const micBtn = document.getElementById('mic-btn');

// ============================================================
// マイクボタン クリックハンドラ
// ============================================================
micBtn.addEventListener('click', async () => {
  const state = window.AppState?.micState || 'idle';

  if (state === 'idle' || state === 'speaking') {
    if (state === 'speaking') stopCurrentAudio();

    if (sttProvider === 'browser') {
      await startRecordingBrowser();
    } else {
      await startRecording();
    }
  } else if (state === 'recording') {
    // browser / whisper 両モード共通で録音中タップ → 強制停止
    if (sttProvider === 'browser') {
      stopRecordingBrowser();
    } else {
      stopRecording();
    }
  }
  // processing 中はタップ無効
});

// ============================================================
// Web Speech API（browserモード）
// ============================================================
async function startRecordingBrowser() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    alert('このブラウザはWeb Speech APIに対応していません。\nChromeをお使いください。');
    return;
  }

  // 前回のインスタンスが残っていたら中断
  if (_recognition) {
    try { _recognition.abort(); } catch(e) {}
    _recognition = null;
  }

  const recognition = new SR();
  _recognition = recognition;

  recognition.lang             = sttLanguage;
  recognition.interimResults   = false;
  recognition.maxAlternatives  = 1;

  window.updateMicState('recording');

  recognition.onresult = (e) => {
    _recognition = null;
    const text = e.results[0][0].transcript.trim();
    if (text) {
      window.sendWS({ type: 'text_input', message: text, username: USERNAME });
      window.updateMicState('processing');
      // processingタイムアウト
      clearTimeout(window._processingTimer);
      window._processingTimer = setTimeout(() => {
        if ((window.AppState?.micState || '') === 'processing') {
          console.warn('⏱ processing タイムアウト → idle に復帰');
          window.updateMicState('idle');
          if (window.resumeAudioAfterMic) window.resumeAudioAfterMic();
        }
      }, PROCESSING_TIMEOUT_MS);
    } else {
      window.updateMicState('idle');
    }
  };

  recognition.onerror = (e) => {
    console.warn('Web Speech API エラー:', e.error);
    _recognition = null;
    // aborted は手動停止なので無視。それ以外は必ずidleに戻す
    if (e.error !== 'aborted') {
      window.updateMicState('idle');
    }
  };

  recognition.onend = () => {
    _recognition = null;
    // recording のままなら（onresult/onerror が来なかった場合）強制復帰
    if (window.AppState?.micState === 'recording') {
      console.warn('recognition.onend: recording のまま終了 → idle に復帰');
      window.updateMicState('idle');
    }
  };

  try {
    recognition.start();
  } catch (e) {
    console.error('SpeechRecognition start error:', e);
    _recognition = null;
    window.updateMicState('idle');
  }
}

// Web Speech API の手動停止
function stopRecordingBrowser() {
  if (_recognition) {
    try { _recognition.abort(); } catch(e) {}
    _recognition = null;
  }
  window.updateMicState('idle');
}

// ============================================================
// MediaRecorder（whisperモード）
// ============================================================
async function startRecording() {
  try {
    // echoCancellation 等を無効化することで iOS の VoiceChat モードへの遷移を抑制し
    // 他音声（BGM・TTS）へのダッキング（音量低下）を防ぐ
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation:  false,
        noiseSuppression:  false,
        autoGainControl:   false,
      },
      video: false,
    });
  } catch (e) {
    alert('マイクへのアクセスが拒否されました。\nブラウザの設定を確認してください。');
    return;
  }

  // 無音検出専用 AudioContext（TTS 用とは分離・close せず使い回す）
  if (!silenceCtx || silenceCtx.state === 'closed') {
    silenceCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (silenceCtx.state === 'suspended') {
    await silenceCtx.resume().catch(() => {});
  }
  // 前回の source を切断してから新しいストリームを接続
  if (silenceSource) {
    try { silenceSource.disconnect(); } catch(e) {}
    silenceSource = null;
  }
  silenceSource = silenceCtx.createMediaStreamSource(micStream);
  analyser = silenceCtx.createAnalyser();
  analyser.fftSize = 256;
  silenceSource.connect(analyser);

  audioChunks  = [];
  mediaRecorder = new MediaRecorder(micStream, { mimeType: getSupportedMimeType() });

  mediaRecorder.addEventListener('dataavailable', (e) => { if (e.data.size > 0) audioChunks.push(e.data); });

  mediaRecorder.addEventListener('stop', async () => {
    clearTimers();
    window.updateMicState('processing');

    const blob   = new Blob(audioChunks, { type: getSupportedMimeType() });
    const wavB64 = await blobToBase64(blob);
    const sent   = window.sendVoiceInput(wavB64, USERNAME);

    if (!sent) {
      console.warn('WS送信失敗');
      window.updateMicState('idle');
    } else {
      // STT空テキスト等でサーバーが無応答の場合に備えてタイムアウトで強制復帰
      clearTimeout(window._processingTimer);
      window._processingTimer = setTimeout(() => {
        if ((window.AppState?.micState || '') === 'processing') {
          console.warn('⏱ processing タイムアウト → idle に復帰');
          window.updateMicState('idle');
          if (window.resumeAudioAfterMic) window.resumeAudioAfterMic();
        }
      }, PROCESSING_TIMEOUT_MS);
    }

    // マイクストリーム解放
    micStream.getTracks().forEach(t => t.stop());
    micStream = null;

    // source を切断し silenceCtx を suspend（close しないので再許可不要）
    if (silenceSource) {
      try { silenceSource.disconnect(); } catch(e) {}
      silenceSource = null;
    }
    analyser = null;
    if (silenceCtx && silenceCtx.state === 'running') {
      silenceCtx.suspend().catch(() => {});
    }

    // iOS はマイク終了後すぐにオーディオセッションが戻らないため少し待ってから復帰
    // 無音バッファを再生して AudioContext にプレイバックモードへの切り替えを強制する
    setTimeout(() => {
      if (window.resumeAudioAfterMic) window.resumeAudioAfterMic();
      _playSilentBuffer();
    }, 300);
    setTimeout(() => {
      if (window.resumeAudioAfterMic) window.resumeAudioAfterMic();
    }, 800);
  });

  mediaRecorder.start(100);
  window.updateMicState('recording');
  recordTimer = setTimeout(() => stopRecording(), MAX_RECORD_MS);
  startSilenceDetection();
}

function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state === 'inactive') return;
  clearTimers();
  mediaRecorder.stop();
}

function startSilenceDetection() {
  if (!analyser) return;
  let silentMs = 0;
  const bufLen = analyser.frequencyBinCount;
  const buf    = new Uint8Array(bufLen);
  const CHECK_INTERVAL = 100;
  silenceCheckTimer = setInterval(() => {
    if (!analyser) return;
    analyser.getByteTimeDomainData(buf);
    let sum = 0;
    for (let i = 0; i < bufLen; i++) { const v = (buf[i] - 128) / 128; sum += v * v; }
    const rms = Math.sqrt(sum / bufLen);
    if (rms < SILENCE_THRESHOLD) {
      silentMs += CHECK_INTERVAL;
      if (silentMs >= SILENCE_DURATION_MS) { console.log('🔇 無音検出 → 自動停止'); stopRecording(); }
    } else { silentMs = 0; }
  }, CHECK_INTERVAL);
}

// ============================================================
// 無音バッファ再生（iOS ダッキング解除 / プレイバックモード復帰）
// ============================================================
function _playSilentBuffer() {
  try {
    const ctx = window.getAudioCtx ? window.getAudioCtx()
                : new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended') ctx.resume().catch(() => {});
    const buf = ctx.createBuffer(1, ctx.sampleRate * 0.05, ctx.sampleRate); // 50ms 無音
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(ctx.destination);
    src.start();
  } catch(e) {}
}

// ============================================================
// 共通
// ============================================================
function stopCurrentAudio() {
  if (window.currentSource) { try { window.currentSource.stop(); } catch(e) {} window.currentSource = null; }
}

function clearTimers() {
  clearTimeout(recordTimer);
  clearInterval(silenceCheckTimer);
  recordTimer = silenceCheckTimer = null;
}

function getSupportedMimeType() {
  const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
  for (const t of types) { if (MediaRecorder.isTypeSupported(t)) return t; }
  return '';
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => { resolve(reader.result.split(',')[1]); };
    reader.onerror  = reject;
    reader.readAsDataURL(blob);
  });
}
