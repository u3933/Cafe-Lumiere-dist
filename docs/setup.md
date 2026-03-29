# Cafe Lumiere セットアップガイド

## 目次

1. [必要なもの](#必要なもの)
2. [クイックスタート](#クイックスタート)
3. [セットアップウィザードの使い方](#セットアップウィザードの使い方)
4. [LLM設定](#llm設定)
5. [TTS設定（音声）](#tts設定音声)
6. [BGM設定](#bgm設定)
7. [アセット準備](#アセット準備)
8. [キャラクター設定](#キャラクター設定)
9. [ペルソナ設定](#ペルソナ設定)
10. [記憶・初期設定](#記憶初期設定)
11. [iPhoneでの利用](#iphoneでの利用)
12. [SSL / HTTPS設定](#ssl--https設定)
13. [ファイル構成まとめ](#ファイル構成まとめ)
14. [トラブルシューティング](#トラブルシューティング)

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

# 3. アプリ起動（config.yaml がなければ自動コピーされる）
python main.py

# 4. セットアップウィザードで設定
#    http://localhost:8766/setup_wizard/

# 5. ダウンロードしたYAMLをプロジェクトルートに配置してから再起動
python main.py

# 6. ブラウザで開く（スマホは横画面推奨）
#    http://localhost:8766/
```

---

## セットアップウィザードの使い方

`http://localhost:8766/setup_wizard/` をブラウザで開くと、GUIで設定できます。

### ⚙️ 環境設定タブ（config.yaml を生成）

**LLM設定**
使用するLLMプロバイダーを選択します。

| プロバイダー | 概要 |
|---|---|
| Gemini API | 推奨。APIキーのみで動作。簡単 |
| OpenAI API | APIキーとモデル名を設定 |
| ローカルLLM | llama.cpp / LM Studio / Ollamaのエンドポイントを指定 |

**🔍 Google検索（今日の話題）**
LLMの設定に関係なく、放置時の話題リアルタイム取得には常にGemini APIを使用します。APIキーが未設定の場合は今日の話題が生成されないだけで、その他の機能は正常に動作します。

**TTS設定**
- VOICEVOX を選択した場合：話者IDをウィザード内で音声テスト（chara1 / chara2）して確認できます
- Style-Bert-VITS2 を選択した場合：モデル名と話速を設定できます

**BGM設定**
スケジュールを設定しウィザード内で再生テストできます。

**背景・風景画像 / キャラクター画像**
ファイル名を入力し👁ボタンを押すとレイヤープレビューで重なり具合を確認できます。入力した値はそのまま `config.yaml` の `scene_images` / `characters` セクションに出力されます。

右パネルにリアルタイムでYAMLプレビューが表示されます。「コピー」または「ダウンロード」でファイルを取得してください。

### 🎭 AIペルソナ設定タブ（persona.yaml を生成）

キャラクターの名前・一人称・説明・口調・禁止事項、worldセクション（呼びかけキーワード・ウェルカムメッセージ・フォールバック掛け合い）を設定します。プロンプトは舞台設定とキャラ名から自動生成されます。

### 🌏 世界観設定タブ（themes.yaml を生成）

放置時にキャラクターが自律的に話す話題テーマを追加・編集・削除できます。

### VPS・リモート環境での使い方

VPS上で `main.py` を稼働させ、クライアントPCのブラウザから `http://VPSのIPアドレス:8766/setup_wizard/` にアクセスすることで、リモート設定が可能です。

- YAMLはブラウザにダウンロードされるため、SCP等でVPSに転送して配置してください
- TTS・BGM音声テスト・画像プレビューはVPS上のアセットを参照して動作します

---

## LLM設定

`config.yaml` の `llm` セクションで使用するLLMを選択します。ウィザードでの設定を推奨しますが、手動編集も可能です。

### Gemini API（推奨）

```yaml
llm:
  provider: "gemini"
  gemini_model: "gemini-2.0-flash"

gemini:
  api_key: "YOUR_GEMINI_API_KEY"   # https://aistudio.google.com/ で取得
  grounding: true
  fetch_interval: 3600
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

### ローカルLLM + Google検索（今日の話題）の組み合わせ

ローカルLLMで会話を生成しつつ、今日の話題リアルタイム取得だけGemini APIを使う構成が可能です。

```yaml
llm:
  provider: "openai"
  endpoint: "http://localhost:8080/v1/chat/completions"
  api_key: ""
  model: "default"

# Google検索（今日の話題）— LLM設定に関係なく常にGemini APIを使用
gemini:
  api_key: "YOUR_GEMINI_API_KEY"
  model: "gemini-2.0-flash"
  grounding: true
  fetch_interval: 3600
```

`gemini.api_key` が空の場合は `ThemeFetcher` が無効化され、`themes.yaml` の静的テーマのみが使用されます。エラーにはなりません。

---

## TTS設定（音声）

### VOICEVOX（推奨）

1. [VOICEVOX](https://voicevox.hiroshiba.jp/) をダウンロード・インストール
2. アプリを起動（`http://localhost:50021` で待受）
3. ウィザードの音声テストで話者IDを確認しながら設定

```yaml
tts:
  provider: "voicevox"
  voicevox_endpoint: "http://localhost:50021"
  mia_speaker_id: 3      # chara1の話者ID
  master_speaker_id: 2   # chara2の話者ID
  speed_scale: 1.0       # 話速（0.5〜2.0）
  pitch_scale: 0.0       # ピッチ（-0.15〜0.15）
  volume: 1.0            # TTS音量増幅（1.0=変化なし、3.0=3倍）
  dict_file: "tts_dict.yaml"
```

**話者IDの確認方法:**
VOICEVOXを起動した状態で `http://localhost:50021/speakers` にアクセスすると全話者のIDが確認できます。`styles[].id` の値を使用します。ウィザードの音声テストで実際に再生して確認するのが最も確実です。

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
  volume: 1.0
  dict_file: "tts_dict.yaml"
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

BGMは時間帯ごとに複数ファイル設定できます。ファイルは `assets/bgm/` フォルダに配置してください（著作権フリー素材を各自用意）。

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

`assets/image/` フォルダに配置します。ウィザードの👁ボタンでレイヤープレビューを確認しながら設定できます。

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

緯度経度はウィザードの地域名検索で自動入力できます。

---

### キャラクター画像

`assets/character/` フォルダに配置します。ウィザードで複数画像とレイヤー・conditionを設定できます。

**描画レイヤーの説明:**

```
Layer 2  キャラクター背面位置
Layer 3  キャラクター中間位置
Layer 5  キャラクター前面位置（手前の立ち絵）
```

**画像仕様:** 960×540px・PNG（背景透過推奨）

---

## キャラクター設定

ウィザードで設定するか、`config.yaml` に直接記述します。

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

`persona.yaml` でキャラクターの名前・性格・口調・プロンプトを設定します。ウィザードの「AIペルソナ設定」タブで生成するのを推奨します。詳細は [docs/customization.md](customization.md) を参照してください。

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

iOSでマイクを使用するにはhttpsが必要です。ウィザードで生成した `config.yaml` にはSSLセクションがコメントアウトで含まれています。

```yaml
# SSL（Tailscaleなどで証明書を取得した場合に設定）
# ssl:
#   cert: "/path/to/cert.pem"
#   key:  "/path/to/key.pem"
```

コメントを外してパスを設定すると有効になります。

**Tailscaleを使う場合:**
MagicDNS + HTTPS Certificates 機能で Let's Encrypt の証明書を自動取得・更新できます。

---

## ファイル構成まとめ

```
Cafe-Lumiere-dist/
├── config.yaml              ★ ウィザードで生成・配置
├── config.yaml.example      設定テンプレート（起動時に自動コピー）
├── persona.yaml             ★ ウィザードで生成・配置
├── themes.yaml              ★ ウィザードで生成・配置
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
├── setup_wizard/
│   └── index.html           セットアップウィザード
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
→ `assets/image/` と `assets/character/` のファイル名が `config.yaml` の `scene_images` / `characters` セクションと一致しているか確認してください。ウィザードのレイヤープレビューで確認できます。

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
