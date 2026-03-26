"""
Theme Manager - テーマ選択・遷移・タイマー管理
"""
import logging
import random
import time
import yaml

logger = logging.getLogger(__name__)


class ThemeManager:

    def __init__(self, config: dict, themes_path: str = "themes.yaml"):
        self._themes = self._load_themes(themes_path)
        self._current_index = 0
        self._start_time = 0.0
        self._duration = 0.0
        self._started = False
        self._finished = False

    def _load_themes(self, path: str) -> list:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            themes = data.get("themes", [])
            logger.info(f"✅ テーマ読み込み: {len(themes)}件")
            for t in themes:
                logger.info(f"   📌 {t['title']}")
            return themes
        except FileNotFoundError:
            logger.error(f"❌ テーマファイルが見つかりません: {path}")
            return []

    def start(self):
        if not self._themes:
            logger.warning("⚠️ テーマが定義されていません")
            return
        self._current_index = 0
        self._start_theme()

    def _start_theme(self):
        theme = self.current_theme
        if not theme:
            return
        d_min = theme.get("duration_min", 180)
        d_max = theme.get("duration_max", 300)
        self._duration = random.uniform(d_min, d_max)
        self._start_time = time.time()
        self._started = True
        logger.info(f"🎯 テーマ開始: 「{theme['title']}」 ({self._duration:.0f}秒)")

    @property
    def current_theme(self) -> dict | None:
        if not self._themes:
            return None
        return self._themes[self._current_index % len(self._themes)]

    @property
    def next_theme(self) -> dict | None:
        if not self._themes:
            return None
        return self._themes[(self._current_index + 1) % len(self._themes)]

    @property
    def elapsed(self) -> float:
        return 0.0 if not self._started else time.time() - self._start_time

    @property
    def remaining(self) -> float:
        return max(0.0, self._duration - self.elapsed)

    def should_transition(self) -> bool:
        return self._started and self.elapsed >= self._duration

    @property
    def is_finished(self) -> bool:
        return self._finished

    def advance(self):
        old_title = self.current_theme["title"] if self.current_theme else "?"
        next_index = self._current_index + 1
        if next_index >= len(self._themes):
            self._finished = True
            self._started = False
            logger.info(f"✅ 全{len(self._themes)}テーマ完了")
            return
        self._current_index = next_index
        self._start_theme()
        new_title = self.current_theme["title"] if self.current_theme else "?"
        logger.info(f"🔄 テーマ遷移: 「{old_title}」→「{new_title}」")

    def get_transition_text(self) -> str:
        next_idx = self._current_index + 1
        if next_idx >= len(self._themes):
            return ""
        title = self._themes[next_idx]["title"]
        return random.choice([
            f"さてさて、次のテーマは「{title}」だよ！",
            f"じゃあ次は「{title}」について話していくね！",
            f"よーし、次は「{title}」の話をしよう！",
            f"ここからは「{title}」について語るよ〜！",
        ])

    def get_farewell_text(self) -> str:
        return random.choice([
            "今日もありがとう！また遊びに来てね、待ってるよ！",
            "楽しい時間をありがとう！またCafe Lumiereに来てね！",
            "あっという間だったな〜。またゆっくり話しかけてね！",
        ])

    def all_themes(self) -> list:
        return list(self._themes)

    def get_keywords(self) -> list:
        t = self.current_theme
        return t.get("keywords", []) if t else []

    def get_theme_prompt(self) -> str:
        t = self.current_theme
        return t.get("prompt", "") if t else ""

    def get_theme_title(self) -> str:
        t = self.current_theme
        return t.get("title", "") if t else ""
