"""
ThemeFetcher - Gemini API グラウンディングでリアルタイムテーマ取得
"""
import asyncio
import json
import logging
import re
import time
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_PROMPT_TEMPLATE = """\
今日は{today}です。
カフェ「Cafe Lumiere」のスタッフMiaとオーナーMasterが雑談するための話題を4〜6個考えてください。

以下の観点を組み合わせて話題を選んでください：
- 今日は何の日か（記念日・◯◯の日・祝日・季節イベントなど）
- 今週・最近話題になっていること（ニュース・トレンド・スポーツ・エンタメなど）
- 季節感のある話題（食べ物・天気・旬の出来事など）

カフェの雰囲気に合う、明るく話しやすい話題を選んでください。
政治・宗教・暴力などデリケートな話題は避けてください。
今日から1ヶ月以上前に終了したイベント・大会・キャンペーンは除いてください。

【promptフィールドの書き方】
会話を生成するAIへの情報メモとして書いてください。
- 今現在の具体的な事実・数字・固有名詞を含める（例: 今年の大会名・結果・注目選手など）
- 一般的な背景知識ではなく「今この時期ならではの情報」を優先する
- 3〜4文程度、カフェの軽い雑談に使えるレベルの内容で

以下のJSON配列形式のみで出力してください（説明文・コードブロック不要）：
[
  {{"title": "テーマ名（15文字以内）", "prompt": "今現在の具体的な事実を含む会話ヒント（3〜4文）"}},
  ...
]"""


class ThemeFetcher:

    def __init__(self, config: dict):
        gemini_cfg = config.get("gemini", {})
        self._api_key        = gemini_cfg.get("api_key", "").strip()
        self._model          = gemini_cfg.get("model", "gemini-2.0-flash")
        self._grounding      = gemini_cfg.get("grounding", True)
        self._fetch_interval = int(gemini_cfg.get("fetch_interval", 3600))
        self._enabled        = bool(self._api_key)
        self._cached_themes: list[dict] = []
        self._last_fetch: float = 0.0

    @property
    def enabled(self) -> bool:
        return self._enabled

    def get_themes(self) -> list[dict]:
        return list(self._cached_themes)

    def is_stale(self) -> bool:
        return time.monotonic() - self._last_fetch >= self._fetch_interval

    async def fetch_now(self) -> list[dict]:
        if not self._enabled:
            return []
        today = datetime.now().strftime("%Y年%m月%d日（%A）")
        prompt = _PROMPT_TEMPLATE.format(today=today)
        try:
            themes = await self._call_gemini(prompt)
            if themes:
                self._cached_themes = themes
                self._last_fetch = time.monotonic()
                titles = ", ".join(f'「{t["title"]}」' for t in themes)
                logger.info(f"🌐 動的テーマ取得: {len(themes)}件 [{titles}]")
            else:
                logger.warning("⚠️ 動的テーマ: 有効なテーマが取得できませんでした")
            return themes
        except Exception as e:
            logger.error(f"❌ 動的テーマ取得エラー: {e}")
            return []

    async def run(self, shutdown_event: asyncio.Event):
        if not self._enabled:
            logger.info("🌐 ThemeFetcher 無効（api_key 未設定）— 静的テーマを使用")
            return
        logger.info(f"🌐 ThemeFetcher 起動 (モデル: {self._model}, 更新間隔: {self._fetch_interval}秒)")
        await self.fetch_now()
        while not shutdown_event.is_set():
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=min(300, self._fetch_interval))
            except asyncio.TimeoutError:
                pass
            if shutdown_event.is_set():
                break
            if self.is_stale():
                await self.fetch_now()
        logger.info("🌐 ThemeFetcher 停止")

    async def _call_gemini(self, prompt: str) -> list[dict]:
        url = _ENDPOINT.format(model=self._model)
        params = {"key": self._api_key}
        body: dict = {
            "system_instruction": {"parts": [{"text": "あなたはJSON生成専用のAPIです。出力はJSON配列のみとし、説明文・前置き・コードブロック記号は一切含めないでください。"}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 1.0, "maxOutputTokens": 1024, "responseMimeType": "application/json"},
        }
        if self._grounding:
            body["tools"] = [{"google_search": {}}]
            body["generationConfig"].pop("responseMimeType", None)
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, params=params, json=body) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Gemini API {resp.status}: {text[:300]}")
                data = await resp.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return self._parse_themes(raw_text)

    def _parse_themes(self, text: str) -> list[dict]:
        text = re.sub(r"^```[a-z]*\n?", "", text.strip(), flags=re.MULTILINE)
        text = re.sub(r"\n?```$", "", text.strip(), flags=re.MULTILINE)
        text = text.strip()
        start = text.find("[")
        end   = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            logger.warning(f"⚠️ テーマ JSON が見つかりません: {text[:120]!r}")
            return []
        m_text = text[start:end + 1]
        try:
            raw = json.loads(m_text)
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ テーマ JSON パース失敗: {e} / {text[:120]!r}")
            return []
        themes = []
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            title  = str(item.get("title", "")).strip()
            prompt = str(item.get("prompt", "")).strip()
            if title and prompt:
                themes.append({"id": f"dynamic_{i}", "title": title, "prompt": prompt, "keywords": []})
        return themes
