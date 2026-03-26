/**
 * game_concentration.js（本編と同一）
 */
const ConcentrationConfig = { cardPairs: 9, level: 'normal' };
const ACCURACY = { easy: 0.30, normal: 0.65, hard: 0.95 };

class CpuMemory {
  constructor(accuracy) { this.knownCards = new Map(); this.accuracy = accuracy; }
  memorize(index, cardValue) { if (Math.random() < this.accuracy) this.knownCards.set(index, cardValue); }
  forget(index) { if (this.knownCards.has(index) && Math.random() < (1 - this.accuracy)) this.knownCards.delete(index); }
  findKnownPair(board) {
    const valueMap = new Map();
    for (const [idx, val] of this.knownCards) { if (board && board[idx].status !== 'hidden') continue; if (!valueMap.has(val)) valueMap.set(val, []); valueMap.get(val).push(idx); }
    for (const indices of valueMap.values()) { if (indices.length >= 2) return [indices[0], indices[1]]; }
    return null;
  }
  findPairOf(value, excludeIndex, board) {
    for (const [idx, val] of this.knownCards) { if (idx === excludeIndex) continue; if (val !== value) continue; if (board && board[idx].status !== 'hidden') continue; return idx; }
    return null;
  }
  getKnownButUnpaired(excludeIndex, board) {
    const valueMap = new Map();
    for (const [idx, val] of this.knownCards) { if (idx === excludeIndex) continue; if (board && board[idx].status !== 'hidden') continue; if (!valueMap.has(val)) valueMap.set(val, []); valueMap.get(val).push(idx); }
    const singletons = []; for (const indices of valueMap.values()) { if (indices.length === 1) singletons.push(indices[0]); }
    if (singletons.length === 0) return null;
    return singletons[Math.floor(Math.random() * singletons.length)];
  }
  removeCard(index) { this.knownCards.delete(index); }
  clear() { this.knownCards.clear(); }
}

function selectCards(board, memory, level) {
  const lv = level || ConcentrationConfig.level;
  const hiddenIndices = board.map((c,i) => c.status === 'hidden' ? i : -1).filter(i => i >= 0);
  if (hiddenIndices.length < 2) return null;
  const pickRandom = (arr) => arr[Math.floor(Math.random() * arr.length)];
  let firstIndex, usedMemoryFirst = false, confirmedSecond = null;
  const knownPair = memory.findKnownPair(board);
  if (knownPair) { firstIndex = knownPair[0]; confirmedSecond = knownPair[1]; usedMemoryFirst = true; }
  else { firstIndex = pickRandom(hiddenIndices); }
  const firstValue = board[firstIndex].value;
  memory.memorize(firstIndex, firstValue);
  if (lv === 'easy') memory.forget(firstIndex);
  const remaining = hiddenIndices.filter(i => i !== firstIndex);
  let secondIndex, usedMemorySecond = false;
  if (confirmedSecond !== null && remaining.includes(confirmedSecond)) { secondIndex = confirmedSecond; usedMemorySecond = true; }
  else {
    const pairIdx = memory.findPairOf(firstValue, firstIndex, board);
    if (pairIdx !== null && remaining.includes(pairIdx)) { secondIndex = pairIdx; usedMemorySecond = true; }
    else { const hint = memory.getKnownButUnpaired(firstIndex, board); secondIndex = (hint !== null && remaining.includes(hint)) ? hint : pickRandom(remaining); }
  }
  memory.memorize(secondIndex, board[secondIndex].value);
  if (lv === 'easy') memory.forget(secondIndex);
  const usedMemory = usedMemoryFirst || usedMemorySecond;
  let confidence;
  if (confirmedSecond !== null || (usedMemoryFirst && usedMemorySecond)) confidence = 'high';
  else if (usedMemory) confidence = 'medium';
  else confidence = 'low';
  return { firstIndex, secondIndex, usedMemory, confidence };
}

const GameConcentration = { config: ConcentrationConfig, ACCURACY, CpuMemory, selectCards };
if (typeof module !== 'undefined' && module.exports) module.exports = GameConcentration;
else if (typeof window !== 'undefined') window.GameConcentration = GameConcentration;
