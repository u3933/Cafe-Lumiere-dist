"""
ScenarioBuffer - Mia/Master 掛け合いシナリオバッファ
"""
import asyncio
import logging
import random
import re
from src.orchestrator import world_state

logger = logging.getLogger(__name__)
DialogueExchange = list[dict]


class ScenarioBuffer:

    def __init__(self, config: dict, theme_manager, llm_client, persona: dict,
                 shutdown_event: asyncio.Event, theme_fetcher=None,
                 prompt_key: str = "dialogue_generation"):
        self._config = config
        self._theme_manager = theme_manager
        self._llm = llm_client
        self._persona = persona
        self._shutdown_event = shutdown_event
        self._theme_fetcher = theme_fetcher
        self._prompt_key = prompt_key
        gen_config = config.get("generator", {})
        self._buffer_min      = gen_config.get("scenario_buffer_min", 2)
        self._buffer_max      = gen_config.get("scenario_buffer_max", 5)
        self._refill_interval = gen_config.get("scenario_buffer_refill_interval", 30)
        self._queue: asyncio.Queue = asyncio.Queue()
        self._dynamic_pool: list[dict] = []
        self._static_pool:  list[dict] = []
        self._last_refill_time = 0.0

    async def run(self):
        import time
        logger.info("📦 ScenarioBuffer 起動")
        while not self._shutdown_event.is_set():
            now = time.monotonic()
            if (self._queue.qsize() <= self._buffer_min
                    and now - self._last_refill_time >= self._refill_interval):
                self._last_refill_time = now
                await self._refill()
            else:
                await asyncio.sleep(5.0)
        logger.info("📦 ScenarioBuffer 停止")

    async def _refill(self):
        themes = self._theme_manager.all_themes()
        if self._queue.qsize() >= self._buffer_max:
            return
        theme = self._next_theme(themes)
        if not theme:
            await asyncio.sleep(2.0)
            return
        prompt = self._build_dialogue_prompt(theme)
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": "はい"}]
        try:
            text = await self._llm.generate(messages, max_tokens=768)
            text = text.strip()
            if not text:
                await asyncio.sleep(5.0)
                return
            exchange = self._parse_dialogue(text)
            if len(exchange) < 2:
                logger.warning(f"⚠️ 掛け合い解析失敗 ({len(exchange)}行): {text[:60]!r}")
                await asyncio.sleep(5.0)
                return
            await self._queue.put(exchange)
            preview = " / ".join(f"{d['speaker']}:「{d['text'][:20]}」" for d in exchange)
            logger.info(f"📦 バッファ補充: 計{self._queue.qsize()}件 [{preview}]")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"❌ シナリオ生成エラー: {e}")
            await asyncio.sleep(20.0)

    def get_nowait(self) -> DialogueExchange | None:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def qsize(self) -> int:
        return self._queue.qsize()

    def _next_theme(self, static_themes: list) -> dict | None:
        if self._theme_fetcher and self._theme_fetcher.enabled:
            dynamic = self._theme_fetcher.get_themes()
            if dynamic:
                if not self._dynamic_pool:
                    self._dynamic_pool = list(dynamic)
                    random.shuffle(self._dynamic_pool)
                    logger.info(f"🌐 動的テーマをシャッフル: {len(self._dynamic_pool)}件")
                theme = self._dynamic_pool.pop()
                logger.debug(f"🌐 動的テーマ使用: 「{theme['title']}」")
                return theme
            logger.debug("🌐 動的テーマ未取得 — 静的テーマにフォールバック")
        if not static_themes:
            return None
        if not self._static_pool:
            self._static_pool = list(static_themes)
            random.shuffle(self._static_pool)
            logger.info(f"📚 静的テーマをシャッフル: {len(self._static_pool)}件")
        return self._static_pool.pop()

    def _build_dialogue_prompt(self, theme: dict) -> str:
        template = self._persona.get("prompts", {}).get(self._prompt_key, "")
        mia    = self._persona.get("mia", {})
        master = self._persona.get("master", {})
        mia_persona    = f"{mia.get('description', '')} 口調: {mia.get('tone', '')}"
        master_persona = f"{master.get('description', '')} 口調: {master.get('tone', '')}"
        if not template:
            return (
                f"カフェのスタッフMiaとオーナーMasterの掛け合いを以下の形式で生成してください。\n"
                f"話題: {theme.get('title', '')}\n"
                f"Mia: [Miaの発言]\nMaster: [Masterの発言]\nテキストのみ出力。"
            )
        return template.format(
            theme_title=theme.get("title", ""),
            theme_prompt=theme.get("prompt", ""),
            mia_persona=mia_persona,
            master_persona=master_persona,
            real_world_context=world_state.get_context_str(),
        )

    @staticmethod
    def _parse_dialogue(text: str) -> DialogueExchange:
        result = []
        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            for prefix, speaker in [
                ("Mia:", "mia"), ("Mia：", "mia"),
                ("Master:", "master"), ("Master：", "master"),
                ("ミア:", "mia"), ("マスター:", "master"),
            ]:
                if line.lower().startswith(prefix.lower()):
                    content = line[len(prefix):].strip()
                    if content and ScenarioBuffer.is_valid_response(content):
                        result.append({"speaker": speaker, "text": content})
                    break
        return result

    @staticmethod
    def is_valid_response(text: str) -> bool:
        text = text.strip()
        if not text:
            return False
        if text[0] in ('{', '[', '<', '`', '#', '('):
            return False
        if re.search(r'(The user says|system\s*:|user\s*:|assistant\s*:)', text, re.IGNORECASE):
            return False
        if not re.search(r'[\u3040-\u9FFF]', text):
            return False
        return True

    @staticmethod
    def split_sentences(text: str) -> list:
        parts = re.split(r'(?<=[。！？\n])(?!」)', text)
        return [p for p in parts if p.strip()]

    def _split_into_sentences(self, text: str) -> list:
        return self.split_sentences(text)
