# Cafe Lumiere ☕ — 配布版 (vA1)

AIが営むカフェを舞台にした、放置型音声会話アプリ。
2キャラクター（スタッフ・オーナー）が自律的に掛け合いを行い、音声・テキストで話しかけると自然に応答します。

詳細なセットアップ手順は [docs/setup.md](docs/setup.md) を参照してください。

---

## 必要なもの

1. **Python 3.11以上**
2. **VOICEVOX**（無料）— キャラクター音声用
   - https://voicevox.hiroshiba.jp/ からダウンロード・インストール
3. **LLM** — 以下のいずれか
   - **Gemini APIキー**（推奨・簡単） — https://aistudio.google.com/
   - llama.cpp / LM Studio / Ollama（ローカルLLM）
   - OpenAI APIキー

---

## セットアップ（5ステップ）

### 1. リポジトリをダウンロード
```bash
git clone https://github.com/YOUR_USERNAME/Cafe-Lumiere-dist.git
cd Cafe-Lumiere-dist
```

### 2. Pythonパッケージをインストール
```bash
pip install -r requirements.txt
```

### 3. VOICEVOXを起動
VOICEVOXアプリを起動し、そのままにしておく（`http://localhost:50021` で待受）

### 4. config.yamlを設定
```bash
cp config.yaml.example config.yaml
```
`config.yaml` を開いてGemini APIキーを設定：

```yaml
llm:
  provider: "gemini"

gemini:
  api_key: "YOUR_GEMINI_API_KEY"  # ← ここに入力
```

### 5. 起動
```bash
python main.py
```

ブラウザで `http://localhost:8766/` を開く（スマホは横画面推奨）。

---

## LLM別の設定例

### Gemini API（推奨）
```yaml
llm:
  provider: "gemini"
gemini:
  api_key: "YOUR_GEMINI_API_KEY"
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

## アクセス先

| 用途 | URL |
|---|---|
| カフェアプリ | `http://localhost:8766/` |
| 記憶管理ツール | `http://localhost:8767/` |

- スマートフォンは横画面（landscape）で開く
- **最初のタップでBGMと音声が有効になる**（ブラウザのautoplay制限のため）

---

## GPUは不要

| コンポーネント | 動作 |
|---|---|
| LLM（Gemini API）| Googleクラウドで処理 |
| STT（Web Speech API）| ブラウザ内蔵 |
| TTS（VOICEVOX）| CPU動作 |

---

## ミニゲーム

画面右下のボタンでポップアップを開く。

| ゲーム | 難易度 |
|---|---|
| ドローポーカー | Easy / Normal / Hard |
| 神経衰弱 | Easy / Normal / Hard |
| リバーシ | Easy / Normal / Hard |

---

## アセットの配置

以下のフォルダに画像・BGMを配置してください（著作権フリー素材を各自用意）。
詳細は [docs/setup.md](docs/setup.md) を参照。

```
assets/
  bgm/         ← BGMファイル（.mp3）
  image/       ← 背景・風景画像（960×540px PNG推奨）
  character/   ← キャラクター画像（960×540px 背景透過PNG推奨）
```

サンプルアセット（`assets/` 同梱）はAI生成物を加工したものです。
著作権を主張せず、商用・非商用を問わず自由に利用・改変できます。

---

## トラブルシューティング

**VOICEVOXの音声が出ない**
→ VOICEVOXアプリが起動しているか確認。`http://localhost:50021/version` にアクセスできればOK。

**マイクが動かない**
→ ブラウザのマイク許可を確認。iOSはhttpsが必要（[docs/setup.md](docs/setup.md) のSSL設定を参照）。

**LLMがエラーを返す**
→ `config.yaml` の `llm.endpoint` と `api_key` を確認。

**Ollamaで応答しない**
→ `model` にOllamaで実行中のモデル名（例: `llama3.2`）を設定してください。

---

## ライセンス

### アプリケーションコード

本リポジトリのコード（`src/`、`frontend/`、`main.py` 等）は **MIT License** で提供します。

```
MIT License

Copyright (c) 2025 Cafe Lumiere Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### サンプルアセット

`assets/` フォルダ内のサンプルアセット（画像・BGM）はAI生成物を加工したものです。
著作権を主張せず、商用・非商用を問わず自由に利用・改変できます。

### フォント

| フォント | ライセンス |
|---|---|
| [PixelMplus](https://itouhiro.hatenablog.com/entry/20130602/font)（M+ FONTS派生） | [M+ FONTS LICENSE](https://mplusfonts.osdn.jp/) — 再配布・改変・商用利用自由、著作権表示不要 |

### 使用ライブラリ

| ライブラリ | ライセンス | 用途 |
|---|---|---|
| [aiohttp](https://github.com/aio-libs/aiohttp) | Apache 2.0 | HTTPサーバ・非同期HTTPクライアント |
| [websockets](https://github.com/python-websockets/websockets) | BSD 3-Clause | WebSocketサーバ |
| [PyYAML](https://github.com/yaml/pyyaml) | MIT | YAML設定ファイル読み込み |
| [FastAPI](https://github.com/fastapi/fastapi) | MIT | 記憶管理WebツールAPI |
| [uvicorn](https://github.com/encode/uvicorn) | BSD 3-Clause | ASGIサーバ |
| sqlite3 | Python標準ライブラリ（PSF） | 長期記憶データベース |

フロントエンドはブラウザ標準API（Web Speech API / Web Audio API / Canvas 2D）のみを使用しており、外部JavaScriptライブラリへの依存はありません。

### 外部サービス

| サービス | 利用規約 |
|---|---|
| [VOICEVOX](https://voicevox.hiroshiba.jp/) | [VOICEVOX利用規約](https://voicevox.hiroshiba.jp/term/) — キャラクターごとに個別規約あり |
| [Gemini API](https://ai.google.dev/) | [Google AI利用規約](https://ai.google.dev/gemini-api/terms) |
| [Open-Meteo](https://open-meteo.com/) | [CC BY 4.0](https://open-meteo.com/en/terms) — 天気データ取得に使用 |

VOICEVOXの各キャラクターには個別の利用規約があります。商用利用可否やクレジット表記の要否はキャラクターごとに異なるため、使用するキャラクターの規約を必ずご確認ください。
