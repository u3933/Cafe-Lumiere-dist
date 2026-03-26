"""
Context Manager - 短期メモリ・話題トラッカー
"""
import logging
from collections import deque
from typing import List, Dict

logger = logging.getLogger(__name__)


class ContextManager:

    def __init__(self, config: dict):
        gen_config = config.get("generator", {})
        self.window_size = gen_config.get("context_window", 10)
        self._history: deque = deque(maxlen=self.window_size)
        self._current_topic: str = ""
        self._recent_comments: deque = deque(maxlen=20)

    def add_exchange(self, user_comments: List[str], ai_response: str):
        self._history.append({"comments": user_comments, "response": ai_response})
        for c in user_comments:
            self._recent_comments.append(c)
        logger.debug(f"📝 会話ペア追加 (履歴: {len(self._history)}/{self.window_size})")

    def get_history_for_prompt(self) -> List[Dict[str, str]]:
        messages = []
        for exchange in self._history:
            comments_text = "\n".join(f"- {c}" for c in exchange["comments"])
            messages.append({"role": "user", "content": f"【お客さんの発言】\n{comments_text}"})
            messages.append({"role": "assistant", "content": exchange["response"]})
        return messages

    def get_context_summary(self, memory_summary: str = "") -> str:
        parts = []
        if memory_summary:
            parts.append(f"【お客さんの記憶】\n{memory_summary}")
        if not self._history:
            parts.append("今日の会話はまだありません。")
            return "\n\n".join(parts)
        recent = list(self._recent_comments)[-5:]
        recent_text = "、".join(f"「{c}」" for c in recent) if recent else "なし"
        if self._current_topic:
            parts.append(f"現在の話題: {self._current_topic}")
        parts.append(f"直近のお客さんの発言: {recent_text}")
        return "\n\n".join(parts)

    @property
    def current_topic(self) -> str:
        return self._current_topic

    @current_topic.setter
    def current_topic(self, topic: str):
        self._current_topic = topic
        logger.debug(f"📝 話題更新: {topic[:50]}...")

    def clear(self):
        self._history.clear()
        self._recent_comments.clear()
        self._current_topic = ""
        logger.info("🗑️ コンテキストクリア")
