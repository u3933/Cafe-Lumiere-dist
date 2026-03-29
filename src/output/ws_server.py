"""
WebSocket Server（dist版）
"""
import asyncio
import base64
import json
import logging
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class WSServer:

    def __init__(self, config: dict, voice_queue=None, output_queue=None):
        ws_config = config.get("websocket", {})
        self.host = ws_config.get("host", "0.0.0.0")
        self.port = ws_config.get("port", 8765)
        self._clients: Set[WebSocketServerProtocol] = set()
        self._server = None
        self.voice_queue   = voice_queue
        self.output_queue  = output_queue
        self.client_available = asyncio.Event()
        self.on_client_connect = None

    async def start(self, ssl_context=None):
        self._server = await websockets.serve(self._handler, self.host, self.port, ssl=ssl_context)
        scheme = "wss" if ssl_context else "ws"
        logger.info(f"🌐 WebSocket サーバ起動: {scheme}://{self.host}:{self.port}")

    async def _handler(self, websocket: WebSocketServerProtocol):
        self._clients.add(websocket)
        self.client_available.set()
        client_info = f"{websocket.remote_address}"
        logger.info(f"🔗 クライアント接続: {client_info} (計{len(self._clients)})")
        try:
            await websocket.send(json.dumps({"type": "bgm_play"}, ensure_ascii=False))
        except Exception:
            pass
        if self.on_client_connect:
            asyncio.create_task(self.on_client_connect())
        try:
            async for message in websocket:
                await self._handle_client_message(message)
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            if not self._clients:
                self.client_available.clear()
                logger.info("⏸ 全クライアント切断 — アイドル停止")
            logger.info(f"🔌 クライアント切断: {client_info} (残{len(self._clients)})")

    async def _handle_client_message(self, raw_message: str):
        import time
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError:
            return
        msg_type = data.get("type")

        if msg_type == "voice_input" and self.voice_queue:
            from models import ChatMessage
            username  = data.get("username", "user")
            audio_b64 = data.get("audio", "")
            if audio_b64:
                msg = ChatMessage(user_id=f"voice_{username}", username=username, message=audio_b64, timestamp=time.time())
                if self.voice_queue.full():
                    try: self.voice_queue.get_nowait()
                    except asyncio.QueueEmpty: pass
                await self.voice_queue.put(msg)
                logger.info(f"🎤 voice_input 受信: {username} ({len(audio_b64)} bytes b64)")

        elif msg_type == "text_input" and self.voice_queue:
            from models import ChatMessage
            username = data.get("username", "user")
            message  = data.get("message", "").strip()
            if message:
                # ユーザーテキストをチャット履歴に即時表示
                await self.broadcast({"type": "user_text", "text": message})
                msg = ChatMessage(user_id=f"text_{username}", username=username, message=message, timestamp=time.time())
                if self.voice_queue.full():
                    try: self.voice_queue.get_nowait()
                    except asyncio.QueueEmpty: pass
                await self.voice_queue.put(msg)
                logger.info(f"💬 text_input 受信: {username}「{message[:40]}」")

        elif msg_type == "game_comment" and self.voice_queue:
            from models import ChatMessage
            game   = data.get("game", "unknown")
            event  = data.get("event", "unknown")
            detail = data.get("detail", {})
            text   = self._game_event_to_text(game, event, detail)
            if text:
                msg = ChatMessage(user_id="text_game", username="game", message=text, timestamp=time.time())
                if not self.voice_queue.full():
                    await self.voice_queue.put(msg)
                logger.info(f"🎮 game_comment: {game}/{event}")

        elif msg_type == "rin_speak" and self.output_queue:
            from models import TextChunk
            text    = data.get("text", "").strip()
            emotion = data.get("emotion", "neutral")
            if text and not self.output_queue.full():
                await self.output_queue.put(TextChunk(text=text, emotion=emotion, speaker="mia"))
                logger.info(f"🎮 rin_speak: [{emotion}] {text[:40]}")

    def _game_event_to_text(self, game: str, event: str, detail: dict) -> str:
        if event == 'start':
            names = {'poker': 'ポーカー', 'concentration': '神経衰弱', 'reversi': 'リバーシ'}
            name = names.get(game, game)
            return (
                f"[ゲーム:{name}] あなたはりんです。お客さんが{name}を始めました。"
                f"対戦相手として「よろしくお願いします」的な一言を、りんらしく1文で言ってください。テキストのみ出力。"
            )
        return ''

    async def broadcast(self, data: dict):
        if not self._clients:
            return
        message = json.dumps(data, ensure_ascii=False)
        disconnected = set()
        for client in self._clients:
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                disconnected.add(client)
        self._clients -= disconnected

    async def send_speak(self, text: str, audio_data: bytes, duration: float, emotion: str = "neutral", speaker: str = "mia"):
        audio_b64 = base64.b64encode(audio_data).decode("ascii")
        await self.broadcast({"type": "speak", "text": text, "summary": text[:30], "audio": audio_b64, "duration": duration, "emotion": emotion, "speaker": speaker})
        logger.debug(f"📡 speak送信: [{speaker}/{emotion}] {text[:30]}... ({duration:.1f}s)")

    async def send_emotion(self, emotion: str, speaker: str = "mia"):
        await self.broadcast({"type": "emotion", "emotion": emotion, "speaker": speaker})

    async def send_stop(self):
        await self.broadcast({"type": "stop"})

    async def send_filler(self, text: str, audio_data: bytes, duration: float, speaker: str = "mia"):
        audio_b64 = base64.b64encode(audio_data).decode("ascii")
        await self.broadcast({"type": "speak", "text": text, "summary": text[:30], "audio": audio_b64, "duration": duration, "emotion": "neutral", "speaker": speaker, "is_filler": True})

    async def send_theme_update(self, themes: list, current_index: int):
        await self.broadcast({"type": "theme_update", "themes": themes, "current_index": current_index})

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def close(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for client in self._clients:
            await client.close()
        logger.info("🛑 WebSocketサーバ停止")
