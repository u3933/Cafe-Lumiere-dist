"""
SpeakerAgent (vA1)

output_queue からテキストチャンクを取得し、
TextChunk.speaker を参照してTTSモデルを切り替え、
音声合成 → WebSocket配信 を行う。

VOICEVOX対応のため synthesize() に speaker 引数を追加。
"""
import asyncio
import logging
import time

from models import TextChunk
from src.output.tts_bridge import TTSBridge
from src.output.ws_server import WSServer

logger = logging.getLogger(__name__)


class SpeakerAgent:

    def __init__(self, output_queue: asyncio.Queue, config: dict, ws_server: WSServer):
        self.output_queue = output_queue
        self.config = config
        self.ws = ws_server
        self._running = False

        tts_config = config.get("tts", {})
        self.mia_model    = tts_config.get("mia_model_name", "woman001")
        self.master_model = tts_config.get("master_model_name", "man001")

        speaker_config = config.get("speaker", {})
        self.filler_threshold_ms = speaker_config.get("filler_threshold_ms", 800)
        self.inter_line_pause    = speaker_config.get("inter_line_pause", 0.8)

        self.tts = TTSBridge(config)
        self._last_speak_time = 0.0

    async def run(self):
        self._running = True
        logger.info("🔊 Speaker Agent 起動")

        while self._running:
            try:
                try:
                    chunk: TextChunk = await asyncio.wait_for(
                        self.output_queue.get(),
                        timeout=self.filler_threshold_ms / 1000.0,
                    )
                except asyncio.TimeoutError:
                    continue

                await self._speak_chunk(chunk)

            except Exception as e:
                logger.error(f"❌ Speaker エラー: {e}")
                await asyncio.sleep(1.0)

        logger.info("🛑 Speaker Agent 停止")

    async def _speak_chunk(self, chunk: TextChunk):
        # SBV2モード用モデル名（VOICEVOXの場合は tts_bridge 内で speaker_id に変換される）
        model = self.mia_model if chunk.speaker == "mia" else self.master_model

        result = await self.tts.synthesize(
            chunk.text,
            model_name=model,
            speaker=chunk.speaker,   # VOICEVOX用
        )

        if result is None:
            logger.warning(f"⚠️ TTS失敗: [{chunk.speaker}] {chunk.text[:30]}...")
            return

        await self.ws.send_speak(
            text=chunk.text,
            audio_data=result["audio"],
            duration=result["duration"],
            emotion=chunk.emotion,
            speaker=chunk.speaker,
        )

        await asyncio.sleep(result["duration"] + self.inter_line_pause)
        self._last_speak_time = time.time()
        logger.info(f"🗣️ 発話完了: [{chunk.speaker}/{chunk.emotion}] {chunk.text[:30]}... ({result['duration']:.1f}s)")

    async def close(self):
        await self.tts.close()

    def stop(self):
        self._running = False
