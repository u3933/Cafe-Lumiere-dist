"""
BGMPlayer - dist版

dist版ではBGMはブラウザ側（ws_client.js / Web Audio API）で再生するため、
サーバー側 pygame 再生はデフォルト無効。
config.yaml で bgm.enabled: true にすると pygame 再生も有効化できる。
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


class BGMPlayer:

    def __init__(self, config: dict, shutdown_event: asyncio.Event):
        bgm_config = config.get("bgm", {})
        # dist版デフォルトは False（ブラウザ側で再生するため）
        self.enabled   = bgm_config.get("enabled", False)
        self.bgm_file  = bgm_config.get("file", "")
        self.volume    = float(bgm_config.get("volume", 0.3))
        self.shutdown_event = shutdown_event
        self._mixer_initialized = False

    async def run(self):
        if not self.enabled:
            logger.info("🎵 BGMPlayer: 無効設定のためスキップ（ブラウザ側で再生）")
            await self.shutdown_event.wait()
            return

        if not self.bgm_file:
            logger.warning("⚠️ BGMPlayer: bgm.file が未設定のためスキップ")
            await self.shutdown_event.wait()
            return

        try:
            import pygame
        except ImportError:
            logger.warning("⚠️ pygame がインストールされていません。BGMをスキップします。")
            await self.shutdown_event.wait()
            return

        try:
            pygame.mixer.init()
            self._mixer_initialized = True
            pygame.mixer.music.load(self.bgm_file)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(loops=-1)
            logger.info(f"🎵 BGM再生開始: {self.bgm_file} (volume={self.volume})")
        except FileNotFoundError:
            logger.warning(f"⚠️ BGMファイルが見つかりません: {self.bgm_file}")
            await self.shutdown_event.wait()
            return
        except Exception as e:
            logger.error(f"❌ BGM初期化エラー: {e}")
            await self.shutdown_event.wait()
            return

        await self.shutdown_event.wait()
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            logger.info("🎵 BGM停止")
        except Exception:
            pass
