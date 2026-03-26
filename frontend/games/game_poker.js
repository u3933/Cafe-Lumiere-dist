/**
 * game_poker.js（本編と同一）
 */
const PokerConfig = { level: "normal", monteCarloSamples: 200 };
const HAND_SCORE = { ROYAL_FLUSH: 900, STRAIGHT_FLUSH: 800, FOUR_OF_A_KIND: 700, FULL_HOUSE: 600, FLUSH: 500, STRAIGHT: 400, THREE_OF_A_KIND: 300, TWO_PAIR: 200, ONE_PAIR: 100, HIGH_CARD: 0 };
function cardLabel(card) { return `${card.rank}${card.suit}`; }
function evaluateHand(cards) {
  if (!cards || cards.length !== 5) return HAND_SCORE.HIGH_CARD;
  const values = cards.map(c => c.value).sort((a, b) => a - b), suits = cards.map(c => c.suit);
  const cnt = {}; for (const v of values) cnt[v] = (cnt[v] || 0) + 1;
  const groups = Object.values(cnt).sort((a, b) => b - a);
  const isFlush = suits.every(s => s === suits[0]);
  const unique = [...new Set(values)];
  const isAceLow = unique.length === 5 && JSON.stringify(unique) === JSON.stringify([2,3,4,5,14]);
  const isNormStr = unique.length === 5 && (unique[4] - unique[0] === 4);
  const isStraight = isNormStr || isAceLow;
  if (isFlush && isNormStr && JSON.stringify(values) === JSON.stringify([10,11,12,13,14])) return HAND_SCORE.ROYAL_FLUSH;
  if (isFlush && isStraight) return HAND_SCORE.STRAIGHT_FLUSH;
  if (groups[0] === 4) return HAND_SCORE.FOUR_OF_A_KIND;
  if (groups[0] === 3 && groups[1] === 2) return HAND_SCORE.FULL_HOUSE;
  if (isFlush) return HAND_SCORE.FLUSH;
  if (isStraight) return HAND_SCORE.STRAIGHT;
  if (groups[0] === 3) return HAND_SCORE.THREE_OF_A_KIND;
  if (groups[0] === 2 && groups[1] === 2) return HAND_SCORE.TWO_PAIR;
  if (groups[0] === 2) return HAND_SCORE.ONE_PAIR;
  return HAND_SCORE.HIGH_CARD;
}
function calcExchangeEV(hand, keepIndices, deckRemaining) {
  const keptCards = keepIndices.map(i => hand[i]), drawCount = 5 - keepIndices.length;
  if (drawCount === 0) return evaluateHand(hand);
  if (deckRemaining.length < drawCount) return evaluateHand(keptCards.concat(deckRemaining).slice(0, 5));
  const n = PokerConfig.monteCarloSamples; let total = 0;
  for (let s = 0; s < n; s++) {
    const deck = [...deckRemaining];
    for (let j = 0; j < drawCount; j++) { const r = j + Math.floor(Math.random() * (deck.length - j)); const tmp = deck[j]; deck[j] = deck[r]; deck[r] = tmp; }
    total += evaluateHand([...keptCards, ...deck.slice(0, drawCount)]);
  }
  return total / n;
}
function _analyzeHand(hand) {
  const values = hand.map(c => c.value), suits = hand.map(c => c.suit);
  const valCnt = {}; for (const v of values) valCnt[v] = (valCnt[v] || 0) + 1;
  const pairs  = Object.entries(valCnt).filter(([,c]) => c === 2).map(([v]) => Number(v));
  const threes = Object.entries(valCnt).filter(([,c]) => c === 3).map(([v]) => Number(v));
  const fours  = Object.entries(valCnt).filter(([,c]) => c === 4).map(([v]) => Number(v));
  const suitCnt = {}; for (const s of suits) suitCnt[s] = (suitCnt[s] || 0) + 1;
  const fdEntry = Object.entries(suitCnt).find(([,c]) => c === 4);
  const flushDrawSuit = fdEntry ? fdEntry[0] : null;
  const unique = [...new Set(values)].sort((a,b) => a-b);
  let straightDrawVals = null;
  for (let i = 0; i <= unique.length - 4; i++) { const sub = unique.slice(i, i+4); const span = sub[3]-sub[0]; if (span === 3 || span === 4) { straightDrawVals = sub; break; } }
  return { pairs, threes, fours, flushDrawSuit, straightDrawVals, valCnt };
}
function _inferReason(hand, keepIndices) {
  if (keepIndices.length === 5) return "keep_all"; if (keepIndices.length === 0) return "high_card";
  const kept = keepIndices.map(i => hand[i]), info = _analyzeHand(kept);
  if (info.fours.length > 0) return "four_of_a_kind";
  if (info.threes.length > 0 && info.pairs.length > 0) return "full_house";
  if (info.threes.length > 0) return "three_of_a_kind";
  if (info.pairs.length >= 2) return "two_pair";
  if (info.pairs.length === 1) return "pair";
  if (kept.length === 4) { const s = kept.map(c => c.suit); if (s.every(x => x === s[0])) return "flush_draw"; const v = kept.map(c => c.value).sort((a,b) => a-b); if (v[3]-v[0] <= 4) return "straight_draw"; }
  return "high_card";
}
function _selectEasy(hand) {
  const info = _analyzeHand(hand), keepVals = new Set();
  if (info.fours.length > 0) info.fours.forEach(v => keepVals.add(v));
  else if (info.threes.length > 0 && info.pairs.length > 0) [...info.threes, ...info.pairs].forEach(v => keepVals.add(v));
  else if (info.threes.length > 0) info.threes.forEach(v => keepVals.add(v));
  else if (info.pairs.length >= 2) info.pairs.forEach(v => keepVals.add(v));
  else if (info.pairs.length === 1) info.pairs.forEach(v => keepVals.add(v));
  const keepIndices = hand.map((c,i) => keepVals.has(c.value) ? i : -1).filter(i => i >= 0);
  let reason = "high_card";
  if (info.fours.length > 0) reason = "four_of_a_kind";
  else if (info.threes.length > 0 && info.pairs.length > 0) reason = "full_house";
  else if (info.threes.length > 0) reason = "three_of_a_kind";
  else if (info.pairs.length >= 2) reason = "two_pair";
  else if (info.pairs.length === 1) reason = "pair";
  return { keepIndices, reason, expectedScore: evaluateHand(hand) };
}
function _selectNormal(hand, deckRemaining) {
  const info = _analyzeHand(hand), candidates = new Map(), currentScore = evaluateHand(hand);
  const add = (indices, reason) => { const key = JSON.stringify([...indices].sort((a,b) => a-b)); if (!candidates.has(key)) candidates.set(key, { keepIndices: [...indices], reason }); };
  if (currentScore >= HAND_SCORE.STRAIGHT) { let reason = "keep_all"; if (currentScore >= HAND_SCORE.FOUR_OF_A_KIND) reason = "four_of_a_kind"; else if (currentScore >= HAND_SCORE.FULL_HOUSE) reason = "full_house"; add([0,1,2,3,4], reason); }
  if (info.fours.length > 0) { const v = info.fours[0]; add(hand.map((c,i) => c.value === v ? i : -1).filter(i => i >= 0), "four_of_a_kind"); }
  if (info.threes.length > 0 && info.pairs.length > 0) add([0,1,2,3,4], "full_house");
  if (info.threes.length > 0) { const v = info.threes[0]; add(hand.map((c,i) => c.value === v ? i : -1).filter(i => i >= 0), "three_of_a_kind"); }
  if (info.pairs.length >= 2) { const pairVals = new Set(info.pairs); add(hand.map((c,i) => pairVals.has(c.value) ? i : -1).filter(i => i >= 0), "two_pair"); }
  if (info.pairs.length >= 1) { const bestPair = Math.max(...info.pairs); add(hand.map((c,i) => c.value === bestPair ? i : -1).filter(i => i >= 0), "pair"); }
  if (info.flushDrawSuit) { const idx = hand.map((c,i) => c.suit === info.flushDrawSuit ? i : -1).filter(i => i >= 0); if (idx.length === 4) add(idx, "flush_draw"); }
  if (info.straightDrawVals) { const drawVals = new Set(info.straightDrawVals); const idx = hand.map((c,i) => drawVals.has(c.value) ? i : -1).filter(i => i >= 0); if (idx.length === 4) add(idx, "straight_draw"); }
  const highIdx = hand.map((c,i) => c.value >= 11 ? i : -1).filter(i => i >= 0).sort((a,b) => hand[b].value - hand[a].value).slice(0, 2);
  if (highIdx.length > 0) add(highIdx, "high_card");
  add([], "high_card");
  let best = null;
  for (const { keepIndices, reason } of candidates.values()) { const ev = calcExchangeEV(hand, keepIndices, deckRemaining); if (!best || ev > best.ev) best = { keepIndices, reason, ev }; }
  return { keepIndices: best.keepIndices, reason: best.reason, expectedScore: best.ev };
}
function _selectHard(hand, deckRemaining) {
  let best = null;
  for (let mask = 0; mask < 32; mask++) { const keepIndices = []; for (let i = 0; i < 5; i++) if (mask & (1 << i)) keepIndices.push(i); const ev = calcExchangeEV(hand, keepIndices, deckRemaining); if (!best || ev > best.ev) best = { keepIndices, ev }; }
  return { keepIndices: best.keepIndices, reason: _inferReason(hand, best.keepIndices), expectedScore: best.ev };
}
function selectBestExchange(hand, deck, level) {
  const lv = level || PokerConfig.level;
  let result;
  if (lv === "hard") result = _selectHard(hand, deck);
  else if (lv === "normal") result = _selectNormal(hand, deck);
  else result = _selectEasy(hand);
  return { keepIndices: result.keepIndices, exchangeCount: 5 - result.keepIndices.length, keptCards: result.keepIndices.map(i => cardLabel(hand[i])), reason: result.reason, expectedScore: result.expectedScore };
}
const GamePoker = { config: PokerConfig, HAND_SCORE, evaluateHand, calcExchangeEV, selectBestExchange };
if (typeof module !== "undefined" && module.exports) module.exports = GamePoker;
else if (typeof window !== "undefined") window.GamePoker = GamePoker;
