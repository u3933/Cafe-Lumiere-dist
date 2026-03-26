"""
Cafe Lumiere - エントリーポイント (vA1 配布版)
"""
import asyncio
import logging
import signal
import ssl
import sys
from pathlib import Path

import yaml
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-22s] %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def load_config(path: str = "config.yaml") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ 設定読み込み: {path}")
        return config
    except FileNotFoundError:
        logger.error(f"❌ 設定ファイルが見つかりません: {path}")
        sys.exit(1)


def _build_ssl_context(config: dict):
    ssl_cfg = config.get("ssl", {})
    cert = ssl_cfg.get("cert", "").strip()
    key  = ssl_cfg.get("key",  "").strip()
    if not cert or not key:
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    logger.info(f"🔒 SSL有効: cert={cert}")
    return ctx


# デフォルトキャラクター設定（config.yaml に characters がない場合のフォールバック）
_DEFAULT_CHARACTERS = {
    "chara1": {
        "pool": [
            {"file": "rin_mid_1.png",     "layer": 5},
            {"file": "rin_mid_2.png",     "layer": 5},
            {"file": "rin_mid_3.png",     "layer": 5},
            {"file": "rin_back_clean.png","layer": 2},
            {"file": "rin_back_rest.png", "layer": 2, "condition": "sunny_daytime"},
        ],
        "late_night_pool": [
            {"file": "rin_back_sleep.png","layer": 2},
        ],
    },
    "chara2": {
        "pool": [
            {"file": "master_front.png",  "layer": 3},
            {"file": "master_back.png",   "layer": 3},
        ],
    },
}

# デフォルト背景画像設定
_DEFAULT_SCENE_IMAGES = {
    "bg_indoor": "bg_indoor.png",
    "obj_mid":   "obj_mid.png",
    "obj_front": "obj_front.png",
    "scenery": {
        "day":       "scenery_day.png",
        "dawn":      "scenery_dawn.png",
        "evening":   "scenery_evening.png",
        "night":     "scenery_night.png",
        "latenight": "scenery_latenight.png",
        "cloudy":    "scenery_cloudy.png",
        "rain":      "scenery_rain.png",
    },
}


async def start_http_server(config: dict, shutdown_event: asyncio.Event, ssl_context=None):
    http_config = config.get("http", {})
    port = http_config.get("port", 8766)

    app = web.Application()

    async def handle_api_config(request):
        bgm_cfg         = config.get("bgm", {})
        stt_cfg         = config.get("stt", {})
        tts_cfg         = config.get("tts", {})
        characters_cfg  = config.get("characters", _DEFAULT_CHARACTERS)
        scene_cfg       = config.get("scene_images", _DEFAULT_SCENE_IMAGES)

        default_schedules = [
            {"file": "assets/bgm/cafe_bgm_morning.mp3", "start": 6},
            {"file": "assets/bgm/cafe_bgm.mp3",         "start": 13},
            {"file": "assets/bgm/cafe_bgm_night.mp3",   "start": 22},
        ]
        return web.json_response({
            "bgm": {
                "volume":    bgm_cfg.get("volume", 0.3),
                "schedules": bgm_cfg.get("schedules", default_schedules),
            },
            "stt": {
                "provider": stt_cfg.get("provider", "browser"),
                "language": stt_cfg.get("language", "ja-JP"),
            },
            "tts": {
                "provider": tts_cfg.get("provider", "voicevox"),
            },
            "characters":   characters_cfg,
            "scene_images": scene_cfg,
        })
    app.router.add_get("/api/config", handle_api_config)

    assets_path = Path("assets").resolve()
    if assets_path.exists():
        app.router.add_static("/assets", assets_path)

    frontend_path = Path("frontend").resolve()

    async def handle_index(request):
        return web.FileResponse(frontend_path / "index.html")
    app.router.add_get("/", handle_index)
    app.router.add_static("/", frontend_path, show_index=False)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port, ssl_context=ssl_context)
    await site.start()
    scheme = "https" if ssl_context else "http"
    logger.info(f"🌐 HTTP サーバ起動: {scheme}://0.0.0.0:{port}/")

    await shutdown_event.wait()
    await runner.cleanup()
    logger.info("🌐 HTTP サーバ停止")


async def main():
    logger.info("=" * 60)
    logger.info("☕ Cafe Lumiere 起動 (vA1 配布版)")
    logger.info("=" * 60)

    config = load_config()

    queue_config   = config.get("queues", {})
    ws_voice_queue = asyncio.Queue(maxsize=queue_config.get("ws_voice_queue_maxsize", 5))
    voice_queue    = asyncio.Queue(maxsize=queue_config.get("voice_queue_maxsize", 10))
    output_queue   = asyncio.Queue(maxsize=queue_config.get("output_queue_maxsize", 10))

    ssl_context = _build_ssl_context(config)

    from src.output.ws_server import WSServer
    ws_server = WSServer(config, voice_queue=ws_voice_queue, output_queue=output_queue)
    await ws_server.start(ssl_context=ssl_context)

    from src.orchestrator.theme_manager import ThemeManager
    theme_config  = config.get("theme", {})
    theme_manager = ThemeManager(config, themes_path=theme_config.get("themes_file", "themes.yaml"))

    shutdown_event = asyncio.Event()

    from src.agents.voice_receiver import VoiceReceiverAgent
    from src.agents.generator import GeneratorAgent
    from src.agents.speaker import SpeakerAgent
    from src.output.bgm_player import BGMPlayer
    from src.orchestrator.theme_fetcher import ThemeFetcher
    from src.orchestrator.memory_manager import MemoryManager
    from src.output.memory_server import MemoryServer
    from src.output.weather_fetcher import WeatherFetcher

    theme_fetcher   = ThemeFetcher(config)
    memory_manager  = MemoryManager(config)
    memory_server   = MemoryServer(config, memory_manager)
    weather_fetcher = WeatherFetcher(config, ws_server)

    voice_receiver = VoiceReceiverAgent(
        voice_queue_in=ws_voice_queue, voice_queue_out=voice_queue, config=config,
    )
    generator = GeneratorAgent(
        voice_queue=voice_queue, output_queue=output_queue, config=config,
        theme_manager=theme_manager, ws_server=ws_server, shutdown_event=shutdown_event,
        theme_fetcher=theme_fetcher, memory_manager=memory_manager,
    )
    speaker    = SpeakerAgent(output_queue=output_queue, config=config, ws_server=ws_server)
    bgm_player = BGMPlayer(config=config, shutdown_event=shutdown_event)

    ws_server.on_client_connect = generator.on_client_connected
    agents = [voice_receiver, generator, speaker]

    def signal_handler():
        logger.info("\n🛑 シャットダウンシグナルを受信...")
        for agent in agents:
            agent.stop()
        shutdown_event.set()

    if sys.platform == "win32":
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    else:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

    stt_provider = config.get("stt", {}).get("provider", "browser")
    tts_provider = config.get("tts", {}).get("provider", "voicevox")
    llm_provider = config.get("llm", {}).get("provider", "openai")
    mem_port     = config.get("memory_server", {}).get("port", 8767)
    char_names   = list(config.get("characters", _DEFAULT_CHARACTERS).keys())

    logger.info("🏃 全エージェント起動:")
    logger.info(f"  🎤 Agent 1: VoiceReceiver  (STT: {stt_provider})")
    logger.info(f"  🧠 Agent 2: Generator      (LLM: {llm_provider})")
    logger.info(f"  🔊 Agent 3: Speaker        (TTS: {tts_provider})")
    logger.info(f"  🎭 キャラクター: {', '.join(char_names)}")
    logger.info(f"  🧠 MemoryServer            (http://0.0.0.0:{mem_port}/)")
    logger.info(f"  📌 テーマ数: {len(theme_manager._themes)}")
    logger.info("-" * 60)

    try:
        tasks = [
            asyncio.create_task(voice_receiver.run(),   name="voice_receiver"),
            asyncio.create_task(generator.run(),         name="generator"),
            asyncio.create_task(speaker.run(),           name="speaker"),
            asyncio.create_task(bgm_player.run(),        name="bgm_player"),
            asyncio.create_task(start_http_server(config, shutdown_event, ssl_context), name="http_server"),
            asyncio.create_task(theme_fetcher.run(shutdown_event), name="theme_fetcher"),
            asyncio.create_task(memory_server.run(),     name="memory_server"),
            asyncio.create_task(weather_fetcher.run(),   name="weather_fetcher"),
        ]
        await shutdown_event.wait()
        logger.info("🛑 全タスクをキャンセル中...")
        for t in tasks:
            t.cancel()
        await asyncio.wait(tasks, timeout=5.0)
    except Exception as e:
        logger.error(f"❌ 致命的エラー: {e}")
    finally:
        logger.info("🧹 クリーンアップ中...")
        await generator.close()
        await speaker.close()
        await voice_receiver.close()
        await ws_server.close()
        logger.info("✅ シャットダウン完了")


if __name__ == "__main__":
    asyncio.run(main())
