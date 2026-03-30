"""
Cafe Lumiere - エントリーポイント (vA1 配布版)
"""
import asyncio
import logging
import os
import shutil
import signal
import ssl
import sys
from pathlib import Path

# ----------------------------------------------------------------
# PyInstaller 対応: ベースディレクトリの解決
#
# 通常実行時 : BASE_DIR = main.py と同じディレクトリ
# PyInstaller: BASE_DIR = EXE と同じディレクトリ（_internal/ の親）
#
# config.yaml / persona.yaml / assets/ 等の外出しファイルは
# BASE_DIR 基準で参照する。
# ----------------------------------------------------------------
if getattr(sys, 'frozen', False):
    # PyInstaller でビルドされた EXE として実行中
    BASE_DIR = Path(sys.executable).parent
else:
    # 通常の python main.py 実行
    BASE_DIR = Path(__file__).parent

# カレントディレクトリを BASE_DIR に固定
# （相対パスで開くファイルが BASE_DIR 基準になる）
os.chdir(BASE_DIR)

import yaml
import aiohttp as _aiohttp
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-22s] %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def load_config(path: str = "config.yaml") -> dict:
    config_path  = Path(path)

    # config.yaml.example の検索順:
    #   1. BASE_DIR（EXEと同じ場所 / 通常実行時はmain.pyと同じ場所）
    #   2. sys._MEIPASS（PyInstallerが展開した_internal/フォルダ）
    example_candidates = [BASE_DIR / "config.yaml.example"]
    if hasattr(sys, '_MEIPASS'):
        example_candidates.append(Path(sys._MEIPASS) / "config.yaml.example")
    example_path = next((p for p in example_candidates if p.exists()), None)

    # PyInstaller _internal/ から外出しファイルを BASE_DIR にコピー
    # （初回起動時のみ実行される）
    if hasattr(sys, '_MEIPASS'):
        for fname in ['tts_dict.yaml']:
            src = Path(sys._MEIPASS) / fname
            dst = BASE_DIR / fname
            if src.exists() and not dst.exists():
                shutil.copy(src, dst)

    # config.yaml がなければ example から自動コピーして起動
    if not config_path.exists():
        if example_path:
            shutil.copy(example_path, config_path)
            logger.warning("⚠️  config.yaml が見つからないため config.yaml.example からコピーしました。")
            logger.warning("⚠️  http://localhost:8766/setup_wizard/ で設定を完了してください。")
        else:
            logger.error("❌ config.yaml も config.yaml.example も見つかりません。")
            sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ 設定読み込み: {config_path}")
        return config
    except Exception as e:
        logger.error(f"❌ 設定ファイルの読み込みエラー: {e}")
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

    # ----------------------------------------------------------
    # /api/config
    # ----------------------------------------------------------
    async def handle_api_config(request):
        bgm_cfg        = config.get("bgm", {})
        stt_cfg        = config.get("stt", {})
        tts_cfg        = config.get("tts", {})
        scene_cfg_raw  = config.get("scene", {})
        characters_cfg = config.get("characters", _DEFAULT_CHARACTERS)
        scene_img_cfg  = config.get("scene_images", _DEFAULT_SCENE_IMAGES)

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
                "volume":   tts_cfg.get("volume", 1.0),
            },
            "characters":   characters_cfg,
            "scene_images": scene_img_cfg,
            "scene": {
                "overlay_title": scene_cfg_raw.get("overlay_title", "☕ Cafe Lumiere"),
            },
        })

    # ----------------------------------------------------------
    # /api/tts_test  ← セットアップウィザード用 TTSプロキシ
    # VOICEVOX / Style-Bert-VITS2 両対応
    # ----------------------------------------------------------
    async def handle_tts_test(request):
        try:
            body     = await request.json()
            provider = body.get("provider", "voicevox")
            text     = body.get("text", "テスト音声です")

            async with _aiohttp.ClientSession(
                timeout=_aiohttp.ClientTimeout(total=15)
            ) as session:

                if provider == "voicevox":
                    endpoint   = body.get("endpoint", "http://localhost:50021")
                    speaker_id = int(body.get("speaker_id", 3))
                    speed      = float(body.get("speed_scale", 1.0))
                    pitch      = float(body.get("pitch_scale", 0.0))

                    async with session.post(
                        f"{endpoint}/audio_query",
                        params={"text": text, "speaker": speaker_id},
                    ) as resp:
                        if resp.status != 200:
                            return web.json_response(
                                {"error": f"audio_query failed: {resp.status}"}, status=502
                            )
                        query = await resp.json()

                    query["speedScale"] = speed
                    query["pitchScale"] = pitch

                    async with session.post(
                        f"{endpoint}/synthesis",
                        params={"speaker": speaker_id},
                        json=query,
                        headers={"Content-Type": "application/json"},
                    ) as resp:
                        if resp.status != 200:
                            return web.json_response(
                                {"error": f"synthesis failed: {resp.status}"}, status=502
                            )
                        wav = await resp.read()

                elif provider == "sbv2":
                    endpoint   = body.get("endpoint", "http://localhost:5000")
                    model_name = body.get("model_name", "woman001")
                    speed      = float(body.get("speed", 1.0))

                    async with session.get(
                        f"{endpoint}/voice",
                        params={"text": text, "model_name": model_name, "length": speed},
                    ) as resp:
                        if resp.status != 200:
                            return web.json_response(
                                {"error": f"SBV2 synthesis failed: {resp.status}"}, status=502
                            )
                        wav = await resp.read()

                else:
                    return web.json_response(
                        {"error": f"未対応のprovider: {provider}"}, status=400
                    )

            return web.Response(
                body=wav,
                content_type="audio/wav",
                headers={"Access-Control-Allow-Origin": "*"},
            )

        except _aiohttp.ClientConnectorError as e:
            return web.json_response(
                {"error": f"TTSサーバーに接続できません: {e}"}, status=503
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    app.router.add_get ("/api/config",   handle_api_config)
    app.router.add_post("/api/tts_test", handle_tts_test)

    # ----------------------------------------------------------
    # 静的ファイル
    # パス解決順: BASE_DIR → sys._MEIPASS (_internal/)
    # 外出しファイル（assets/）は BASE_DIR のみ、
    # 同梱ファイル（frontend/ setup_wizard/）は両方を探索
    # ----------------------------------------------------------
    def find_dir(name: str) -> Path | None:
        """BASE_DIR を2内でディレクトリを探索する"""
        candidates = [BASE_DIR / name]
        if hasattr(sys, '_MEIPASS'):
            candidates.append(Path(sys._MEIPASS) / name)
        return next((p for p in candidates if p.exists()), None)

    assets_path = find_dir("assets")
    if assets_path:
        app.router.add_static("/assets", assets_path)

    # setup_wizard（ユーザーが任意でアクセス）
    wizard_path = find_dir("setup_wizard")
    if wizard_path:
        async def handle_wizard(request):
            return web.FileResponse(wizard_path / "index.html")
        app.router.add_get("/setup_wizard",  handle_wizard)
        app.router.add_get("/setup_wizard/", handle_wizard)
        app.router.add_static("/setup_wizard", wizard_path)
        logger.info("🧙 セットアップウィザード: /setup_wizard/")

    frontend_path = find_dir("frontend")
    if not frontend_path:
        logger.error("❌ frontend/ ディレクトリが見つかりません")
        return

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
