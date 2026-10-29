# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：pyinstaller build.spec --noconfirm"""

a = Analysis(
    ["run.py"],
    pathex=[".", "third_party"],
    binaries=[],
    datas=[
        ("assets/app.ico", "assets"),
        # SiliconUI 启动时会读取图标包目录，必须一并打包
        ("third_party/siui/gui/icons/packages/fluent_ui_icon_light.icons",
         "siui/gui/icons/packages"),
        ("third_party/siui/gui/icons/packages/fluent_ui_icon_regular.icons",
         "siui/gui/icons/packages"),
        ("third_party/siui/gui/icons/packages/fluent_ui_icon_filled.icons",
         "siui/gui/icons/packages"),
    ],
    hiddenimports=["numpy"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "pydoc",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQml",
        "PySide6.Qt3DCore",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtPdf",
        "PySide6.QtDesigner",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="2.4G设备电量助手",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/app.ico",
    version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="2.4G设备电量助手",
)
