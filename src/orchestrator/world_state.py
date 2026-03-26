"""
world_state.py - 現実世界の状態（天気・時刻・季節）をグローバルに保持する
"""
from datetime import datetime

_weather: str = "sunny"


def update_weather(w: str) -> None:
    global _weather
    _weather = w


def get_context_str() -> str:
    now = datetime.now()
    h, m = now.hour, now.month

    if 5 <= h < 10:   time_label = "朝"
    elif 10 <= h < 13: time_label = "昼前"
    elif 13 <= h < 17: time_label = "午後"
    elif 17 <= h < 20: time_label = "夕方"
    elif 20 <= h < 23: time_label = "夜"
    else:              time_label = "深夜"

    if m in (3, 4, 5):    season = "春"
    elif m in (6, 7, 8):  season = "夏"
    elif m in (9, 10, 11): season = "秋"
    else:                  season = "冬"

    weather_map = {"sunny": "晴れ", "cloudy": "曇り", "rain": "雨"}
    return f"{season}の{time_label}。外は{weather_map.get(_weather, '晴れ')}。"
