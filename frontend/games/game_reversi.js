/**
 * game_reversi.js（本編と同一）
 */
const EMPTY = 0, BLACK = 1, WHITE = 2, BOARD_SIZE = 8;
const AI_DEPTH = { easy: 2, normal: 4, hard: 6 };
const POSITION_WEIGHTS = [
  [100,-20,10,5,5,10,-20,100],[-20,-50,-2,-2,-2,-2,-50,-20],[10,-2,-1,-1,-1,-1,-2,10],
  [5,-2,-1,-1,-1,-1,-2,5],[5,-2,-1,-1,-1,-1,-2,5],[10,-2,-1,-1,-1,-1,-2,10],
  [-20,-50,-2,-2,-2,-2,-50,-20],[100,-20,10,5,5,10,-20,100],
];
const ReversiConfig = { level: 'normal' };

class ReversiGame {
  constructor() {
    this.board = Array.from({ length: BOARD_SIZE }, () => Array(BOARD_SIZE).fill(EMPTY));
    this.currentPlayer = BLACK; this.gameOver = false;
    this.board[3][3] = WHITE; this.board[3][4] = BLACK; this.board[4][3] = BLACK; this.board[4][4] = WHITE;
    this.validMoves = new Set(); this.updateValidMoves();
  }
  getValidMoves(player) {
    const moves = new Set(), opponent = player === BLACK ? WHITE : BLACK;
    for (let row = 0; row < BOARD_SIZE; row++) {
      for (let col = 0; col < BOARD_SIZE; col++) {
        if (this.board[row][col] !== EMPTY) continue;
        outer: for (let dr = -1; dr <= 1; dr++) { for (let dc = -1; dc <= 1; dc++) { if (dr === 0 && dc === 0) continue; if (this._checkDir(row, col, dr, dc, player, opponent)) { moves.add(`${row},${col}`); break outer; } } }
      }
    }
    return moves;
  }
  _checkDir(row, col, dr, dc, player, opponent) {
    let r = row + dr, c = col + dc, foundOpponent = false;
    while (r >= 0 && r < BOARD_SIZE && c >= 0 && c < BOARD_SIZE) {
      if (this.board[r][c] === opponent) { foundOpponent = true; }
      else if (this.board[r][c] === player) { return foundOpponent; }
      else { return false; }
      r += dr; c += dc;
    }
    return false;
  }
  flipStones(row, col, player) {
    const opponent = player === BLACK ? WHITE : BLACK, flipped = [];
    for (let dr = -1; dr <= 1; dr++) {
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;
        let r = row + dr, c = col + dc; const candidates = [];
        while (r >= 0 && r < BOARD_SIZE && c >= 0 && c < BOARD_SIZE) {
          if (this.board[r][c] === opponent) { candidates.push([r,c]); }
          else if (this.board[r][c] === player) { flipped.push(...candidates); break; }
          else { break; }
          r += dr; c += dc;
        }
      }
    }
    for (const [r,c] of flipped) this.board[r][c] = player;
    return flipped;
  }
  makeMove(row, col) { const flipped = this.flipStones(row, col, this.currentPlayer); this.board[row][col] = this.currentPlayer; this.currentPlayer = this.currentPlayer === BLACK ? WHITE : BLACK; this.updateValidMoves(); return flipped; }
  updateValidMoves() { this.validMoves = this.getValidMoves(this.currentPlayer); }
  countStones() { let black = 0, white = 0; for (const row of this.board) for (const cell of row) if (cell === BLACK) black++; else if (cell === WHITE) white++; return { black, white }; }
  checkGameOver() { if (this.validMoves.size === 0) { this.currentPlayer = this.currentPlayer === BLACK ? WHITE : BLACK; this.updateValidMoves(); if (this.validMoves.size === 0) return true; } return false; }
  copy() { const g = Object.create(ReversiGame.prototype); g.board = this.board.map(r => [...r]); g.currentPlayer = this.currentPlayer; g.gameOver = this.gameOver; g.validMoves = new Set(this.validMoves); return g; }
  evaluate(player) { const opponent = player === BLACK ? WHITE : BLACK; let score = 0; for (let row = 0; row < BOARD_SIZE; row++) for (let col = 0; col < BOARD_SIZE; col++) { const w = POSITION_WEIGHTS[row][col]; if (this.board[row][col] === player) score += w; else if (this.board[row][col] === opponent) score -= w; } return score; }
  hasMove(row, col) { return this.validMoves.has(`${row},${col}`); }
}

class ReversiAI {
  constructor(depth) { this.depth = depth ?? AI_DEPTH['normal']; }
  getBestMove(game) {
    const moves = [...game.validMoves]; if (moves.length === 0) return null;
    let bestScore = -Infinity; const bestMoves = [];
    for (const key of moves) { const [r,c] = key.split(',').map(Number); const tmp = game.copy(); tmp.makeMove(r,c); const score = this._minimax(tmp, this.depth-1, -Infinity, Infinity, false); if (score > bestScore) { bestScore = score; bestMoves.length = 0; bestMoves.push([r,c]); } else if (score === bestScore) bestMoves.push([r,c]); }
    return bestMoves[Math.floor(Math.random() * bestMoves.length)] ?? null;
  }
  _minimax(game, depth, alpha, beta, isMaximizing) {
    if (depth === 0 || game.checkGameOver()) return game.evaluate(WHITE);
    const moves = [...game.validMoves];
    if (isMaximizing) { let best = -Infinity; for (const key of moves) { const [r,c] = key.split(',').map(Number); const tmp = game.copy(); tmp.makeMove(r,c); const s = this._minimax(tmp,depth-1,alpha,beta,false); best = Math.max(best,s); alpha = Math.max(alpha,s); if (beta <= alpha) break; } return best; }
    else { let best = Infinity; for (const key of moves) { const [r,c] = key.split(',').map(Number); const tmp = game.copy(); tmp.makeMove(r,c); const s = this._minimax(tmp,depth-1,alpha,beta,true); best = Math.min(best,s); beta = Math.min(beta,s); if (beta <= alpha) break; } return best; }
  }
}

const GameReversi = { config: ReversiConfig, EMPTY, BLACK, WHITE, BOARD_SIZE, AI_DEPTH, POSITION_WEIGHTS, ReversiGame, ReversiAI };
if (typeof module !== 'undefined' && module.exports) module.exports = GameReversi;
else if (typeof window !== 'undefined') window.GameReversi = GameReversi;
