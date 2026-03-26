"""
GeneratorAgent (vA1 - 本編と同一)
"""
import asyncio
import json
import logging
import random
import re
from datetime import datetime

import yaml

from models import ChatMessage, TextChunk
from src.orchestrator.llm_client import LLMClient
from src.orchestrator.context import ContextManager
from src.orchestrator.scenario_buffer import ScenarioBuffer
from src.orchestrator import world_state

logger = logging.getLogger(__name__)


class GeneratorAgent:

    _MASTER_KEYWORDS = ["マスター", "大将", "店長", "オーナー"]

    _FALLBACK_DIALOGUES = [
        [
            {"speaker": "mia",    "text": "マスター、最近新しいコーヒー豆は入りましたか？"},
            {"speaker": "master", "text": "そうそう、エチオピアのイエルガチェフェが届いたよ。フルーティな香りが特徴でね。"},
        ],
        [
            {"speaker": "mia",    "text": "マスター、今日のおすすめってどれですか？"},
            {"speaker": "master", "text": "コロンビア産のナリーニョがいいかな。甘みと酸味のバランスがちょうどいいよ。"},
        ],
        [
            {"speaker": "mia",    "text": "マスター、コーヒーの香りって本当に落ち着きますよね。"},
            {"speaker": "master", "text": "うん、豆を挽いた瞬間の香りは特別だよね。"},
        ],
        [
            {"speaker": "mia",    "text": "マスター、ラテアートって難しいですか？"},
            {"speaker": "master", "text": "コツは注ぎの速度にあるんだよ。練習すれば誰でもできるよ。"},
        ],
        [
            {"speaker": "mia",    "text": "マスター、今日はお客さん多いですね。"},
            {"speaker": "master", "text": "天気がいいからかな。コーヒーを丁寧に出すのが一番だよ。"},
        ],
    ]

    def __init__(self, voice_queue: asyncio.Queue, output_queue: asyncio.Queue,
                 config: dict, theme_manager=None, ws_server=None, shutdown_event=None,
                 theme_fetcher=None, memory_manager=None):
        self.voice_queue    = voice_queue
        self.output_queue   = output_queue
        self.config         = config
        self.theme_manager  = theme_manager
        self.ws_server      = ws_server
        self.shutdown_event = shutdown_event
        self.theme_fetcher  = theme_fetcher
        self.memory_manager = memory_manager
        self._running       = False

        self.llm     = LLMClient(config)
        self.context = ContextManager(config)
        self.persona = self._load_persona()

        self._scenario_buffer: ScenarioBuffer | None = None
        self._monologue_buffer: ScenarioBuffer | None = None

        mem_cfg = config.get("memory", {})
        self._extract_interval = mem_cfg.get("extract_interval", 5)
        self._max_memories     = mem_cfg.get("max_memories_in_prompt", 10)
        self._turn_count       = 0

        gen_cfg = config.get("generator", {})
        self._late_night_start = gen_cfg.get("late_night_start", 23)
        self._late_night_end   = gen_cfg.get("late_night_end",   6)

        if self.memory_manager:
            self.memory_manager.start_visit()

    def _load_persona(self) -> dict:
        try:
            with open("persona.yaml", "r", encoding="utf-8") as f:
                persona = yaml.safe_load(f)
            logger.info("✅ ペルソナ読み込み完了")
            return persona
        except FileNotFoundError:
            logger.warning("⚠️ persona.yaml が見つかりません。デフォルト設定を使用。")
            return {}

    def _get_mia_persona_str(self) -> str:
        mia = self.persona.get("mia", {})
        return (
            f"名前: {mia.get('name', 'Mia')}\n"
            f"説明: {mia.get('description', '')}\n"
            f"一人称: {mia.get('first_person', 'わたし')}\n"
            f"口調: {mia.get('tone', '')}\n"
            f"禁止事項: {', '.join(mia.get('forbidden', []))}"
        )

    def _get_master_persona_str(self) -> str:
        master = self.persona.get("master", {})
        return (
            f"名前: {master.get('name', 'Master')}\n"
            f"説明: {master.get('description', '')}\n"
            f"一人称: {master.get('first_person', 'ぼく')}\n"
            f"口調: {master.get('tone', '')}\n"
            f"禁止事項: {', '.join(master.get('forbidden', []))}"
        )

    def _is_late_night(self) -> bool:
        h = datetime.now().hour
        s, e = self._late_night_start, self._late_night_end
        return (h >= s or h < e)

    def _get_memory_summary(self) -> str:
        if self.memory_manager:
            return self.memory_manager.get_memories_for_prompt(self._max_memories)
        return ""

    def _build_prompt(self, key: str, variables: dict) -> str:
        template = self.persona.get("prompts", {}).get(key, "")
        if not template:
            logger.warning(f"⚠️ プロンプトキー '{key}' が見つかりません")
            return ""
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"⚠️ プロンプト変数不足 '{key}': {e}")
            return template

    def _build_comment_response_prompt(self, user_message: str) -> str:
        return self._build_prompt("comment_response", {
            "user_message":      user_message,
            "context":           self.context.get_context_summary(),
            "persona":           self._get_mia_persona_str(),
            "memory_summary":    self._get_memory_summary(),
            "real_world_context": world_state.get_context_str(),
        })

    async def run(self):
        self._running = True
        logger.info("🧠 Generator Agent 起動 (シナリオバッファモード)")

        if not self.theme_manager:
            logger.error("❌ ThemeManager が設定されていません")
            return

        self._scenario_buffer = ScenarioBuffer(
            config=self.config, theme_manager=self.theme_manager, llm_client=self.llm,
            persona=self.persona, shutdown_event=self.shutdown_event, theme_fetcher=self.theme_fetcher,
        )
        self._monologue_buffer = ScenarioBuffer(
            config=self.config, theme_manager=self.theme_manager, llm_client=self.llm,
            persona=self.persona, shutdown_event=self.shutdown_event, theme_fetcher=self.theme_fetcher,
            prompt_key="master_monologue",
        )
        asyncio.create_task(self._scenario_buffer.run(), name="scenario_buffer")
        asyncio.create_task(self._monologue_buffer.run(), name="monologue_buffer")

        idle_timeout     = self.config.get("generator", {}).get("idle_timeout", 90)
        client_available = getattr(self.ws_server, "client_available", None)

        while self._running and not (self.shutdown_event and self.shutdown_event.is_set()):
            if client_available and not client_available.is_set():
                logger.info("⏸ クライアント不在 — 接続待機中...")
                try:
                    await client_available.wait()
                except asyncio.CancelledError:
                    break
                logger.info("▶ クライアント接続 — アイドル再開")
                continue
            try:
                msg = await asyncio.wait_for(self.voice_queue.get(), timeout=idle_timeout)
                await self._respond_to_user(msg)
            except asyncio.TimeoutError:
                if client_available and not client_available.is_set():
                    continue
                await self._idle_dialogue()
            except asyncio.CancelledError:
                break

        logger.info("🛑 Generator Agent 停止")

    async def on_client_connected(self):
        await asyncio.sleep(0.8)
        if self._is_late_night():
            welcome = [{"speaker": "master", "text": "いらっしゃい。静かな時間だけど、ゆっくりしていって。"}]
        else:
            welcome = [
                {"speaker": "mia",    "text": "いらっしゃいませ！Cafe Lumiereへようこそ。"},
                {"speaker": "master", "text": "ゆっくりしていってください。"},
            ]
        for line in welcome:
            await self.output_queue.put(TextChunk(
                text=line["text"], emotion=self._detect_emotion(line["text"]), speaker=line["speaker"]
            ))
        logger.info("👋 ウェルカムメッセージ送出")

    async def _idle_dialogue(self):
        if self._is_late_night():
            await self._idle_monologue()
        else:
            await self._idle_exchange()

    async def _idle_exchange(self):
        logger.info(f"🕐 掛け合い開始 (buffer={self._scenario_buffer.qsize()}件)")
        exchange = self._scenario_buffer.get_nowait()
        if exchange is None:
            logger.info("📦 バッファ空 — 固定フォールバック使用")
            exchange = random.choice(self._FALLBACK_DIALOGUES)
        for line in exchange:
            text = line["text"]
            await self.output_queue.put(TextChunk(
                text=text, emotion=self._detect_emotion(text), speaker=line["speaker"]
            ))
            icon = "💬" if line["speaker"] == "mia" else "☕"
            logger.info(f"{icon} {line['speaker'].title()}: {text[:50]}")
        if len(exchange) >= 2:
            self.context.add_exchange([f"[Mia] {exchange[0]['text']}"], f"[Master] {exchange[-1]['text']}")

    async def _idle_monologue(self):
        logger.info(f"🌙 独り言開始 (buffer={self._monologue_buffer.qsize()}件)")
        exchange = self._monologue_buffer.get_nowait()
        if exchange is None:
            logger.info("📦 モノローグバッファ空 — スキップ")
            return
        for line in exchange:
            if line["speaker"] != "master":
                continue
            text = line["text"]
            await self.output_queue.put(TextChunk(text=text, emotion=self._detect_emotion(text), speaker="master"))
            logger.info(f"🌙 Master: {text[:50]}")

    def _is_addressed_to_master(self, message: str) -> bool:
        head = message[:10]
        return any(kw in head for kw in self._MASTER_KEYWORDS)

    async def _respond_to_user(self, msg: ChatMessage):
        if self._is_late_night():
            await self._respond_as_master_solo(msg)
        elif self._is_addressed_to_master(msg.message):
            await self._relay_to_master(msg)
        else:
            await self._respond_as_mia(msg)

    async def _respond_as_master_solo(self, msg: ChatMessage):
        user_message = msg.message
        logger.info(f"🌙 深夜モード — Master単独応答: 「{user_message[:30]}」")
        prompt = self._build_prompt("master_solo_response", {
            "user_message":       user_message,
            "context":            self.context.get_context_summary(),
            "memory_summary":     self._get_memory_summary(),
            "master_persona":     self._get_master_persona_str(),
            "real_world_context": world_state.get_context_str(),
        })
        if not prompt:
            return
        response = (await self.llm.generate([
            {"role": "system", "content": prompt},
            {"role": "user",   "content": user_message},
        ])).strip()
        if response:
            for s in self._split_into_sentences(response):
                if s.strip():
                    await self.output_queue.put(TextChunk(text=s.strip(), emotion=self._detect_emotion(s), speaker="master"))
            self.context.add_exchange([user_message], response)
            if self.memory_manager:
                self.memory_manager.log_message("user",   user_message)
                self.memory_manager.log_message("master", response)
            self._turn_count += 1
            if self._turn_count % self._extract_interval == 0:
                asyncio.create_task(self._extract_memory())
            logger.info(f"☕ Master単独: {response[:50]}")

    async def _relay_to_master(self, msg: ChatMessage):
        user_message = msg.message
        logger.info(f"↪ マスター呼びかけ検出: 「{user_message[:30]}」")

        relay_prompt = self._build_prompt("master_relay", {
            "user_message": user_message,
            "mia_persona":  self._get_mia_persona_str(),
        })
        relay_text = ""
        if relay_prompt:
            relay_text = (await self.llm.generate([
                {"role": "system", "content": relay_prompt},
                {"role": "user",   "content": user_message},
            ])).strip()
        if relay_text:
            await self.output_queue.put(TextChunk(text=relay_text, emotion=self._detect_emotion(relay_text), speaker="mia"))
            logger.info(f"💬 Mia中継: {relay_text[:40]}")

        master_prompt = self._build_prompt("master_direct_response", {
            "user_message":       user_message,
            "relay_text":         relay_text,
            "context":            self.context.get_context_summary(),
            "memory_summary":     self._get_memory_summary(),
            "master_persona":     self._get_master_persona_str(),
            "real_world_context": world_state.get_context_str(),
        })
        master_response = ""
        if master_prompt:
            master_response = (await self.llm.generate([
                {"role": "system", "content": master_prompt},
                {"role": "user",   "content": user_message},
            ])).strip()
        if master_response:
            for s in self._split_into_sentences(master_response):
                if s.strip():
                    await self.output_queue.put(TextChunk(text=s.strip(), emotion=self._detect_emotion(s), speaker="master"))
            logger.info(f"☕ Master返答: {master_response[:40]}")

        if master_response and random.random() < 0.3:
            followup = (await self.llm.generate([
                {"role": "system", "content": f"マスターが「{master_response}」と言いました。Miaとして一言だけ短く添えてください。1文のみ。テキストのみ出力。"},
            ])).strip()
            if followup:
                await self.output_queue.put(TextChunk(text=followup, emotion="happy", speaker="mia"))

        self.context.add_exchange([user_message], master_response)
        if self.memory_manager:
            self.memory_manager.log_message("user",   user_message)
            self.memory_manager.log_message("master", master_response)
        self._turn_count += 1
        if self._turn_count % self._extract_interval == 0:
            asyncio.create_task(self._extract_memory())

    async def _respond_as_mia(self, msg: ChatMessage):
        user_message = msg.message
        logger.info(f"🎤 ユーザー応答: {msg.username}「{user_message}」")
        messages = [
            {"role": "system", "content": self._build_comment_response_prompt(user_message)},
            {"role": "user",   "content": user_message},
        ]
        response = await self.llm.generate(messages)
        if response.strip():
            for s in self._split_into_sentences(response.strip()):
                s = s.strip()
                if s:
                    await self.output_queue.put(TextChunk(
                        text=s, emotion=self._detect_emotion(s, [user_message]),
                        speaker="mia", source_comments=[msg.username],
                    ))
            self.context.add_exchange([user_message], response.strip())
            if self.memory_manager:
                self.memory_manager.log_message("user", user_message)
                self.memory_manager.log_message("mia",  response.strip())
            self._turn_count += 1
            if self._turn_count % self._extract_interval == 0:
                asyncio.create_task(self._extract_memory())
            logger.info(f"🎤 応答完了: {response.strip()[:50]}")

    async def _extract_memory(self):
        if not self.memory_manager:
            return
        history = self.context.get_history_for_prompt()
        if not history:
            return
        conversation_text = "\n".join(
            f"{'お客さん' if m['role'] == 'user' else 'Mia/Master'}: {m['content']}" for m in history
        )
        extract_prompt = self._build_prompt("memory_extract", {"conversation": conversation_text})
        if not extract_prompt:
            return
        try:
            raw = (await self.llm.generate([{"role": "system", "content": extract_prompt}], max_tokens=512)).strip()
            if "```" in raw:
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else raw
                if raw.startswith("json"):
                    raw = raw[4:]
            facts = json.loads(raw)
            if isinstance(facts, list) and facts:
                self.memory_manager.save_memories(facts)
                logger.info(f"🧠 記憶抽出完了: {len(facts)}件")
        except Exception as e:
            logger.warning(f"⚠️ 記憶抽出失敗（スキップ）: {e}")

    def _split_into_sentences(self, text: str) -> list:
        parts = re.split(r'(?<=[。！？\n])(?!」)', text)
        return [p for p in parts if p]

    def _detect_emotion(self, text: str, input_comments: list = None) -> str:
        full_text = text if not input_comments else " ".join(input_comments) + " " + text
        if re.search(r'(悲し|残念|ごめん|つらい|辛い|泣|寂し|切な|しんどい|落ち込|心配)', full_text): return "sad"
        if re.search(r'(えっ|マジ|すごい|びっくり|驚|えぇ|ほんと[にう]？|信じられ|衝撃|！？|？！|まさか|うそ)', full_text): return "surprised"
        if re.search(r'(怒|むかつく|ひどい|ふざけ|許さ|イライラ|うざ)', full_text): return "angry"
        if re.search(r'(嬉し|楽し|やった|わーい|ありがと|好き|最高|大好き|幸せ|かわいい|おめでと|よかった)', full_text): return "happy"
        if re.search(r'(ふふ|のんびり|まったり|ゆっくり|癒さ|落ち着|コーヒー|カフェ)', full_text): return "relaxed"
        return "neutral"

    async def close(self):
        if self.memory_manager:
            self.memory_manager.end_visit(self._turn_count)
        await self.llm.close()

    def stop(self):
        self._running = False
        logger.info("🛑 Generator Agent 停止リクエスト")
