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

### フォント

| フォント | ライセンス |
|---|---|
| [PixelMplus](https://itouhiro.hatenablog.com/entry/20130602/font)（M+ FONTS派生） | [M+ FONTS LICENSE](https://mplusfonts.osdn.jp/) — 再配布・改変・商用利用自由、著作権表示不要 |

### 外部サービス

| サービス | 利用規約 |
|---|---|
| [VOICEVOX](https://voicevox.hiroshiba.jp/) | [VOICEVOX利用規約](https://voicevox.hiroshiba.jp/term/) — キャラクターごとに個別規約あり |
| [Gemini API](https://ai.google.dev/) | [Google AI利用規約](https://ai.google.dev/gemini-api/terms) |
| [Open-Meteo](https://open-meteo.com/) | [CC BY 4.0](https://open-meteo.com/en/terms) — 天気データ取得に使用 |

VOICEVOXの各キャラクターには個別の利用規約があります。商用利用可否やクレジット表記の要否はキャラクターごとに異なるため、使用するキャラクターの規約を必ずご確認ください。
