# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None
root = Path.cwd()
entry = root / "Dataset" / "Select_Programme" / "CIVL7009_source_group_picker_qt_V3.0.4_202606051830.py"
programme = root / "Dataset" / "Select_Programme"

a = Analysis(
    [str(entry)],
    pathex=[str(programme)],
    binaries=[],
    datas=[
        (str(programme / "CIVL7009_source_group_picker_gui_V1.8.2_202606042313.py"), "."),
        (str(programme / "civl7009_picker_v3_0_4"), "civl7009_picker_v3_0_4"),
    ],
    hiddenimports=["PySide6.QtSvgWidgets", "PIL.Image"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CIVL7009_Source_Group_Picker_V3.0.4_202606051830",
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
)
