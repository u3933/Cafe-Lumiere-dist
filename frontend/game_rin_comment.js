/**
 * game_rin_comment.js（本編と同一）
 */
(function (window) {
  'use strict';

  const LINES = {
    reversi: {
      corner:    [['かど、もらった！','happy'],['ふふ、ここかどだよ','happy'],['かど取れた！ラッキー','happy']],
      big_flip:  [['わあ、いっぱいひっくり返せた！','happy'],['えい！　ごっそりいただき','happy'],['一気にひっくり返っちゃった','happy']],
      losing:    [['うー、まだ諦めないよ','sad'],['ちょっとまずいかも…','sad'],['負けてる…でもここから！','sad']],
      leading:   [['リードしてるけど油断しないよ','relaxed'],['このまま行けるかな','relaxed'],['まだまだ気を抜かないで','neutral']],
      normal:    [['ここにしよっと','neutral'],['んー、こっちかな','neutral'],['よし、ここ','neutral'],['このへんかな','neutral']],
    },
    poker: {
      keep_all:        [['全部キープ！　いい手が来てるよ','happy'],['交換なし。これで行く！','happy'],['このまま勝負','relaxed']],
      big_exchange:    [['思い切って替えちゃえ！','surprised'],['えいっ、全部入れ替え！','surprised'],['イチかバチか！','surprised']],
      normal_exchange: [['少し替えてみようかな','neutral'],['ここ、替えとく','neutral'],['んーこっちをキープして','neutral']],
      win:  [['やった、勝っちゃった…ごめんね？','happy'],['勝ったよ。次はもっと強くなってね','relaxed'],['えへへ、勝ち','happy']],
      lose: [['うわ、負けた…悔しい！','sad'],['強いじゃん、やられた','sad'],['くっ…次は負けないよ','sad']],
      draw: [['引き分け？　すごい偶然','surprised'],['まさかの引き分けだ','surprised'],['おんなじ手だったんだ','surprised']],
    },
    concentration_result: {
      win:  [['負けちゃった…　強かったね','sad'],['くやしい！　次は負けないよ','sad'],['うー、やられた','sad']],
      lose: [['やった、勝てた！　ありがとう','happy'],['えへへ、勝ち！','happy'],['わたしの勝ちだよ。次は頑張ってね','relaxed']],
      draw: [['引き分けだ、すごい！','surprised'],['おんなじ枚数？　びっくり','surprised']],
    },
    reversi_result: {
      win:  [['負けた…。次は絶対勝つ','sad'],['くっ、やられた。強いね','sad'],['うー、悔しい！','sad']],
      lose: [['わたしの勝ちだよ。強くなってね','relaxed'],['やった、勝てた！','happy'],['えへへ、勝ったよ','happy']],
      draw: [['引き分け！　すごい','surprised'],['まさかの同点だ','surprised']],
    },
    concentration_player_streak: {
      2:    [['え、また当たった！','surprised'],['すごい、連続！','surprised'],['2連続じゃん！','surprised']],
      3:    [['3連続！？　うそ…','surprised'],['え、止まらないじゃん','surprised'],['すごすぎ、3連続だよ','surprised']],
      many: [['もうほとんど覚えてるの！？','surprised'],['えー、全部わかるの…？','surprised'],['記憶力おばけだ…','surprised']],
    },
    concentration: {
      confirmed:    [['そのカード、いただきです！','happy'],['覚えてたよ、もらったー！','happy'],['ふふ、バッチリ記憶してた','happy'],['ちゃんと見てたもん！','happy']],
      high_match:   [['確信してたやつ、当たった！','happy'],['ここだと思ってたんだ','relaxed'],['やっぱり合ってた！','happy']],
      memory_match: [['なんとなく覚えてて良かった','relaxed'],['ぼんやり覚えてたの、合ってた','relaxed'],['あー、そこにあったか！','happy']],
      lucky_match:  [['えへへ、なんか当たっちゃった！','happy'],['ラッキー！','happy'],['まぐれだけど嬉しい','happy']],
      high_miss:    [['え、違った！？　絶対ここだと思ったのに','surprised'],['あれ、おかしいな…','surprised'],['確かここだったはず…','surprised']],
      memory_miss:  [['あれ、覚えてたのに外れた…','sad'],['記憶違いだったかな','sad'],['あーん、思い違いだった','sad']],
      random_miss:  [['あーあ、外れた','sad'],['残念…','sad'],['うー、違った','sad']],
    },
  };

  function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

  const RinComment = {
    send(game, event, detail = {}) { if (typeof window.sendWS !== 'function') return; window.sendWS({ type: 'game_comment', game, event, detail }); },
    _speak(text, emotion = 'neutral') { if (typeof window.sendWS !== 'function') return; window.sendWS({ type: 'rin_speak', text, emotion }); },
    reversiCpuMove(row, col, flipped, myScore, oppScore, isCorner = false) {
      let bucket;
      if (isCorner) bucket = LINES.reversi.corner;
      else if (flipped >= 5) bucket = LINES.reversi.big_flip;
      else if (myScore < oppScore) bucket = LINES.reversi.losing;
      else if (myScore > oppScore + 10) bucket = LINES.reversi.leading;
      else bucket = LINES.reversi.normal;
      const [text, emotion] = pick(bucket); this._speak(text, emotion);
    },
    pokerCpuExchange(exchangeCount, reason, expectedScore) {
      let bucket;
      if (exchangeCount === 0) bucket = LINES.poker.keep_all;
      else if (exchangeCount >= 4) bucket = LINES.poker.big_exchange;
      else bucket = LINES.poker.normal_exchange;
      const [text, emotion] = pick(bucket); this._speak(text, emotion);
    },
    pokerResult(result, playerHandName, cpuHandName) {
      const bucket = result === 'win' ? LINES.poker.lose : result === 'lose' ? LINES.poker.win : LINES.poker.draw;
      const [text, emotion] = pick(bucket); this._speak(text, emotion);
    },
    concentrationCpuConfirmed() { const [text, emotion] = pick(LINES.concentration.confirmed); this._speak(text, emotion); },
    concentrationResult(outcome) {
      const bucket = outcome === 'win' ? LINES.concentration_result.win : outcome === 'lose' ? LINES.concentration_result.lose : LINES.concentration_result.draw;
      const [text, emotion] = pick(bucket); this._speak(text, emotion);
    },
    reversiResult(outcome) {
      const bucket = outcome === 'win' ? LINES.reversi_result.win : outcome === 'lose' ? LINES.reversi_result.lose : LINES.reversi_result.draw;
      const [text, emotion] = pick(bucket); this._speak(text, emotion);
    },
    concentrationPlayerStreak(count) {
      const bucket = count >= 4 ? LINES.concentration_player_streak.many : count === 3 ? LINES.concentration_player_streak[3] : LINES.concentration_player_streak[2];
      const [text, emotion] = pick(bucket); this._speak(text, emotion);
    },
    concentrationCpuMove(matched, usedMemory, confidence) {
      if (!matched && Math.random() >= 0.5) return;
      let bucket;
      if (matched && confidence === 'confirmed')               bucket = LINES.concentration.confirmed;
      else if (matched && usedMemory && confidence === 'high') bucket = LINES.concentration.high_match;
      else if (matched && usedMemory)                          bucket = LINES.concentration.memory_match;
      else if (matched)                                        bucket = LINES.concentration.lucky_match;
      else if (!matched && confidence === 'high')              bucket = LINES.concentration.high_miss;
      else if (!matched && usedMemory)                         bucket = LINES.concentration.memory_miss;
      else                                                     bucket = LINES.concentration.random_miss;
      const [text, emotion] = pick(bucket); this._speak(text, emotion);
    },
  };

  window.RinComment = RinComment;
})(window);
