# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


programme_dir = Path("D:/P/CIVL7009/Dataset/Select_Programme")
qt_plugin_datas = collect_data_files(
    "PySide6",
    includes=[
        "plugins/platforms/qwindows.dll",
        "plugins/imageformats/qjpeg.dll",
        "plugins/imageformats/qico.dll",
        "plugins/imageformats/qsvg.dll",
        "plugins/styles/*",
    ],
)

datas = [
    (
        str(programme_dir / "CIVL7009_source_group_picker_gui_V1.8.1_202606041443.py"),
        ".",
    ),
    (
        str(programme_dir / "UI_Assets" / "V1.9.1_202606041705"),
        "UI_Assets/V1.9.1_202606041705",
    ),
]
datas += qt_plugin_datas


a = Analysis(
    ["D:\\P\\CIVL7009\\Dataset\\Select_Programme\\CIVL7009_source_group_picker_qt_V1.9.1_202606041705.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "argparse",
        "atexit",
        "ctypes",
        "socket",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.ttk",
        "uuid",
        "PIL.ImageTk",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvgWidgets",
    ],
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
    name="CIVL7009_Source_Group_Picker_V1.9.1_202606041705",
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
