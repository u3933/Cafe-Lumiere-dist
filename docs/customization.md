# 世界観カスタマイズガイド

このアプリはカフェ以外の世界観でも動作します。
コードを一切変更せず、以下の5種類のファイルを差し替えるだけで自分だけの空間が作れます。

---

## カスタマイズが必要なファイル一覧

| ファイル | 変更内容 |
|---|---|
| `config.yaml` | 左上ロゴ・BGMスケジュール・VOICEVOXの話者ID |
| `persona.yaml` | キャラクター設定・口調・ウェルカムメッセージ・プロンプト |
| `themes.yaml` | トークテーマ一覧 |
| `assets/image/` | 背景・風景画像 |
| `assets/character/` | キャラクター画像 |
| `assets/bgm/` | BGMファイル（任意） |

コードファイル（`src/`・`frontend/`）は変更不要です。

---

## 1. config.yaml

### 左上ロゴ

画面左上に表示されるタイトルを変更します。

```yaml
scene:
  overlay_title: "☕ Cafe Lumiere"   # ← ここを変更

# 例
# overlay_title: "🚀 Space Station Lumiere"
# overlay_title: "🔮 Magical Apothecary"
# overlay_title: "🏠 Share House 404"
```

### BGMスケジュール

時間帯ごとに異なるBGMを設定できます（最大3件）。

```yaml
bgm:
  volume: 0.3
  schedules:
    - file: "assets/bgm/bgm_morning.mp3"
      start: 6    # 6時〜
    - file: "assets/bgm/bgm_day.mp3"
      start: 13   # 13時〜
    - file: "assets/bgm/bgm_night.mp3"
      start: 22   # 22時〜
```

BGMを1種類だけにする場合：

```yaml
bgm:
  volume: 0.3
  schedules:
    - file: "assets/bgm/bgm.mp3"
      start: 0
```

### VOICEVOXの話者ID

`http://localhost:50021/speakers` にアクセスして話者IDを確認し、キャラクターに合う声を設定します。

```yaml
tts:
  mia_speaker_id: 3      # chara1の話者ID
  master_speaker_id: 2   # chara2の話者ID
```

---

## 2. persona.yaml

キャラクターの性格・口調と、世界観に関する設定をすべてここで管理します。

### キャラクター設定（`mia` / `master` セクション）

`mia` が chara1、`master` が chara2 に対応します。
キー名（`mia` `master`）は変えてはいけません。値（名前・説明・口調）は自由に書き換えられます。

```yaml
mia:
  name: "先輩"                          # ← キャラクターの名前
  description: "シェアハウスの住人。30代男性。渋くてマイペース。"
  first_person: "俺"                    # ← 一人称
  tone: |
    低めのテンションで、淡々と、でも的を射たことを言う。
    断言するか、ぽつりと感想を漏らす程度。
  forbidden:
    - "長い文での説明や説教"
    - "1〜2文まで"

master:
  name: "タカシ"
  description: "シェアハウスの住人。20代男性。元気でお調子者。"
  first_person: "俺"
  tone: |
    感情をストレートに口に出す。テンポよく短く反応する。
  forbidden:
    - "堅苦しい説明口調"
    - "1応答2文まで"
```

### 世界観設定（`world` セクション）

コードにハードコードされていた世界観の要素をすべてここで管理します。

```yaml
world:
  # chara2への呼びかけキーワード（メッセージ冒頭10文字に含まれたら chara2 が返答）
  master_keywords:
    - "タカシ"
    - "たかし"

  # 接続時のウェルカムメッセージ（通常時）
  welcome:
    - speaker: "mia"
      text: "……来たか。まあ、ゆっくりしていけ。"
    - speaker: "master"
      text: "あ、お疲れ様っす！"

  # 接続時のウェルカムメッセージ（深夜時）
  welcome_late_night:
    - speaker: "master"
      text: "……まだ起きてたのか。まあ、座れ。"

  # chara2返答後に chara1 が一言添えるプロンプト（30%の確率で発動）
  # {master_response} は必ず残すこと
  mia_followup_prompt: |
    タカシが「{master_response}」と言いました。
    先輩として一言だけ短く添えてください。1文のみ。テキストのみ出力。

  # LLM失敗・バッファ空時に使う固定掛け合い（最低2〜3パターン推奨）
  fallback_dialogues:
    - - speaker: "mia"
        text: "……飯、どうする。"
      - speaker: "master"
        text: "あ、俺コンビニ行きますよ！何か買ってきましょうか？"
    - - speaker: "mia"
        text: "お前の服、また猫の毛だらけだぞ。"
      - speaker: "master"
        text: "うわ、マジだ！さっきまで膝で寝てたんすよ〜。"
```

### プロンプト（`prompts` セクション）

各プロンプトの**文章は自由に変更できます**が、`{変数名}` のプレースホルダーは削除しないでください。

#### 使用できる変数一覧

| プロンプトキー | 使用できる変数 |
|---|---|
| `dialogue_generation` | `{real_world_context}` `{theme_title}` `{theme_prompt}` `{mia_persona}` `{master_persona}` |
| `comment_response` | `{real_world_context}` `{user_message}` `{context}` `{persona}` `{memory_summary}` |
| `master_monologue` | `{real_world_context}` `{theme_title}` `{theme_prompt}` `{master_persona}` |
| `master_solo_response` | `{real_world_context}` `{user_message}` `{context}` `{memory_summary}` `{master_persona}` |
| `master_relay` | `{user_message}` `{mia_persona}` `{master_persona}` |
| `master_direct_response` | `{user_message}` `{relay_text}` `{real_world_context}` `{context}` `{memory_summary}` `{master_persona}` |
| `mia_followup_prompt` | `{master_response}` |
| `memory_extract` | `{conversation}` |

#### 変更してはいけないもの

- `prompts` 以下の**キー名**（`dialogue_generation` `comment_response` 等）
- `mia` `master` `world` の**キー名**
- プロンプト内の `{変数名}` プレースホルダー

---

## 3. themes.yaml

放置時にキャラクターが話す話題を定義します。
世界観に合わせて自由に書き換えてください。

```yaml
themes:
  - id: "unique_id"          # 重複しなければ何でもOK
    title: "話題のタイトル"
    prompt: "LLMへの指示。どんな内容で話してほしいかを説明する文章。"
    keywords: ["キーワード1", "キーワード2"]   # 関連語（任意）
```

**例（シェアハウス版）:**

```yaml
themes:
  - id: "cat"
    title: "シェアハウスの猫"
    prompt: "部屋にいる茶トラの猫の様子についての話題。"
    keywords: ["猫", "ねこ", "茶トラ"]

  - id: "gadget"
    title: "機材とガジェット"
    prompt: "新しいガジェットやデスク周りの環境構築についての話題。"
    keywords: ["スマホ", "ガジェット", "キーボード"]
```

---

## 4. 画像ファイル

### 画像仕様

- サイズ：**960×540px**（16:9）推奨
- 形式：PNG
- キャラクター・オブジェクト画像は**背景透過PNG**

### レイヤー構成

画面は複数の画像を重ねて表示します。何をどの層に置くかを先に設計してください。

```
Layer 0  風景（時間帯・天気で自動切替）
Layer 1  室内背景（bg_indoor）— 常時表示
Layer 2  キャラクター（奥）
Layer 3  キャラクター（中間）
Layer 4  中景オブジェクト（obj_mid）— 常時表示
Layer 5  キャラクター（手前）
Layer 6  前景オブジェクト（obj_front）— 常時表示
Layer 7  ユーザー画像
```

数字が大きいほど手前に表示されます。

### 背景・風景画像（`assets/image/`）

`config.yaml` の `scene_images` でファイル名を指定します。

```yaml
scene_images:
  bg_indoor: "bg_indoor.png"      # 室内背景（常時）
  obj_mid:   "obj_mid.png"        # 中景オブジェクト（常時）
  obj_front: "obj_front.png"      # 前景オブジェクト（常時）
  scenery:
    day:       "scenery_day.png"       # 昼（6〜16時・晴れ）
    dawn:      "scenery_dawn.png"      # 夜明け（4〜6時）
    evening:   "scenery_evening.png"   # 夕方（16〜19時）
    night:     "scenery_night.png"     # 夜（19〜23時）
    latenight: "scenery_latenight.png" # 深夜（23〜4時）
    cloudy:    "scenery_cloudy.png"    # 曇り
    rain:      "scenery_rain.png"      # 雨
```

**風景の切り替えロジック：**
- 19〜23時・23〜4時は天気に関係なく時刻で固定
- 4〜19時は天気（晴れ・曇り・雨）で切り替え、晴れの場合は時刻で切り替え

### キャラクター画像（`assets/character/`）

`config.yaml` の `characters` でファイル名・レイヤー・出現条件を指定します。

```yaml
characters:
  chara1:
    pool:                              # 通常時のランダムプール（最大6枚）
      - file: "chara1_a.png"
        layer: 5                       # 2 / 3 / 5 のいずれか
      - file: "chara1_b.png"
        layer: 5
      - file: "chara1_back.png"
        layer: 2
        condition: sunny_daytime       # 晴れの昼〜夕方のみ出現（省略時は常時）
    late_night_pool:                   # 深夜専用プール（省略時は pool をそのまま使用）
      - file: "chara1_sleep.png"
        layer: 2

  chara2:
    pool:
      - file: "chara2_front.png"
        layer: 3
      - file: "chara2_back.png"
        layer: 3
```

**`condition` の値：**

| 値 | 説明 |
|---|---|
| 省略 | 常時プールに含まれる |
| `sunny_daytime` | 晴れの11〜19時のみ出現 |
| `late_night` | 深夜23〜6時のみ出現 |

---

## 5. 世界観ごとの変更例

### カフェ（デフォルト）

```
config.yaml     : overlay_title: "☕ Cafe Lumiere"
persona.yaml    : mia=Mia（スタッフ）/ master=Master（オーナー）
themes.yaml     : コーヒー・天気・おすすめ
assets/image/   : カフェの室内・窓の外の風景
assets/character/: スタッフ・オーナーの立ち絵
```

### シェアハウス

```
config.yaml     : overlay_title: "🏠 Share House 404"
persona.yaml    : mia=先輩（30代男性）/ master=タカシ（20代男性）
themes.yaml     : 筋トレ・キャンプ・猫・ガジェット
assets/image/   : シェアハウスのリビング・窓の外
assets/character/: 先輩・タカシの立ち絵
```

### 宇宙ステーション（SF）

```
config.yaml     : overlay_title: "🚀 Station Lumiere"
persona.yaml    : mia=AIオペレーター / master=謎の乗客
themes.yaml     : 今日の宙域・次の寄港地・宇宙食
assets/image/   : 宇宙船の内部・窓から見える星空（時間帯で星の配置を変える）
assets/character/: AIオペレーター・乗客の立ち絵
```

### 魔法の薬屋（ファンタジー）

```
config.yaml     : overlay_title: "🔮 Magical Apothecary"
persona.yaml    : mia=魔法使いの弟子 / master=喋る黒猫
themes.yaml     : 今日の薬草・不思議な依頼・魔法の練習
assets/image/   : 薬棚が並ぶ店・窓から見える魔法の森（夜は月明かり）
assets/character/: 弟子・黒猫の立ち絵
```

---

## よくある質問

**Q. キャラクターを1人にできますか？**
現状は2キャラ固定です。chara2の画像を透明PNGにして、`master_keywords` を空にすると実質的に chara1 だけが動く構成になります。

**Q. 風景画像は何種類必要ですか？**
最小1種類でも動きます。`scenery` の各キーに同じファイル名を指定すれば、時間帯・天気に関係なく同じ背景が表示されます。

**Q. プロンプトを日本語以外で書けますか？**
書けます。`dialogue_generation` のプロンプトを英語で書けば英語での掛け合いになります。`stt.language` も合わせて変更してください。

```yaml
stt:
  language: "en-US"
```
