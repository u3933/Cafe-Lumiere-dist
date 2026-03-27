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
  endpoint: "http://localhost:8080/v1/chat/completions"  # llama.cpp
  # endpoint: "http://localhost:1234/v1/chat/completions"  # LM Studio
  api_key: ""       # 不要
  model: "default"
```

### Ollama

```yaml
llm:
  provider: "openai"
  endpoint: "http://localhost:11434/v1/chat/completions"
  api_key: ""
  model: "llama3.2"   # 起動中のモデル名を指定
```

---

## TTS設定（音声）

### VOICEVOX（推奨）

1. [VOICEVOX](https://voicevox.hiroshiba.jp/) をダウンロード・インストール
2. アプリを起動（`http://localhost:50021` で待受）
3. `config.yaml` に話者IDを設定

```yaml
tts:
  provider: "voicevox"
  voicevox_endpoint: "http://localhost:50021"
  mia_speaker_id: 3      # chara1（りん）の話者ID
  master_speaker_id: 2   # chara2（マスター）の話者ID
  speed_scale: 1.0       # 話速（0.5〜2.0）
  pitch_scale: 0.0       # ピッチ（-0.15〜0.15）
```

**話者IDの確認方法:**
VOICEVOXを起動した状態で `http://localhost:50021/speakers` にアクセスすると全話者のIDが確認できます。

### Style-Bert-VITS2（上級者向け）

```yaml
tts:
  provider: "sbv2"
  endpoint: "http://localhost:5000"
  mia_model_name: "your_mia_model"
  master_model_name: "your_master_model"
  speed: 1.0
  style_weight: 1.0
```

### TTS読み辞書

`tts_dict.yaml` に単語と読みを追記することで、英単語や固有名詞の誤読を防げます。

```yaml
words:
  YouTube: ゆーちゅーぶ
  API: えーぴーあい
  YourCharaName: よみがな
```

---

## BGM設定

BGMは時間帯ごとに最大3ファイルまで設定できます。
ファイルは `assets/bgm/` フォルダに配置してください（著作権フリー素材を各自用意）。

```yaml
bgm:
  volume: 0.3        # 音量（0.0〜1.0）
  schedules:
    - file: "assets/bgm/cafe_bgm_morning.mp3"
      start: 6       # 6時〜
    - file: "assets/bgm/cafe_bgm.mp3"
      start: 13      # 13時〜
    - file: "assets/bgm/cafe_bgm_night.mp3"
      start: 22      # 22時〜
```

**BGMを1ファイルのみにする場合:**

```yaml
bgm:
  volume: 0.3
  schedules:
    - file: "assets/bgm/cafe_bgm.mp3"
      start: 0
```

---

## アセット準備

画像ファイルはすべて著作権フリーの素材を各自用意してください。
以下のフォルダ構成で配置します。

```
assets/
  bgm/           BGM音声ファイル（.mp3）
  image/         背景・風景画像
  character/     キャラクター画像
```

### 背景・風景画像

`assets/image/` フォルダに配置します。
ファイル名は `config.yaml` の `scene_images` セクションで自由に設定できます。

```yaml
scene_images:
  bg_indoor: "bg_indoor.png"     # 室内背景（常時表示）
  obj_mid:   "obj_mid.png"       # 中景オブジェクト（常時表示・省略可）
  obj_front: "obj_front.png"     # 前景オブジェクト（常時表示・省略可）
  scenery:
    day:       "scenery_day.png"       # 昼（6〜16時・晴れ）
    dawn:      "scenery_dawn.png"      # 夜明け（4〜6時）
    evening:   "scenery_evening.png"   # 夕方（16〜19時）
    night:     "scenery_night.png"     # 夜（19〜23時）
    latenight: "scenery_latenight.png" # 深夜（23〜4時）
    cloudy:    "scenery_cloudy.png"    # 曇り
    rain:      "scenery_rain.png"      # 雨
```

**画像仕様:**
- サイズ: **960×540px**（16:9）推奨
- 形式: PNG
- 風景画像は天気・時間帯で自動切り替えされます
- `obj_mid` / `obj_front` はカウンターや小物など前景に重ねるオブジェクト用です。不要であればファイルを透明PNGにしてください

**天気連動設定（任意）:**

天気はOpen-Meteo API（無料・APIキー不要）から自動取得できます。

```yaml
weather:
  enabled: true
  latitude: 35.6762    # 緯度（東京の例）
  longitude: 139.6503  # 経度（東京の例）
  fetch_interval: 1800 # 更新間隔（秒）
```

---

### キャラクター画像

`assets/character/` フォルダに配置します。
ファイル名・枚数・描画レイヤーはすべて `config.yaml` の `characters` セクションで設定します。

**描画レイヤーの説明:**

```
Layer 0  風景（背景）
Layer 1  室内背景（bg_indoor）
Layer 2  キャラクター背面位置（カウンター内・後ろの立ち絵など）
Layer 3  キャラクター中間位置（カウンター越しなど）
Layer 4  中景オブジェクト（obj_mid）
Layer 5  キャラクター前面位置（手前の立ち絵）
Layer 6  前景オブジェクト（obj_front）
Layer 7  ユーザー画像
```

数字が大きいほど手前に表示されます。

**画像仕様:**
- サイズ: **960×540px**（16:9）推奨
- 形式: PNG（背景透過推奨）
- キャラクターは背景を透明にし、立ち位置のみ描いたPNGを用意します

---

## キャラクター設定

`config.yaml` の `characters` セクションで、2キャラ（`chara1` / `chara2`）の画像プールを設定します。各キャラ最大6枚まで登録できます。

```yaml
characters:
  chara1:
    # 通常時のランダムプール（最大6枚）
    pool:
      - file: "rin_mid_1.png"       # ファイル名（assets/character/ 以下）
        layer: 5                     # 描画レイヤー（2 / 3 / 5 のいずれか）
      - file: "rin_mid_2.png"
        layer: 5
      - file: "rin_mid_3.png"
        layer: 5
      - file: "rin_back_clean.png"
        layer: 2
      - file: "rin_back_rest.png"
        layer: 2
        condition: sunny_daytime     # 出現条件（省略時は常時）

    # 深夜専用プール（省略時は通常プールをそのまま使用）
    late_night_pool:
      - file: "rin_back_sleep.png"
        layer: 2

  chara2:
    pool:
      - file: "master_front.png"
        layer: 3
      - file: "master_back.png"
        layer: 3
```

### `condition`（出現条件）

| 値 | 説明 |
|----|------|
| 省略 | 常時プールに含まれる |
| `sunny_daytime` | 晴れの昼〜夕方（11〜19時）のみ出現 |
| `late_night` | 深夜帯（23〜6時）のみ出現 |

### `late_night_pool`

深夜帯（23〜6時）に使用する専用プールです。省略した場合は通常の `pool` をそのまま使用します。眠っているポーズなど深夜専用の立ち絵を設定するのに使います。

### キャラ切り替えのタイミング

- `chara1` は30〜60秒ごとにランダムで切り替わります
- `chara2` は60〜180秒ごとにランダムで切り替わります
- 切り替え時はフェードアウト→フェードインのアニメーションが入ります

---

## ペルソナ設定

`persona.yaml` でキャラクターの名前・性格・口調・プロンプトを設定します。

```yaml
mia:
  name: "Mia"
  description: "カフェのスタッフ。明るくフレンドリー。"
  first_person: "わたし"
  tone: |
    感情や感覚をそのまま口に出す。理由や説明は付け加えない。
    「あ、それいいな！」「なんか好き」のように短く反応する。
  forbidden:
    - "説明的な長文"
    - "1応答2文まで"

master:
  name: "Master"
  description: "カフェのオーナー。言葉数は少ないが的を射る。"
  first_person: "ぼく"
  tone: |
    言葉数は少ない。断言するか、静かに問いかけるか、どちらか。
  forbidden:
    - "長い文で説明しない"
    - "1〜2文まで"
```

会話テーマは `themes.yaml` で設定します（動的テーマ取得にはGemini APIキーが必要）。

---

## 記憶・初期設定

アプリはユーザーとの会話から自動的に記憶を蓄積します。
初回起動時に投入する初期記憶を `config.yaml` で設定できます。

```yaml
memory:
  db_path: "data/memory.db"
  extract_interval: 5          # 何ターンごとに記憶を抽出するか
  max_memories_in_prompt: 10   # プロンプトに含める記憶の最大件数
  initial_memories:
    - category: fact
      content: "名前はまだ知らない"
    - category: preference
      content: "コーヒーが好きそう"
```

**記憶カテゴリ:**

| カテゴリ | 内容 |
|----------|------|
| `fact` | ユーザーに関する事実（職業・趣味など） |
| `preference` | 好み（飲み物・話題など） |
| `topic` | 会話した話題 |
| `event` | 出来事（ゲーム結果など） |

記憶は `http://localhost:8767/` の管理画面で確認・編集できます。

---

## iPhoneでの利用

iPhoneからマイク入力を使う場合は **Chrome でPWAとしてホーム画面に追加する**のが確実です。

**手順:**

1. iPhone の **Chrome** でアプリのURL（https）を開く
2. アドレスバー右の共有ボタン → **「ホーム画面に追加」**
3. ホーム画面のアイコンから起動 → フルスクリーン＋マイク入力OK

**Safari を推奨しない理由:**

- Safari でURLを直接開く → アドレスバーで画面下部が切れ、マイクボタンが表示されない
- Safari でPWAとして起動 → フルスクリーンになるが、Web Speech APIが正常に動作しないケースがある

Chrome PWAとしてインストールすることでフルスクリーン表示とマイク入力の両方が解決します。

https接続の設定方法は次のSSL設定セクションを参照してください。

---

## SSL / HTTPS設定

iOSでマイクを使用するにはhttpsが必要です。
Tailscaleなどで証明書を取得した場合、`config.yaml` の `ssl` セクションを有効化してください。

```yaml
ssl:
  cert: "/path/to/cert.pem"
  key:  "/path/to/key.pem"
```

証明書を設定するとWebSocketも自動的に `wss://` に切り替わります。

**Tailscaleを使う場合:**

Tailscale の MagicDNS + HTTPS Certificates 機能を使うと、Let's Encrypt の証明書を自動取得・更新できます。ローカルネットワーク内のPCへスマホから接続する際に便利です。

---

## ファイル構成まとめ

```
Cafe-Lumiere-dist/
├── config.yaml              ★ 起動前に必ず設定（config.yaml.exampleをコピーして作成）
├── config.yaml.example      設定テンプレート
├── persona.yaml             キャラクター設定・プロンプト
├── themes.yaml              会話テーマ
├── tts_dict.yaml            TTS読み辞書
├── requirements.txt         依存パッケージ
├── main.py                  起動スクリプト
│
├── assets/
│   ├── bgm/                 ★ BGM音声ファイル（各自用意）
│   │   ├── cafe_bgm.mp3
│   │   ├── cafe_bgm_morning.mp3
│   │   └── cafe_bgm_night.mp3
│   ├── image/               背景・風景画像（サンプル同梱）
│   │   ├── bg_indoor.png        室内背景
│   │   ├── obj_mid.png          中景オブジェクト
│   │   ├── obj_front.png        前景オブジェクト
│   │   ├── scenery_day.png      昼の風景
│   │   ├── scenery_dawn.png     夜明けの風景
│   │   ├── scenery_evening.png  夕方の風景
│   │   ├── scenery_night.png    夜の風景
│   │   ├── scenery_latenight.png 深夜の風景
│   │   ├── scenery_cloudy.png   曇りの風景
│   │   └── scenery_rain.png     雨の風景
│   └── character/           キャラクター画像（サンプル同梱）
│       ├── rin_mid_1.png        （chara1 デフォルト設定）
│       ├── rin_mid_2.png
│       ├── rin_mid_3.png
│       ├── rin_back_clean.png
│       ├── rin_back_rest.png
│       ├── rin_back_sleep.png   （深夜専用）
│       ├── master_front.png     （chara2 デフォルト設定）
│       ├── master_back.png
│       ├── user_1.png           ユーザー画像（固定）
│       └── user_2.png           ユーザー画像2（固定）
│
├── data/
│   └── memory.db            会話記憶（自動生成）
│
├── docs/
│   └── setup.md             このドキュメント
│
├── frontend/                フロントエンド（変更不要）
└── src/                     バックエンド（変更不要）
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
→ 最初のタップ/クリックで有効になります（ブラウザのautoplay制限のため）。また `assets/bgm/` にファイルが存在するか確認してください。
