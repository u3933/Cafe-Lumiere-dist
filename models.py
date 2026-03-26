"""
Cafe Lumiere - データモデル定義
エージェント間でやり取りされるメッセージの型を定義。
"""
from dataclasses import dataclass, field
import time


@dataclass
class ChatMessage:
    """VoiceReceiverAgent → GeneratorAgent に渡る音声認識メッセージ"""
    user_id: str
    username: str
    message: str
    timestamp: float = field(default_factory=time.time)
    is_superchat: bool = False
    superchat_amount: int = 0


@dataclass
class TextChunk:
    """GeneratorAgent → SpeakerAgent に渡るテキストチャンク"""
    text: str
    emotion: str = "neutral"        # happy / sad / surprised / angry / relaxed / neutral
    speaker: str = "mia"            # "mia" | "master"
    is_filler: bool = False
    source_comments: list = field(default_factory=list)
