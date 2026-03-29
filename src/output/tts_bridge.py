"""
TTS Bridge - VOICEVOX / Style-Bert-VITS2 両対応 (vA1)

config.yaml の tts.provider で切り替え:
  provider: "voicevox" → VOICEVOX（推奨・要インストール・CPU動作）
  provider: "sbv2"     → Style-Bert-VITS2（本編互換）

tts.volume（1.0以上）を設定すると、サーバー側でWAV音量を増幅して送信する。
Python 3.13 で audioop が削除されたため numpy で実装。
"""
import asyncio
import io
import logging
import re
import struct
import wave
from pathlib import Path

import aiohttp
import yaml

logger = logging.getLogger(__name__)


def _clean_for_tts(text: str) -> str:
    cleaned = re.sub(
        r'[^\w\s。、！？!?\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBFa-zA-Z0-9ー〜～・]',
        '', text
    )
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


_JP_CHARS = r'\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF'
_KANJI    = r'\u4E00-\u9FFF\u3400-\u4DBF'


def _load_dict(dict_file: str) -> list[tuple[re.Pattern, str]]:
    if not dict_file:
        return []
    path = Path(dict_file)
    if not path.exists():
        logger.warning(f"⚠️ TTS辞書ファイルが見つかりません: {dict_file}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"❌ TTS辞書読み込みエラー: {e}")
        return []

    words: dict = data.get("words", {}) or {}
    if not words:
        return []

    sorted_words = sorted(words.items(), key=lambda kv: len(str(kv[0])), reverse=True)
    patterns: list[tuple[re.Pattern, str]] = []
    for word, reading in sorted_words:
        word = str(word)
        reading = str(reading)
        escaped = re.escape(word)
        if re.fullmatch(r'[a-zA-Z0-9\-]+', word):
            pattern = re.compile(
                r'(?<![a-zA-Z0-9])' + escaped + r'(?![a-zA-Z0-9])',
                re.IGNORECASE,
            )
        elif re.search(f'[{_JP_CHARS}]', word):
            if len(word) == 1:
                pattern = re.compile(
                    r'(?<![' + _KANJI + r'])' + escaped + r'(?![' + _KANJI + r'])'
                )
            else:
                pattern = re.compile(escaped + r'(?![' + _KANJI + r'])')
        else:
            pattern = re.compile(escaped)
        patterns.append((pattern, reading))

    logger.info(f"📖 TTS辞書読み込み完了: {len(patterns)}件 ({dict_file})")
    return patterns


def _amplify_wav(wav_data: bytes, volume: float) -> bytes:
    """
    WAVデータの音量を volume 倍に増幅して返す。
    volume=1.0 は変化なし、2.0 で2倍に増幅。
    numpy が使える場合は numpy で、なければ struct で処理する。
    """
    if abs(volume - 1.0) < 0.01:
        return wav_data

    try:
        with wave.open(io.BytesIO(wav_data), "rb") as wf:
            params = wf.getparams()
            frames = wf.readframes(wf.getnframes())
            sampwidth = wf.getsampwidth()

        # 16bit PCM のみ対応（VOICEVOXは常に16bit）
        if sampwidth != 2:
            return wav_data

        try:
            import numpy as np
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
            samples *= volume
            # クリッピング（-32768〜32767 に収める）
            samples = np.clip(samples, -32768, 32767)
            amplified = samples.astype(np.int16).tobytes()
        except ImportError:
            # numpy がない場合は struct で処理
            n = len(frames) // 2
            samples_list = list(struct.unpack(f'<{n}h', frames))
            amplified_list = [max(-32768, min(32767, int(s * volume))) for s in samples_list]
            amplified = struct.pack(f'<{n}h', *amplified_list)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as out:
            out.setparams(params)
            out.writeframes(amplified)
        return buf.getvalue()

    except Exception as e:
        logger.warning(f"⚠️ WAV増幅エラー（元データで送信）: {e}")
        return wav_data


class TTSBridge:
    """VOICEVOX / Style-Bert-VITS2 両対応 TTS ブリッジ"""

    def __init__(self, config: dict):
        tts_config = config.get("tts", {})

        self._provider = tts_config.get("provider", "voicevox").strip().lower()

        # VOICEVOX設定
        self._vv_endpoint  = tts_config.get("voicevox_endpoint", "http://localhost:50021")
        self._vv_mia_id    = tts_config.get("mia_speaker_id", 3)
        self._vv_master_id = tts_config.get("master_speaker_id", 2)
        self._vv_speed     = tts_config.get("speed_scale", 1.0)
        self._vv_pitch     = tts_config.get("pitch_scale", 0.0)

        # SBV2設定
        self.endpoint           = tts_config.get("endpoint", "http://localhost:5000")
        self.default_model_name = tts_config.get("mia_model_name", "woman001")
        self.speed              = tts_config.get("speed", 1.0)
        self.style_weight       = tts_config.get("style_weight", 1.0)

        # 音量増幅（1.0 = 変化なし、2.0 = 2倍）
        self._volume = float(tts_config.get("volume", 1.0))

        # 読み辞書
        dict_file = tts_config.get("dict_file", "tts_dict.yaml")
        self._dict_patterns = _load_dict(dict_file)

        self._session: aiohttp.ClientSession | None = None
        logger.info(f"🔊 TTSBridge: provider={self._provider}, volume={self._volume}")

    def _apply_dict(self, text: str) -> str:
        for pattern, reading in self._dict_patterns:
            text = pattern.sub(reading, text)
        return text

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30, connect=10)
            )
        return self._session

    async def synthesize(self, text: str, model_name: str = None, speaker: str = "mia") -> dict | None:
        if not text.strip():
            return None

        text = self._apply_dict(text)
        text = _clean_for_tts(text)
        if not text:
            return None

        if self._provider == "voicevox":
            return await self._synthesize_voicevox(text, speaker)
        else:
            return await self._synthesize_sbv2(text, model_name)

    async def _synthesize_voicevox(self, text: str, speaker: str = "mia") -> dict | None:
        speaker_id = self._vv_mia_id if speaker == "mia" else self._vv_master_id
        session = await self._get_session()

        try:
            async with session.post(
                f"{self._vv_endpoint}/audio_query",
                params={"text": text, "speaker": speaker_id},
            ) as resp:
                if resp.status != 200:
                    logger.error(f"❌ VOICEVOX audio_query エラー: {resp.status}")
                    return None
                query = await resp.json()

            query["speedScale"] = self._vv_speed
            query["pitchScale"] = self._vv_pitch

            async with session.post(
                f"{self._vv_endpoint}/synthesis",
                params={"speaker": speaker_id},
                json=query,
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status != 200:
                    logger.error(f"❌ VOICEVOX synthesis エラー: {resp.status}")
                    return None
                audio_data = await resp.read()

            # サーバー側で音量増幅
            audio_data = _amplify_wav(audio_data, self._volume)

            duration = self._calc_duration(audio_data)
            logger.info(f"🔊 VOICEVOX合成: [id={speaker_id}] {text[:20]}... ({duration:.1f}s, vol={self._volume})")
            return {"audio": audio_data, "duration": duration}

        except aiohttp.ClientError as e:
            logger.error(f"❌ VOICEVOX 通信エラー: {e}")
            return None
        except asyncio.TimeoutError:
            logger.error("❌ VOICEVOX タイムアウト")
            return None

    async def _synthesize_sbv2(self, text: str, model_name: str = None) -> dict | None:
        model = model_name or self.default_model_name
        session = await self._get_session()

        params = {
            "text":         text,
            "model_name":   model,
            "length":       self.speed,
            "style_weight": self.style_weight,
        }

        try:
            async with session.get(f"{self.endpoint}/voice", params=params) as resp:
                if resp.status != 200:
                    logger.error(f"❌ SBV2 API エラー: {resp.status}")
                    return None
                audio_data = await resp.read()

                # サーバー側で音量増幅
                audio_data = _amplify_wav(audio_data, self._volume)

                duration = self._calc_duration(audio_data)
                logger.info(f"🔊 SBV2合成: [{model}] {text[:20]}... ({duration:.1f}s, vol={self._volume})")
                return {"audio": audio_data, "duration": duration}

        except aiohttp.ClientError as e:
            logger.error(f"❌ SBV2 通信エラー: {e}")
            return None
        except asyncio.TimeoutError:
            logger.error("❌ SBV2 タイムアウト")
            return None

    def _calc_duration(self, wav_data: bytes) -> float:
        try:
            with wave.open(io.BytesIO(wav_data), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / rate if rate > 0 else 0.0
        except Exception:
            try:
                return (len(wav_data) - 44) / (24000 * 2)
            except Exception:
                return 2.0

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
