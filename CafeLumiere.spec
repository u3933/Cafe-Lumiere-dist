# -*- mode: python ; coding: utf-8 -*-
#
# Cafe Lumiere - PyInstaller spec ファイル
#
# ビルド方法:
#   pip install pyinstaller
#   pyinstaller CafeLumiere.spec
#
# 出力先: dist/CafeLumiere/
# 配布物: dist/CafeLumiere/ フォルダをZIP圧縮して配布

import sys
from pathlib import Path

block_cipher = None

# ----------------------------------------------------------------
# 同梱するデータファイル（外部参照するファイル類）
# 形式: (実ファイルパス, EXE内での配置先ディレクトリ)
# ※ config.yaml / persona.yaml / themes.yaml / assets/ は
#    外出しのため同梱しない（ユーザーが配置する）
# ----------------------------------------------------------------
datas = [
    # フロントエンド（HTML/JS/CSS）
    ('frontend',        'frontend'),
    # セットアップウィザード
    ('setup_wizard',    'setup_wizard'),
    # アセット（サンプル画像・フォント）
    #   bgm/ は外出し（著作権フリー素材を各自用意）なので除外
    ('assets/image',    'assets/image'),
    ('assets/character','assets/character'),
    ('assets/LICENSE.txt',       'assets'),
    ('assets/PixelMplus12-Bold.ttf', 'assets'),
    # テンプレート・辞書
    ('config.yaml.example', '.'),
    ('tts_dict.yaml',        '.'),
    # ドキュメント
    ('docs',            'docs'),
]

# ----------------------------------------------------------------
# 隠しインポート（PyInstallerが自動検出できないモジュール）
# ----------------------------------------------------------------
hiddenimports = [
    # aiohttp 関連
    'aiohttp',
    'aiohttp.web',
    'aiohttp.web_runner',
    'aiohttp.connector',
    'aiohttp.client',
    # websockets
    'websockets',
    'websockets.server',
    'websockets.legacy',
    'websockets.legacy.server',
    # yaml
    'yaml',
    # fastapi / uvicorn（記憶サーバー）
    'fastapi',
    'uvicorn',
    'uvicorn.main',
    'uvicorn.config',
    'uvicorn.loops',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    # numpy（TTS音量増幅）
    'numpy',
    # sqlite3（記憶DB）
    'sqlite3',
    # その他標準ライブラリ
    'asyncio',
    'ssl',
    'json',
    'pathlib',
    'shutil',
    'signal',
]

# ----------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 不要なもの
        'tkinter',
        'matplotlib',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ----------------------------------------------------------------
# EXE
# ----------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # --onedir モード（起動速度優先）
    name='CafeLumiere',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                       # UPX圧縮（インストール済みの場合）
    console=True,                   # コンソール表示（ログ確認用）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',       # アイコン（用意した場合はコメント解除）
)

# ----------------------------------------------------------------
# COLLECT（--onedir モード: dist/CafeLumiere/ にまとめる）
# ----------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CafeLumiere',
)
