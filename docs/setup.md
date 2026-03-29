# Cafe Lumiere セットアップガイド

## 目次

1. [必要なもの](#必要なもの)
2. [クイックスタート](#クイックスタート)
3. [LLM設定](#llm設定)
4. [TTS設定（音声）](#tts設定音声)
5. [BGM設定](#bgm設定)
6. [アセット準備](#アセット準備)
   - [背景・風景画像](#背景風景画像)
   - [キャラクター画像](#キャラクター画像)
7. [キャラクター設定](#キャラクター設定)
8. [ペルソナ設定](#ペルソナ設定)
9. [記憶・初期設定](#記憶初期設定)
10. [iPhoneでの利用](#iphoneでの利用)
11. [SSL / HTTPS設定](#ssl--https設定)
12. [ファイル構成まとめ](#ファイル構成まとめ)
13. [トラブルシューティング](#トラブルシューティング)

---

## 必要なもの

| 項目 | 内容 |
|------|------|
| Python | 3.11以上 |
| VOICEVOX | 無料・要インストール（CPU動作） |
| LLM | Gemini APIキー（推奨）/ ローカルLLM / OpenAI API |
| OS | Windows / macOS / Linux |
| GPU | 不要 |

---

## クイックスタート

```bash
# 1. パッケージインストール
pip install -r requirements.txt

# 2. VOICEVOXを起動（アプリを起動してそのまま放置）

# 3. 設定ファイルを作成
cp config.yaml.example config.yaml

# 4. config.yaml を編集してGemini APIキーを設定
#    gemini.api_key に取得したキーを貼り付ける

# 5. 起動
python main.py

# 6. ブラウザで開く（スマホは横画面推奨）
#    http://localhost:8766/
```

---

## LLM設定

`config.yaml` の `llm` セクションで使用するLLMを選択します。

### Gemini API（推奨）

```yaml
llm:
  provider: "gemini"
  gemini_model: "gemini-2.0-flash"

gemini:
  api_key: "YOUR_GEMINI_API_KEY"   # https://aistudio.google.com/ で取得
```

### OpenAI API

```yaml
llm:
  provider: "openai"
  endpoint: "https://api.openai.com/v1/chat/completions"
  api_key: "sk-..."
  model: "gpt-4o-mini"
```

### llama.cpp / LM Studio

```yaml
llm:
  provider: "openai"
  endpoint: "http://localhost:8080/v1/chat/completions"
  api_key: ""
  model: "default"
```

### Ollama

```yaml
llm:
  provider: "openai"
  endpoint: "http://localhost:11434/v1/chat/completions"
  api_key: ""
  model: "llama3.2"
```

---

## TTS設定（音声）

### VOICEVOX（推奨）

1. [VOICEVOX](https://voicevox.hiroshiba.jp/) をダウンロード・インストール
2. アプリを起動（`http://localhost:50021` で待受）
3. `config.yaml` に話者IDと音量を設定

```yaml
tts:
  provider: "voicevox"
  voicevox_endpoint: "http://localhost:50021"
  mia_speaker_id: 3      # chara1の話者ID
  master_speaker_id: 2   # chara2の話者ID
  speed_scale: 1.0       # 話速（0.5〜2.0）
  pitch_scale: 0.0       # ピッチ（-0.15〜0.15）
  volume: 1.0            # TTS音量増幅（1.0=変化なし、3.0=3倍）
```

**話者IDの確認方法:**
VOICEVOXを起動した状態で `http://localhost:50021/speakers` にアクセスすると全話者のIDが確認できます。`styles[].id` の値を使用します。

### TTS音量について

VOICEVOXが生成するWAVデータの録音レベルは話者ごとに異なります。特に低い声の話者はレベルが低く、iOSでは聞こえにくい場合があります。`tts.volume` を上げることでサーバー側でWAVデータを直接増幅します。

| `tts.volume` | 効果 |
|---|---|
| `1.0` | 変化なし（デフォルト） |
| `2.0` | 2倍に増幅 |
| `3.0` | 3倍に増幅（推奨上限） |
| `5.0`以上 | 声が割れ始める場合がある |

### Style-Bert-VITS2（上級者向け）

```yaml
tts:
  provider: "sbv2"
  endpoint: "http://localhost:5000"
  mia_model_name: "your_mia_model"
  master_model_name: "your_master_model"
  speed: 1.0
  style_weight: 1.0
  volume: 1.0
```

### TTS読み辞書

`tts_dict.yaml` に単語と読みを追記することで、英単語や固有名詞の誤読を防げます。

```yaml
words:
  YouTube: ゆーちゅーぶ
  API: えーぴーあい
```

---

## BGM設定

BGMは時間帯ごとに最大3ファイルまで設定できます。
ファイルは `assets/bgm/` フォルダに配置してください（著作権フリー素材を各自用意）。

```yaml
bgm:
  enabled: false   # サーバー側pygame再生は無効（ブラウザ側で再生）
  volume: 0.3      # BGM音量（0.0〜1.0）
  schedules:
    - file: "assets/bgm/bgm_morning.mp3"
      start: 6     # 6時〜
    - file: "assets/bgm/bgm_day.mp3"
      start: 13    # 13時〜
    - file: "assets/bgm/bgm_night.mp3"
      start: 22    # 22時〜
```

BGMを1ファイルのみにする場合：

```yaml
bgm:
  volume: 0.3
  schedules:
    - file: "assets/bgm/bgm.mp3"
      start: 0
```

---

## アセット準備

```
assets/
  bgm/           BGM音声ファイル（.mp3）
  image/         背景・風景画像
  character/     キャラクター画像
```

### 背景・風景画像

`assets/image/` フォルダに配置します。

```yaml
scene_images:
  bg_indoor: "bg_indoor.png"
  obj_mid:   "obj_mid.png"
  obj_front: "obj_front.png"
  scenery:
    day:       "scenery_day.png"       # 昼（6〜16時・晴れ）
    dawn:      "scenery_dawn.png"      # 夜明け（4〜6時）
    evening:   "scenery_evening.png"   # 夕方（16〜19時）
    night:     "scenery_night.png"     # 夜（19〜23時）
    latenight: "scenery_latenight.png" # 深夜（23〜4時）
    cloudy:    "scenery_cloudy.png"    # 曇り
    rain:      "scenery_rain.png"      # 雨
```

**画像仕様:** サイズ 960×540px（16:9）推奨・PNG形式

**天気連動設定（任意）:**

```yaml
weather:
  enabled: true
  latitude: 35.6762
  longitude: 139.6503
  fetch_interval: 1800
```

---

### キャラクター画像

`assets/character/` フォルダに配置します。

**描画レイヤーの説明:**

```
Layer 2  キャラクター背面位置
Layer 3  キャラクター中間位置
Layer 5  キャラクター前面位置（手前の立ち絵）
```

**画像仕様:** 960×540px・PNG（背景透過推奨）

---

## キャラクター設定

```yaml
characters:
  chara1:
    pool:
      - file: "chara1_a.png"
        layer: 5
      - file: "chara1_b.png"
        layer: 2
        condition: sunny_daytime   # 晴れの昼〜夕方のみ
    late_night_pool:
      - file: "chara1_sleep.png"
        layer: 2

  chara2:
    pool:
      - file: "chara2_front.png"
        layer: 3
      - file: "chara2_back.png"
        layer: 3
```

**`condition` の値:**

| 値 | 説明 |
|----|------|
| 省略 | 常時 |
| `sunny_daytime` | 晴れの11〜19時のみ |
| `late_night` | 深夜23〜6時のみ |

---

## ペルソナ設定

`persona.yaml` でキャラクターの名前・性格・口調・プロンプトを設定します。詳細は [docs/customization.md](customization.md) を参照してください。

---

## 記憶・初期設定

```yaml
memory:
  db_path: "data/memory.db"
  extract_interval: 5
  max_memories_in_prompt: 10
  initial_memories:
    - category: fact
      content: "名前はまだ知らない"
```

記憶は `http://localhost:8767/` の管理画面で確認・編集できます。

---

## iPhoneでの利用

iPhoneからマイク入力を使う場合は **Chrome でPWAとしてホーム画面に追加する**のが確実です。

1. iPhone の **Chrome** でアプリのURL（https）を開く
2. アドレスバー右の共有ボタン → **「ホーム画面に追加」**
3. ホーム画面のアイコンから起動 → フルスクリーン＋マイク入力OK

**Safari を推奨しない理由:**
- Safari でURLを直接開く → アドレスバーで画面下部が切れてマイクボタンが表示されない
- Safari でPWAとして起動 → Web Speech APIが正常に動作しないケースがある

---

## SSL / HTTPS設定

iOSでマイクを使用するにはhttpsが必要です。

```yaml
ssl:
  cert: "/path/to/cert.pem"
  key:  "/path/to/key.pem"
```

**Tailscaleを使う場合:**
MagicDNS + HTTPS Certificates 機能で Let's Encrypt の証明書を自動取得・更新できます。

---

## ファイル構成まとめ

```
Cafe-Lumiere-dist/
├── config.yaml              ★ 起動前に必ず設定
├── config.yaml.example      設定テンプレート
├── persona.yaml             キャラクター設定・プロンプト
├── themes.yaml              会話テーマ
├── tts_dict.yaml            TTS読み辞書
├── requirements.txt
├── main.py
│
├── assets/
│   ├── bgm/                 ★ BGM（各自用意）
│   ├── image/               背景・風景画像（サンプル同梱）
│   └── character/           キャラクター画像（サンプル同梱）
│
├── data/
│   └── memory.db            会話記憶（自動生成）
│
├── docs/
│   ├── setup.md             このドキュメント
│   └── customization.md     世界観カスタマイズガイド
│
├── frontend/
└── src/
```

---

## トラブルシューティング

**音声が出ない**
→ VOICEVOXが起動しているか確認。`http://localhost:50021/version` でバージョンが表示されればOK。

**iPhoneでマイクが動かない**
→ Safari ではなく **Chrome** でアクセスし、PWAとしてホーム画面に追加してください。https接続が必要です（上記SSL設定を参照）。

**マイクが動かない（PC）**
→ ブラウザのアドレスバーのカメラアイコンからマイクのアクセス許可を確認してください。

**LLMが応答しない**
→ `config.yaml` の `llm.endpoint` と `api_key` を確認。Ollamaの場合は `model` にモデル名が必要です。

**画像が表示されない**
→ `assets/image/` と `assets/character/` のファイル名が `config.yaml` の `scene_images` / `characters` セクションと一致しているか確認してください。

**BGMが流れない**
→ 最初のタップ/クリックで有効になります（ブラウザのautoplay制限のため）。`assets/bgm/` にファイルが存在するか確認してください。

**TTSの音量が小さい / BGMとのバランスが悪い**
→ `config.yaml` の以下2箇所で調整してください。

```yaml
bgm:
  volume: 0.3    # BGM音量（0.0〜1.0）

tts:
  volume: 1.0    # TTS音量（1.0=変化なし、3.0=3倍に増幅）
```

iOSでTTSが特に小さく聞こえる背景：iOSはBGMとTTSが別オーディオセッションになるとOSレベルでTTS音量を自動ダッキング（低減）する仕様があります。本アプリはBGM・TTSを同一の `AudioContext` 経由で再生することでこれを緩和していますが、VOICEVOXの録音レベルは話者ごとに異なるため、低い声の話者では音量が小さく聞こえるケースがあります。

`tts.volume` はサーバー側でWAVデータを直接増幅するため、ブラウザやOS側の制約に関係なく効果があります。本体音量を最大にした上で `3.0` 程度が実用的な上限の目安です（`5.0` 以上では声が割れ始める場合があります）。
