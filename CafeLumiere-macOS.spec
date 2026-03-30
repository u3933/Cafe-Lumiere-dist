# -*- mode: python ; coding: utf-8 -*-
#
# Cafe Lumiere - PyInstaller spec ファイル（macOS 専用）
#
# ビルド方法（Mac上で実行）:
#   pip install pyinstaller
#   pyinstaller CafeLumiere-macOS.spec
#
# 出力先: dist/CafeLumiere.app
# 配布物: dist/CafeLumiere.app を ZIP 圧縮して配布
#
# Gatekeeper 警告への対処（署名なし配布の場合）:
#   受け取った側は「右クリック → 開く」で起動できる
#   または配布前に以下を実行:
#     xattr -cr dist/CafeLumiere.app

import sys
from pathlib import Path

block_cipher = None

# ----------------------------------------------------------------
# 同梱するデータファイル
# Windows版と同一内容（パス区切りはmacOSでも同じく / でOK）
# ----------------------------------------------------------------
datas = [
    ('frontend',             'frontend'),
    ('setup_wizard',         'setup_wizard'),
    ('assets/image',         'assets/image'),
    ('assets/character',     'assets/character'),
    ('assets/LICENSE.txt',   'assets'),
    ('assets/PixelMplus12-Bold.ttf', 'assets'),
    ('config.yaml.example',  '.'),
    ('tts_dict.yaml',        '.'),
    ('docs',                 'docs'),
]

# ----------------------------------------------------------------
# 隠しインポート（Windows版と同一）
# ----------------------------------------------------------------
hiddenimports = [
    'aiohttp',
    'aiohttp.web',
    'aiohttp.web_runner',
    'aiohttp.connector',
    'aiohttp.client',
    'websockets',
    'websockets.server',
    'websockets.legacy',
    'websockets.legacy.server',
    'yaml',
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
    'numpy',
    'sqlite3',
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
        'tkinter',
        'matplotlib',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
        'pytest',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ----------------------------------------------------------------
# EXE（macOS では .app 内の Unix 実行ファイル）
# ----------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CafeLumiere',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # macOS: console=True にするとターミナルウィンドウが開く
    # ログ確認のため True 推奨。運用が安定したら False にしてもよい
    console=True,
    disable_windowed_traceback=False,
    # Apple Silicon (M1/M2/M3/M4) ネイティブビルド
    # 'arm64' に固定することで Rosetta 不要の高速動作
    # Intel Mac でビルドする場合は 'x86_64' に変更
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.icns',  # アイコン（.icns形式、用意した場合はコメント解除）
)

# ----------------------------------------------------------------
# COLLECT（.app 内に全ファイルを集める）
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

# ----------------------------------------------------------------
# BUNDLE（macOS .app パッケージを生成）
# ----------------------------------------------------------------
app = BUNDLE(
    coll,
    name='CafeLumiere.app',
    # icon='assets/icon.icns',
    bundle_identifier='com.cafelumiere.app',
    info_plist={
        # アプリ名・バージョン
        'CFBundleName':             'CafeLumiere',
        'CFBundleDisplayName':      'Cafe Lumiere',
        'CFBundleVersion':          '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        # macOS に「バックグラウンドアプリ」として認識させる
        # Dock に表示せず、ターミナルのように動作する
        'LSUIElement': True,
        # マイク使用の説明（Safariからアクセス時に表示）
        'NSMicrophoneUsageDescription': 'Cafe Lumiere は音声入力に使用します。',
        # ネットワークアクセス許可
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True,
        },
    },
)
