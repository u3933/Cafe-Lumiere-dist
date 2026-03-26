/**
 * game_popup.js（本編と同一）
 */
(function (window) {
  'use strict';

  let _ro = null;

  function _cleanupGame() { if (_ro) { _ro.disconnect(); _ro = null; } }

  const GamePopup = {
    open(name) {
      _cleanupGame();
      const overlay = document.getElementById('game-overlay');
      const content = document.getElementById('game-content');
      const titleEl = document.getElementById('game-title');
      const TITLES  = { poker: '🃏 ドローポーカー', concentration: '🎴 神経衰弱', reversi: '⚫ リバーシ' };
      const INITS   = { poker: initPoker, concentration: initConcentration, reversi: initReversi };
      titleEl.textContent   = TITLES[name] || name;
      content.innerHTML     = '';
      overlay.style.cssText = 'display:flex; align-items:center; justify-content:center;';
      if (INITS[name]) INITS[name](content);
    },
    close() {
      _cleanupGame();
      document.getElementById('game-overlay').style.cssText = 'display:none;';
    },
  };

  // ============================================================
  // Poker
  // ============================================================
  function initPoker(container) {
    const RANKS = ['2','3','4','5','6','7','8','9','10','J','Q','K','A'];
    const SUITS = ['♠','♥','♦','♣'];
    const VALUES = Object.fromEntries(RANKS.map((r, i) => [r, i + 2]));
    const HAND_NAMES = {
      900: 'ロイヤルフラッシュ 👑', 800: 'ストレートフラッシュ ✨',
      700: 'フォーカード', 600: 'フルハウス', 500: 'フラッシュ',
      400: 'ストレート', 300: 'スリーカード', 200: 'ツーペア', 100: 'ワンペア', 0: 'ハイカード',
    };
    const REASON_LABELS = {
      high_card: 'ハイカード狙い', pair: 'ペアをキープ', two_pair: 'ツーペアをキープ',
      three_of_a_kind: 'スリーカードをキープ', straight_draw: 'ストレートドロー狙い',
      flush_draw: 'フラッシュドロー狙い', full_house: 'フルハウスをキープ',
      four_of_a_kind: 'フォーカードをキープ', keep_all: '交換なし',
    };
    let deck = [], playerHand = [], cpuHand = [], selectedIdx = new Set(), phase = 'idle';
    let cpuPreplan = null;

    function handName(score) {
      const key = [900,800,700,600,500,400,300,200,100,0].find(k => score >= k);
      return HAND_NAMES[key] ?? 'ハイカード';
    }
    function buildDeck() {
      const d = [];
      for (const suit of SUITS) for (const rank of RANKS) d.push({ rank, suit, value: VALUES[rank] });
      return d;
    }
    function shuffle(arr) {
      for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [arr[i], arr[j]] = [arr[j], arr[i]]; }
      return arr;
    }
    function isRed(suit) { return suit === '♥' || suit === '♦'; }

    container.innerHTML = `
      <div class="gm-wrap">
        <div class="gm-left">
          <select id="pk-level" class="gm-select"><option value="easy">Easy</option><option value="normal" selected>Normal</option><option value="hard">Hard</option></select>
          <button class="gm-btn gm-btn-gold" id="pk-deal">開始</button>
          <button class="gm-btn gm-btn-blue" id="pk-exchange" disabled>交換</button>
          <button class="gm-btn gm-btn-red" id="pk-showdown" disabled>勝負する</button>
          <div id="pk-message" class="gm-info">開始を押してください</div>
          <div id="pk-cpu-hand" class="pk-hand-name"></div>
          <div id="pk-cpu-detail" class="pk-detail"></div>
          <div id="pk-player-hand" class="pk-hand-name"></div>
        </div>
        <div class="gm-right">
          <div class="pk-hand-label">CPU</div>
          <div id="pk-cpu-cards" class="pk-cards"></div>
          <div class="pk-hand-label" style="margin-top:4px">あなた</div>
          <div id="pk-player-cards" class="pk-cards"></div>
        </div>
      </div>`;

    document.getElementById('pk-deal').addEventListener('click', startGame);
    document.getElementById('pk-exchange').addEventListener('click', doExchange);
    document.getElementById('pk-showdown').addEventListener('click', () => { selectedIdx.clear(); doExchange(); });

    _ro = new ResizeObserver(() => { if (playerHand.length) renderPlayerCards(); if (cpuHand.length) renderCpuCards(phase === 'showdown'); });
    _ro.observe(container);

    function cardW() { const right = container.querySelector('.gm-right'); const w = right ? right.clientWidth : 220; return Math.max(26, Math.min(52, Math.floor((w - 16) / 5 - 3))); }
    function makeCardEl(card, index, clickable) {
      const cw = cardW(), ch = Math.floor(cw * 1.4), selected = selectedIdx.has(index);
      const div = document.createElement('div');
      div.className = 'pk-card' + (isRed(card.suit) ? ' pk-red' : '') + (selected ? ' pk-selected' : '');
      div.style.cssText = `width:${cw}px;height:${ch}px;font-size:${Math.floor(cw * 0.18)}px`;
      if (clickable) div.addEventListener('click', () => toggleCard(index));
      if (selected) { const b = document.createElement('div'); b.className = 'pk-exchange-badge'; b.textContent = '交換'; div.appendChild(b); }
      const fs = Math.floor(cw * 0.35);
      div.innerHTML += `<div class="pk-corner">${card.rank}<br><span style="font-size:0.75em">${card.suit}</span></div><div class="pk-suit-lg" style="font-size:${fs}px">${card.suit}</div><div class="pk-corner pk-bottom">${card.rank}<br><span style="font-size:0.75em">${card.suit}</span></div>`;
      return div;
    }
    function makeBackEl() { const cw = cardW(), ch = Math.floor(cw * 1.4); const div = document.createElement('div'); div.className = 'pk-card pk-back'; div.style.cssText = `width:${cw}px;height:${ch}px`; return div; }
    function renderPlayerCards() { const c = document.getElementById('pk-player-cards'); if (!c) return; c.innerHTML = ''; playerHand.forEach((card, i) => c.appendChild(makeCardEl(card, i, phase === 'draw'))); }
    function renderCpuCards(reveal) { const c = document.getElementById('pk-cpu-cards'); if (!c) return; c.innerHTML = ''; cpuHand.forEach((card, i) => c.appendChild(reveal ? makeCardEl(card, i, false) : makeBackEl())); }
    function startGame() {
      deck = shuffle(buildDeck()); playerHand = deck.splice(0, 5); cpuHand = deck.splice(0, 5);
      selectedIdx.clear(); phase = 'draw';
      const level = document.getElementById('pk-level').value;
      cpuPreplan = window.GamePoker.selectBestExchange(cpuHand, deck, level);
      if (window.RinComment) RinComment.pokerCpuExchange(cpuPreplan.exchangeCount, cpuPreplan.reason, cpuPreplan.expectedScore);
      document.getElementById('pk-exchange').disabled = false;
      document.getElementById('pk-showdown').disabled = false;
      document.getElementById('pk-deal').textContent  = '再ゲーム';
      document.getElementById('pk-player-hand').textContent = '';
      document.getElementById('pk-cpu-hand').textContent    = '';
      document.getElementById('pk-cpu-detail').textContent  = '';
      document.getElementById('pk-message').textContent = '交換するカードを選んで「交換」、そのまま勝負は「勝負する」';
      renderPlayerCards(); renderCpuCards(false);
      if (window.RinComment) RinComment.send('poker', 'start', {});
    }
    function toggleCard(i) { if (phase !== 'draw') return; selectedIdx.has(i) ? selectedIdx.delete(i) : selectedIdx.add(i); renderPlayerCards(); }
    function doExchange() {
      if (phase !== 'draw') return; phase = 'showdown';
      document.getElementById('pk-exchange').disabled = true; document.getElementById('pk-showdown').disabled = true;
      for (const i of selectedIdx) playerHand[i] = deck.splice(0, 1)[0];
      selectedIdx.clear(); renderPlayerCards();
      const cpuR = cpuPreplan, drawn = deck.splice(0, cpuR.exchangeCount);
      const newCpu = []; let di = 0;
      for (let i = 0; i < 5; i++) newCpu.push(cpuR.keepIndices.includes(i) ? cpuHand[i] : drawn[di++]);
      cpuHand = newCpu; renderCpuCards(true);
      const ps = window.GamePoker.evaluateHand(playerHand), cs = window.GamePoker.evaluateHand(cpuHand);
      document.getElementById('pk-player-hand').textContent = handName(ps);
      document.getElementById('pk-cpu-hand').textContent    = handName(cs);
      const rl = REASON_LABELS[cpuR.reason] ?? cpuR.reason;
      document.getElementById('pk-cpu-detail').textContent = `${rl} / ${cpuR.exchangeCount}枚交換 / EV ${cpuR.expectedScore.toFixed(1)}`;
      let html, outcome;
      if      (ps > cs) { html = '🎉 あなたの勝ち！'; outcome = 'win'; }
      else if (ps < cs) { html = '😢 CPUの勝ち…';    outcome = 'lose'; }
      else              { html = '🤝 引き分け';        outcome = 'draw'; }
      const cls = { win: 'gm-result-win', lose: 'gm-result-lose', draw: 'gm-result-draw' }[outcome];
      document.getElementById('pk-message').innerHTML = `<span class="${cls}">${html}</span>`;
      if (window.RinComment) RinComment.pokerResult(outcome, handName(ps), handName(cs));
    }
  }

  // ============================================================
  // Concentration
  // ============================================================
  function initConcentration(container) {
    const EMOJIS = ['☕','🍰','🎂','🍩','🧁','🍫','🍪','🥐','🍮','🫖','🧇','🍨'];
    let board = [], playerScore = 0, cpuScore = 0;
    let flipped = [], turnPhase = 'player', gamePhase = 'idle', lockInput = false;
    let cpuMemory = null, playerStreak = 0;

    container.innerHTML = `
      <div class="gm-wrap">
        <div class="gm-left">
          <select id="cn-level" class="gm-select"><option value="easy">Easy</option><option value="normal" selected>Normal</option><option value="hard">Hard</option></select>
          <button class="gm-btn gm-btn-gold" id="cn-new">開始</button>
          <div id="cn-scores" class="gm-info">P:0 / C:0</div>
          <div id="cn-message" class="gm-info">開始を押してください</div>
        </div>
        <div class="gm-right"><div id="cn-board" class="cn-board"></div></div>
      </div>`;

    document.getElementById('cn-new').addEventListener('click', newGame);
    _ro = new ResizeObserver(() => { if (gamePhase !== 'idle') renderBoard(); });
    _ro.observe(container);

    function setMsg(t) { const m = document.getElementById('cn-message'); if (m) m.textContent = t; }
    function updateScores() { const s = document.getElementById('cn-scores'); if (s) s.textContent = `P:${playerScore} / C:${cpuScore}`; }
    function newGame() {
      const level = document.getElementById('cn-level').value;
      const vals  = EMOJIS.slice(0, 9);
      const cards = [...vals, ...vals].map(v => ({ status: 'hidden', value: v }));
      for (let i = cards.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [cards[i], cards[j]] = [cards[j], cards[i]]; }
      board = cards; playerScore = 0; cpuScore = 0; flipped = []; turnPhase = 'player'; gamePhase = 'playing'; lockInput = false; playerStreak = 0;
      cpuMemory = new window.GameConcentration.CpuMemory(window.GameConcentration.ACCURACY[level] ?? 0.65);
      updateScores(); setMsg('あなたのターン — カードを2枚めくってください'); renderBoard();
    }
    function cardSize() { const el = document.getElementById('cn-board'); const w = el ? el.clientWidth : 250; return Math.max(22, Math.min(42, Math.floor((w - 18) / 6 - 3))); }
    function renderBoard() {
      const el = document.getElementById('cn-board'); if (!el) return;
      const cs = cardSize(), ch = Math.floor(cs * 1.25);
      el.innerHTML = '';
      board.forEach((card, i) => {
        const div = document.createElement('div');
        div.className = 'cn-card'; div.style.cssText = `width:100%;height:${ch}px;font-size:${Math.floor(cs * 0.42)}px;line-height:${ch}px`;
        if (card.status === 'hidden') {
          div.classList.add('cn-card-back'); div.textContent = '?';
          if (turnPhase === 'player' && !lockInput && gamePhase === 'playing') { div.style.cursor = 'pointer'; div.addEventListener('click', () => onPlayerClick(i)); }
        } else if (card.status === 'revealed') {
          div.classList.add('cn-card-front'); div.textContent = card.value;
        } else {
          div.classList.add('cn-card-matched'); div.textContent = card.value;
        }
        el.appendChild(div);
      });
    }
    function onPlayerClick(i) {
      if (lockInput || turnPhase !== 'player' || gamePhase !== 'playing') return;
      if (board[i].status !== 'hidden' || flipped.includes(i)) return;
      board[i].status = 'revealed'; cpuMemory.memorize(i, board[i].value); flipped.push(i); renderBoard();
      if (flipped.length < 2) return;
      lockInput = true;
      const [a, b] = flipped;
      if (board[a].value === board[b].value) {
        setTimeout(() => {
          board[a].status = 'matched'; board[b].status = 'matched';
          cpuMemory.removeCard(a); cpuMemory.removeCard(b);
          playerScore++; flipped = []; lockInput = false; playerStreak++;
          if (window.RinComment && playerStreak >= 2) RinComment.concentrationPlayerStreak(playerStreak);
          updateScores(); renderBoard(); setMsg('マッチ！もう1回！'); checkGameOver();
        }, 600);
      } else {
        setTimeout(() => {
          board[a].status = 'hidden'; board[b].status = 'hidden'; flipped = []; lockInput = false; turnPhase = 'cpu'; playerStreak = 0;
          renderBoard(); setMsg('ミス… CPUのターン'); setTimeout(doCpuTurn, 800);
        }, 900);
      }
    }
    function doCpuTurn() {
      if (gamePhase !== 'playing') return;
      const level = document.getElementById('cn-level').value;
      const hasConfirmedPair = cpuMemory.findKnownPair(board) !== null;
      const result = window.GameConcentration.selectCards(board, cpuMemory, level);
      if (!result) { turnPhase = 'player'; setMsg('あなたのターン'); renderBoard(); return; }
      const isConfirmedMove = hasConfirmedPair && result.usedMemory;
      if (window.RinComment && isConfirmedMove) RinComment.concentrationCpuConfirmed();
      const { firstIndex, secondIndex } = result;
      board[firstIndex].status = 'revealed'; renderBoard(); setMsg(`CPU: ${board[firstIndex].value} をめくった`);
      setTimeout(() => {
        board[secondIndex].status = 'revealed'; renderBoard(); setMsg(`CPU: ${board[secondIndex].value} をめくった`);
        setTimeout(() => {
          if (board[firstIndex].value === board[secondIndex].value) {
            board[firstIndex].status = 'matched'; board[secondIndex].status = 'matched';
            cpuMemory.removeCard(firstIndex); cpuMemory.removeCard(secondIndex);
            cpuScore++; updateScores(); renderBoard(); setMsg('CPU マッチ！CPUもう1回');
            if (window.RinComment && !isConfirmedMove) RinComment.concentrationCpuMove(true, result.usedMemory, result.confidence);
            checkGameOver();
            if (gamePhase === 'playing') setTimeout(doCpuTurn, 1000);
          } else {
            board[firstIndex].status = 'hidden'; board[secondIndex].status = 'hidden';
            turnPhase = 'player'; renderBoard(); setMsg('CPUミス。あなたのターン');
            if (window.RinComment) RinComment.concentrationCpuMove(false, result.usedMemory, result.confidence);
          }
        }, 900);
      }, 700);
    }
    function checkGameOver() {
      if (board.some(c => c.status !== 'matched')) return;
      gamePhase = 'over';
      const outcome = playerScore > cpuScore ? 'win' : playerScore < cpuScore ? 'lose' : 'draw';
      const labels  = { win: '🎉 あなたの勝ち！', lose: '😢 CPUの勝ち', draw: '🤝 引き分け' };
      setMsg(`${labels[outcome]} (${playerScore} vs ${cpuScore})`);
      if (window.RinComment) RinComment.concentrationResult(outcome);
    }
  }

  // ============================================================
  // Reversi
  // ============================================================
  function initReversi(container) {
    const { ReversiGame, ReversiAI, AI_DEPTH, BLACK, WHITE, EMPTY, BOARD_SIZE } = window.GameReversi;
    let game = null, ai = null, phase = 'idle';
    let flashMap = new Map(), animFrame = null;
    let canvas = null, ctx = null;

    container.innerHTML = `
      <div class="gm-wrap">
        <div class="gm-left">
          <select id="rv-level" class="gm-select"><option value="easy">Easy</option><option value="normal" selected>Normal</option><option value="hard">Hard</option></select>
          <button class="gm-btn gm-btn-gold" id="rv-new">開始</button>
          <div id="rv-status" class="gm-info">黒:2 白:2</div>
          <div id="rv-message" class="gm-info">開始を押してください</div>
        </div>
        <div class="gm-right"><div id="rv-canvas-wrap" class="rv-canvas-wrap"><canvas id="rv-canvas"></canvas></div></div>
      </div>`;

    canvas = document.getElementById('rv-canvas'); ctx = canvas.getContext('2d');
    document.getElementById('rv-new').addEventListener('click', newGame);
    canvas.addEventListener('click', onCanvasClick);
    _ro = new ResizeObserver(() => { if (game) { resizeCanvas(); draw(); } });
    _ro.observe(container);

    function canvasSz() { const right = container.querySelector('.gm-right'); return Math.max(120, Math.min(300, right ? right.clientWidth - 4 : 200)); }
    function resizeCanvas() { const s = canvasSz(); canvas.width = s; canvas.height = s; }
    function cell() { return Math.floor(canvas.width / BOARD_SIZE); }
    function setMsg(t) { const m = document.getElementById('rv-message'); if (m) m.textContent = t; }
    function updateStatus() { if (!game) return; const { black, white } = game.countStones(); const el = document.getElementById('rv-status'); if (el) el.textContent = `黒:${black} 白:${white}`; }
    function newGame() { const level = document.getElementById('rv-level').value; game = new ReversiGame(); ai = new ReversiAI(AI_DEPTH[level]); phase = 'player'; flashMap.clear(); resizeCanvas(); setMsg('あなたのターン（黒）'); updateStatus(); draw(); }
    function onCanvasClick(e) {
      if (!game || phase !== 'player') return;
      const rect = canvas.getBoundingClientRect(), scaleX = canvas.width / rect.width, scaleY = canvas.height / rect.height, sz = cell();
      const col = Math.floor((e.clientX - rect.left) * scaleX / sz), row = Math.floor((e.clientY - rect.top) * scaleY / sz);
      if (row < 0 || row >= BOARD_SIZE || col < 0 || col >= BOARD_SIZE) return;
      if (!game.hasMove(row, col)) return;
      const flipped = game.makeMove(row, col); addFlash([row, col], flipped); updateStatus();
      if (game.checkGameOver()) { endGame(); return; }
      if (game.currentPlayer === WHITE) { phase = 'ai'; setMsg('CPUが考えています…'); draw(); setTimeout(doAiMove, 400); }
      else { setMsg('あなたのターン（黒）'); draw(); }
    }
    function doAiMove() {
      if (!game || phase !== 'ai') return;
      const move = ai.getBestMove(game);
      if (!move) { if (game.checkGameOver()) { endGame(); return; } phase = 'player'; setMsg('あなたのターン（黒）'); draw(); return; }
      const [r, c] = move, flipped = game.makeMove(r, c); addFlash([r, c], flipped); updateStatus();
      if (window.RinComment) { const isCorner = (r === 0 || r === 7) && (c === 0 || c === 7); const { black, white } = game.countStones(); RinComment.reversiCpuMove(r, c, flipped.length, white, black, isCorner); }
      if (game.checkGameOver()) { endGame(); return; }
      phase = 'player'; setMsg('あなたのターン（黒）'); draw();
    }
    function addFlash(placed, flipped) { const until = Date.now() + 500; flashMap.set(`${placed[0]},${placed[1]}`, until); for (const [r, c] of flipped) flashMap.set(`${r},${c}`, until); }
    function endGame() {
      const { black, white } = game.countStones(), outcome = black > white ? 'win' : white > black ? 'lose' : 'draw';
      const labels = { win: '🎉 あなたの勝ち！', lose: '😢 CPUの勝ち…', draw: '🤝 引き分け' };
      phase = 'idle'; setMsg(`${labels[outcome]} (黒${black} vs 白${white})`); draw();
      if (window.RinComment) RinComment.reversiResult(outcome);
    }
    function draw() {
      if (!ctx || !canvas.width) return;
      const sz = cell(), bsz = sz * BOARD_SIZE, now = Date.now();
      ctx.fillStyle = '#2d7a34'; ctx.fillRect(0, 0, bsz, bsz);
      ctx.strokeStyle = 'rgba(0,0,0,0.5)'; ctx.lineWidth = 1;
      for (let i = 0; i <= BOARD_SIZE; i++) { ctx.beginPath(); ctx.moveTo(i * sz, 0); ctx.lineTo(i * sz, bsz); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0, i * sz); ctx.lineTo(bsz, i * sz); ctx.stroke(); }
      if (!game) return;
      if (phase === 'player') { for (const key of game.validMoves) { const [r, c] = key.split(',').map(Number); ctx.fillStyle = 'rgba(255,255,255,0.2)'; ctx.beginPath(); ctx.arc(c * sz + sz / 2, r * sz + sz / 2, sz * 0.14, 0, Math.PI * 2); ctx.fill(); } }
      let needAnim = false;
      for (let r = 0; r < BOARD_SIZE; r++) {
        for (let c = 0; c < BOARD_SIZE; c++) {
          const cellVal = game.board[r][c]; if (cellVal === EMPTY) continue;
          const key = `${r},${c}`, until = flashMap.get(key);
          if (until && now < until) { drawStone(r, c, cellVal, 1 - (until - now) / 500, sz); needAnim = true; }
          else { drawStone(r, c, cellVal, 0, sz); if (until) flashMap.delete(key); }
        }
      }
      if (needAnim) { if (animFrame) cancelAnimationFrame(animFrame); animFrame = requestAnimationFrame(draw); }
    }
    function drawStone(r, c, color, progress, sz) {
      const x = c * sz + sz / 2, y = r * sz + sz / 2, rad = sz * 0.41, t = Math.sin(progress * Math.PI);
      let base, hl;
      if (color === BLACK) { const v = Math.floor(160 * t); base = `rgb(${v},${v},${v})`; hl = `rgba(255,255,255,${0.3 + 0.4 * t})`; }
      else { const v = Math.floor(255 - 80 * t); base = `rgb(${v},${v},${v})`; hl = `rgba(255,255,255,${0.7 - 0.3 * t})`; }
      const g = ctx.createRadialGradient(x - rad * 0.3, y - rad * 0.3, rad * 0.05, x, y, rad);
      g.addColorStop(0, hl); g.addColorStop(1, base);
      ctx.beginPath(); ctx.arc(x, y, rad, 0, Math.PI * 2); ctx.fillStyle = g; ctx.fill();
    }
  }

  window.GamePopup = GamePopup;
})(window);
