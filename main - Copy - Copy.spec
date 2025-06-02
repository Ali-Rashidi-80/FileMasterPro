# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('SDelete', 'SDelete'), ('about_tab.py', '.'), ('config.py', '.'), ('Cryptography_tab.py', '.'), ('custom_copy_tab.py', '.'), ('duplicate_files_tab.py', '.'), ('file_shredder_tab.py', '.'), ('files_tab.py', '.'), ('folders_tab.py', '.'), ('large_files_tab.py', '.'), ('settings_tab.py', '.'), ('shuffle_tab.py', '.'), ('icons', 'icons')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app.png'],
)
