# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para BalanceLocal (onedir, ventana sin consola).
Usa Pillow (tarjetas Wrapped) y PyMuPDF (informe). El video opcional busca
FFmpeg en el sistema. Sin audio, sin captura de pantalla."""

import os

block_cipher = None

icon_path = os.environ.get("APP_ICON", "")
icon_arg = icon_path if (icon_path and os.path.isfile(icon_path)) else None

a = Analysis(
    ['..\\BalanceLocal.py'],
    pathex=[],
    binaries=[],
    datas=([(icon_path, 'build')] if icon_arg else []),
    hiddenimports=['fitz', 'PIL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy', 'pandas', 'matplotlib', 'PyQt5', 'PyQt6', 'PySide6',
              'soundcard', 'numpy', 'mss', 'pypdf', 'cryptography'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='BalanceLocal',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False, target_arch=None,
    codesign_identity=None, entitlements_file=None, icon=icon_arg,
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False,
               upx_exclude=[], name='BalanceLocal')
