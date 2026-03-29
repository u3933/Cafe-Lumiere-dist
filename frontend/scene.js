/**
 * scene.js (vA1 改修版)
 *
 * キャラクター画像・背景画像を /api/config から動的に読み込む。
 * chara1 / chara2 のキャラ名・ファイル名・レイヤーは config.yaml で設定。
 *
 * レイヤー構成（固定）:
 *   Layer 0: scenery_*       風景（天気・時刻帯で自動切替）
 *   Layer 1: bg_indoor       室内背景（固定）
 *   Layer 2: キャラ背景層    layer:2 のキャラ画像
 *   Layer 3: chara2層        layer:3 のキャラ画像（chara2位置）
 *   Layer 4: obj_mid         中景オブジェクト（固定）
 *   Layer 5: chara1層        layer:5 のキャラ画像（chara1位置）
 *   Layer 6: obj_front       前景オブジェクト（固定）
 *   Layer 7: user_*          ユーザー
 *   Layer 8: UI overlay      日付・時刻・タイトル
 */

const BASE_IMAGE = './assets/image/';
const BASE_CHAR  = './assets/character/';

// ============================================================
// 設定（/api/config から読み込み後に上書き）
// ============================================================
let _sceneImages = {
  bg_indoor: 'bg_indoor.png',
  obj_mid:   'obj_mid.png',
  scenery: {
    day:       'scenery_day.png',
    dawn:      'scenery_dawn.png',
    evening:   'scenery_evening.png',
    night:     'scenery_night.png',
    latenight: 'scenery_latenight.png',
    cloudy:    'scenery_cloudy.png',
    rain:      'scenery_rain.png',
  },
};

let _charaCfg = {
  chara1: {
    pool: [
      { file: 'rin_mid_1.png',      layer: 5 },
      { file: 'rin_mid_2.png',      layer: 5 },
      { file: 'rin_mid_3.png',      layer: 5 },
      { file: 'rin_back_clean.png', layer: 2 },
      { file: 'rin_back_rest.png',  layer: 2, condition: 'sunny_daytime' },
    ],
    late_night_pool: [
      { file: 'rin_back_sleep.png', layer: 2 },
    ],
  },
  chara2: {
    pool: [
      { file: 'master_front.png', layer: 3 },
      { file: 'master_back.png',  layer: 3 },
    ],
  },
};

// 左上オーバーレイのタイトル（config.yaml の scene.overlay_title から読み込む）
let _overlayTitle = '☕ Cafe Lumiere';

// ============================================================
// 画像管理
// ============================================================
const IMAGES = {};

function _buildImageList() {
  const list = {};
  const s = _sceneImages.scenery;
  list['scenery_day']       = BASE_IMAGE + s.day;
  list['scenery_dawn']      = BASE_IMAGE + s.dawn;
  list['scenery_evening']   = BASE_IMAGE + s.evening;
  list['scenery_night']     = BASE_IMAGE + s.night;
  list['scenery_latenight'] = BASE_IMAGE + s.latenight;
  list['scenery_cloudy']    = BASE_IMAGE + s.cloudy;
  list['scenery_rain']      = BASE_IMAGE + s.rain;
  list['bg_indoor'] = BASE_IMAGE + _sceneImages.bg_indoor;
  list['obj_mid']   = BASE_IMAGE + _sceneImages.obj_mid;
  list['obj_front'] = BASE_IMAGE + (_sceneImages.obj_front || 'obj_front.png');
  for (const [charaId, cfg] of Object.entries(_charaCfg)) {
    const seen = new Set();
    for (const frame of [...(cfg.pool || []), ...(cfg.late_night_pool || [])]) {
      if (!seen.has(frame.file)) { seen.add(frame.file); list[`${charaId}_${frame.file}`] = BASE_CHAR + frame.file; }
    }
  }
  list['user_1'] = BASE_CHAR + 'user_1.png';
  list['user_2'] = BASE_CHAR + 'user_2.png';
  return list;
}

function loadAllImages(callback) {
  const imageList = _buildImageList();
  const keys = Object.keys(imageList);
  let loaded = 0;
  keys.forEach(key => {
    const img = new Image();
    img.onload  = () => { if (++loaded === keys.length) callback(); };
    img.onerror = () => { if (++loaded === keys.length) callback(); };
    img.src = imageList[key];
    IMAGES[key] = img;
  });
}

// ============================================================
// 時刻帯・天気判定
// ============================================================
let currentWeather = 'sunny';

function getSceneryKey(weather) {
  const h = new Date().getHours();
  if (h >= 23 || h < 4)  return 'scenery_latenight';
  if (h >= 19 && h < 23) return 'scenery_night';
  if (weather === 'rain')   return 'scenery_rain';
  if (weather === 'cloudy') return 'scenery_cloudy';
  if (h >= 4  && h < 6)  return 'scenery_dawn';
  if (h >= 6  && h < 16) return 'scenery_day';
  return 'scenery_evening';
}

function isLateNight() { const h = new Date().getHours(); return (h >= 23 || h < 6); }
function isSunnyDaytime() { const h = new Date().getHours(); return currentWeather === 'sunny' && h >= 11 && h < 19; }

function checkCondition(condition) {
  if (!condition) return true;
  if (condition === 'sunny_daytime') return isSunnyDaytime();
  if (condition === 'late_night')    return isLateNight();
  return true;
}

// ============================================================
// キャラクターのプールを構築
// ============================================================
function buildCharaPool(charaId) {
  const cfg = _charaCfg[charaId];
  if (!cfg) return [];
  if (isLateNight() && cfg.late_night_pool && cfg.late_night_pool.length > 0) {
    return cfg.late_night_pool.map(f => ({ key: `${charaId}_${f.file}`, layer: f.layer }));
  }
  return (cfg.pool || []).filter(f => checkCondition(f.condition)).map(f => ({ key: `${charaId}_${f.file}`, layer: f.layer }));
}

// ============================================================
// レイヤー状態管理
// ============================================================
const layerState = {
  scenery: { key: 'scenery_day', opacity: 1.0, nextKey: null },
  chara1:  { layer: 5, key: '', opacity: 1.0, nextKey: null },
  chara2:  { layer: 3, key: '', opacity: 1.0, nextKey: null },
  user:    { key: 'user_1',      opacity: 1.0, nextKey: null },
};
const FADE_SPEED = 0.03;

function updateFade(sprite) {
  if (sprite.nextKey === null) return;
  if (sprite.opacity > 0) {
    sprite.opacity = Math.max(0, sprite.opacity - FADE_SPEED);
  } else {
    sprite.key = sprite.nextKey;
    if (sprite.nextLayer !== undefined) sprite.layer = sprite.nextLayer;
    sprite.nextKey = null; sprite.nextLayer = undefined; sprite.opacity = 0;
  }
}

function fadeInAll() {
  Object.values(layerState).forEach(s => {
    if (s.nextKey === null && s.opacity < 1.0) s.opacity = Math.min(1.0, s.opacity + FADE_SPEED);
  });
}

function scheduleChange(sprite, newKey, newLayer) {
  sprite.nextKey = newKey;
  if (newLayer !== undefined) sprite.nextLayer = newLayer;
}

// ============================================================
// キャラクター切替タイマー
// ============================================================
const _charaIndex = { chara1: 0, chara2: 0 };

function nextChara(charaId) {
  const pool = buildCharaPool(charaId);
  if (pool.length === 0) return;
  _charaIndex[charaId] = (_charaIndex[charaId] + 1) % pool.length;
  const next = pool[_charaIndex[charaId]];
  scheduleChange(layerState[charaId], next.key, next.layer);
}

function randomInt(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }

const timers = {
  scenery: 3600,
  chara1:  randomInt(1800, 3600),
  chara2:  randomInt(3600, 10800),
  user:    randomInt(2400, 4800),
};

function updateTimers() {
  const sceneryKey = getSceneryKey(currentWeather);
  if (layerState.scenery.key !== sceneryKey && layerState.scenery.nextKey === null) scheduleChange(layerState.scenery, sceneryKey);
  if (--timers.chara1 <= 0) { nextChara('chara1'); timers.chara1 = randomInt(1800, 3600); }
  if (--timers.chara2 <= 0) { nextChara('chara2'); timers.chara2 = randomInt(3600, 10800); }
  if (--timers.user   <= 0) { scheduleChange(layerState.user, layerState.user.key === 'user_1' ? 'user_2' : 'user_1'); timers.user = randomInt(2400, 4800); }
}

// ============================================================
// 描画
// ============================================================
function drawLayer(ctx, sprite) {
  if (!sprite.key || !IMAGES[sprite.key] || !IMAGES[sprite.key].complete || sprite.opacity <= 0) return;
  const c = ctx.canvas;
  ctx.globalAlpha = sprite.opacity;
  ctx.drawImage(IMAGES[sprite.key], 0, 0, c.width, c.height);
}

function drawFixed(ctx, key) {
  ctx.globalAlpha = 1.0;
  if (IMAGES[key]?.complete) ctx.drawImage(IMAGES[key], 0, 0, ctx.canvas.width, ctx.canvas.height);
}

// ============================================================
// 左上オーバーレイ（タイトルは config.yaml の scene.overlay_title から読み込む）
// ============================================================
function drawOverlay(ctx, canvas) {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  const timeStr = `${hh}:${mm}`;
  const weekDays = ['日','月','火','水','木','金','土'];
  const dateStr = `${now.getMonth()+1}/${now.getDate()}(${weekDays[now.getDay()]})`;

  const pad      = canvas.width * 0.015;
  const fontSize = Math.max(14, canvas.height * 0.0336);

  ctx.globalAlpha = 1.0;
  ctx.font = `bold ${fontSize}px 'Hiragino Kaku Gothic ProN', sans-serif`;

  const logoW = ctx.measureText(_overlayTitle).width;
  const restW = ctx.measureText(`  ${dateStr}  ${timeStr}`).width;
  const textW = logoW + restW;

  ctx.fillStyle = 'rgba(0,0,0,0.45)';
  ctx.beginPath();
  ctx.roundRect(pad, pad, textW + pad * 2, fontSize * 1.8, 8);
  ctx.fill();

  const y = pad + fontSize * 1.2;
  ctx.fillStyle = '#d4a87a';
  ctx.fillText(_overlayTitle, pad * 2, y);
  ctx.fillStyle = '#c8c0a0';
  ctx.fillText(`  ${dateStr}  ${timeStr}`, pad * 2 + logoW, y);
}

// ============================================================
// メイン描画ループ
// ============================================================
function drawFrame() {
  const canvas = document.getElementById('scene-canvas');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  drawLayer(ctx, layerState.scenery);
  drawFixed(ctx, 'bg_indoor');
  if (layerState.chara1.layer === 2) drawLayer(ctx, layerState.chara1);
  if (layerState.chara2.layer === 2) drawLayer(ctx, layerState.chara2);
  if (layerState.chara1.layer === 3) drawLayer(ctx, layerState.chara1);
  if (layerState.chara2.layer === 3) drawLayer(ctx, layerState.chara2);
  drawFixed(ctx, 'obj_mid');
  if (layerState.chara1.layer === 5) drawLayer(ctx, layerState.chara1);
  if (layerState.chara2.layer === 5) drawLayer(ctx, layerState.chara2);
  drawFixed(ctx, 'obj_front');
  drawLayer(ctx, layerState.user);
  ctx.globalAlpha = 1.0;
  drawOverlay(ctx, canvas);

  updateTimers();
  updateFade(layerState.scenery);
  updateFade(layerState.chara1);
  updateFade(layerState.chara2);
  updateFade(layerState.user);
  fadeInAll();

  requestAnimationFrame(drawFrame);
}

// ============================================================
// 外部インターフェース
// ============================================================
window.SceneAPI = {
  setMouthOpen(speaker, open) {},
  setEmotion(speaker, emotion) {},
  setSpeaking(speaker, val) {},
};

// ============================================================
// 初期化: /api/config を読んでから起動
// ============================================================
function initScene() {
  const canvas = document.getElementById('scene-canvas');
  canvas.width  = 960;
  canvas.height = 540;

  fetch('/api/config')
    .then(r => r.json())
    .then(cfg => {
      if (cfg.scene_images) _sceneImages  = cfg.scene_images;
      if (cfg.characters)   _charaCfg     = cfg.characters;
      if (cfg.scene?.overlay_title) _overlayTitle = cfg.scene.overlay_title;
    })
    .catch(() => {})
    .finally(() => {
      layerState.scenery.key = getSceneryKey(currentWeather);
      const c1pool = buildCharaPool('chara1');
      if (c1pool.length > 0) { layerState.chara1.key = c1pool[0].key; layerState.chara1.layer = c1pool[0].layer; }
      const c2pool = buildCharaPool('chara2');
      if (c2pool.length > 0) { layerState.chara2.key = c2pool[0].key; layerState.chara2.layer = c2pool[0].layer; }
      loadAllImages(() => { drawFrame(); });
    });
}

document.addEventListener('DOMContentLoaded', initScene);
