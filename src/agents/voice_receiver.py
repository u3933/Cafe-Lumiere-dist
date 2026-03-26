"""
VoiceReceiverAgent (vA1)

stt.provider で STT を切り替える:
  provider: "browser"  → Web Speech API（ブラウザ側で認識済みテキストが来る）
  provider: "whisper"  → Whisper STT API（本編互換）

browser モードでは voice_input（base64音声）を無視し、
text_input（Web Speech API認識テキスト）のみを処理する。
"""
import asyncio
import base64
import logging
import tempfile
import os

import aiohttp

from models import ChatMessage

logger = logging.getLogger(__name__)


class VoiceReceiverAgent:
    """音声受信 → STT → voice_queue 投入エージェント"""

    def __init__(self, voice_queue_in: asyncio.Queue, voice_queue_out: asyncio.Queue, config: dict):
        self.voice_queue_in  = voice_queue_in
        self.voice_queue_out = voice_queue_out
        self.config = config
        self._running = False

        stt_config = config.get("stt", {})
        self._stt_provider = stt_config.get("provider", "browser").strip().lower()

        whisper_config = config.get("whisper", stt_config)
        self.whisper_endpoint = whisper_config.get("endpoint", "http://localhost:5001/whisper")
        self.whisper_timeout  = whisper_config.get("timeout", 10)

        self._session: aiohttp.ClientSession | None = None

        if self._stt_provider == "browser":
            logger.info("🎤 VoiceReceiver: Web Speech API モード（ブラウザSTT）")
        else:
            logger.info(f"🎤 VoiceReceiver: Whisper モード ({self.whisper_endpoint})")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.whisper_timeout + 5, connect=5)
            )
        return self._session

    async def run(self):
        self._running = True
        logger.info("🎤 VoiceReceiver Agent 起動")

        while self._running:
            try:
                msg: ChatMessage = await asyncio.wait_for(
                    self.voice_queue_in.get(),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ VoiceReceiver キュー読み取りエラー: {e}")
                continue

            # テキスト直接入力（text_ プレフィックス）→ STT スキップ
            if msg.user_id.startswith("text_"):
                recognized_text = msg.message.strip()
                if not recognized_text:
                    continue
                logger.info(f"💬 テキスト入力: {msg.username}「{recognized_text}」")

            elif self._stt_provider == "browser":
                # browserモードでは voice_input（base64音声）を無視
                # Web Speech APIの認識テキストは text_input として届くため
                logger.debug("🎤 browser STT モード: voice_input をスキップ")
                continue

            else:
                # Whisper STT
                recognized_text = await self._transcribe(msg.message, msg.username)
                if not recognized_text:
                    logger.info("🎤 STT: 空テキスト → スキップ")
                    continue
                logger.info(f"🎤 STT認識: {msg.username}「{recognized_text}」")

            out_msg = ChatMessage(
                user_id=msg.user_id,
                username=msg.username,
                message=recognized_text,
                timestamp=msg.timestamp,
            )

            if self.voice_queue_out.full():
                try:
                    self.voice_queue_out.get_nowait()
                    logger.debug("📥 voice_queue_out 満杯 → 古いメッセージをドロップ")
                except asyncio.QueueEmpty:
                    pass

            await self.voice_queue_out.put(out_msg)

        logger.info("🛑 VoiceReceiver Agent 停止")

    async def _transcribe(self, audio_b64: str, username: str) -> str:
        """base64 WAV → Whisper API → 認識テキスト"""
        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception as e:
            logger.error(f"❌ base64デコードエラー: {e}")
            return ""

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            session = await self._get_session()
            with open(tmp_path, "rb") as f:
                form_data = aiohttp.FormData()
                form_data.add_field("audio_file", f, filename="audio.wav", content_type="audio/wav")
                async with session.post(
                    self.whisper_endpoint,
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=self.whisper_timeout),
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"❌ Whisper API エラー: {resp.status}")
                        return ""
                    result = await resp.json()
                    return result.get("text", "").strip()

        except aiohttp.ClientError as e:
            logger.error(f"❌ Whisper 通信エラー: {e}")
            return ""
        except asyncio.TimeoutError:
            logger.error("❌ Whisper タイムアウト")
            return ""
        except Exception as e:
            logger.error(f"❌ Whisper 処理エラー: {e}")
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    def stop(self):
        self._running = False

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
