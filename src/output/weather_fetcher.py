"""
WeatherFetcher - Open-Meteo API（本編と同一）
"""
import asyncio
import logging
import aiohttp
from src.orchestrator import world_state

logger = logging.getLogger(__name__)

_CODE_MAP: list[tuple[tuple, str]] = [
    ((*range(0, 2),),    'sunny'),
    ((*range(2, 4),),    'cloudy'),
    ((*range(45, 49),),  'cloudy'),
    ((*range(51, 68),),  'rain'),
    ((*range(71, 78),),  'rain'),
    ((*range(80, 100),), 'rain'),
]

def _code_to_weather(code: int) -> str:
    for codes, weather in _CODE_MAP:
        if code in codes:
            return weather
    return 'sunny'


class WeatherFetcher:

    def __init__(self, config: dict, ws_server):
        w = config.get("weather", {})
        self._enabled       = w.get("enabled", False)
        self._lat           = w.get("latitude",  35.6762)
        self._lon           = w.get("longitude", 139.6503)
        self._location_name = w.get("location_name", "")
        self._interval      = w.get("fetch_interval", 1800)
        self._ws            = ws_server
        self._current       = 'sunny'

    async def run(self):
        if not self._enabled:
            logger.info("🌤 WeatherFetcher: 無効設定のためスキップ")
            return
        loc = f" ({self._location_name})" if self._location_name else ""
        logger.info(f"🌤 WeatherFetcher: 起動 lat={self._lat} lon={self._lon}{loc}")
        while True:
            await self._fetch_and_broadcast()
            await asyncio.sleep(self._interval)

    async def _fetch_and_broadcast(self):
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={self._lat}&longitude={self._lon}"
            "&current=weather_code&timezone=auto"
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.warning(f"⚠️ 天気API エラー: {resp.status}")
                        return
                    data = await resp.json()
            code    = data["current"]["weather_code"]
            weather = _code_to_weather(code)
            if weather != self._current:
                logger.info(f"🌤 天気更新: {self._current} → {weather} (WMOコード={code})")
                self._current = weather
            else:
                logger.debug(f"🌤 天気変化なし: {weather} (WMOコード={code})")
            world_state.update_weather(weather)
            await self._ws.broadcast({"type": "weather_update", "weather": weather, "code": code})
        except aiohttp.ClientError as e:
            logger.warning(f"⚠️ 天気取得失敗（スキップ）: {e}")
        except (KeyError, ValueError) as e:
            logger.warning(f"⚠️ 天気レスポンス解析失敗: {e}")
