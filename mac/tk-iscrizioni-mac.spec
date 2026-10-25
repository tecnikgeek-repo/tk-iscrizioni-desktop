# -*- mode: python -*-
# PyInstaller: crea "tk-iscrizioni.app" per macOS. Uso: pyinstaller --noconfirm --clean mac/tk-iscrizioni-mac.spec
import os
import re

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
with open(os.path.join(ROOT, "tkiscrizioni", "__init__.py"), encoding="utf-8") as fh:
    VERSION = re.search(r'VERSION = "(.+)"', fh.read()).group(1)

# cartella delle licenze preparata da build_mac.sh (tools_licenze.py); da sola, quella del repo
LICENZE = os.path.join(ROOT, "build", "licenze")
if not os.path.isdir(LICENZE):
    LICENZE = os.path.join(ROOT, "licenze")

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[ROOT],
    datas=[(LICENZE, "licenze")],  # finisce in Contents/Resources/licenze
    hiddenimports=["certifi", "tkiscrizioni.tk_licenza", "tkiscrizioni.tk_licenza_qt", "tkiscrizioni.tk_aggiornamento",
                   "tkiscrizioni.disiscrizione"],
    excludes=["tkinter", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore", "PySide6.QtMultimedia",
              "PySide6.QtPdf", "PySide6.QtNetwork"],
)

# componenti Qt non usati da un'app a widget
DROP = ("QtQuick", "QtQml", "QtVirtualKeyboard", "QtPdf", "libqpdf", "QtWebEngine", "Qt3D", "QtMultimedia",
        "QtNetwork", "QtOpenGL")
a.binaries = [b for b in a.binaries if not any(k in b[0] for k in DROP)]
a.datas = [d for d in a.datas if not any(k in d[0] for k in DROP)]

pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="tk-iscrizioni", console=False, argv_emulation=False)
coll = COLLECT(exe, a.binaries, a.datas, name="tk-iscrizioni")
app = BUNDLE(
    coll,
    name="tk-iscrizioni.app",
    icon=os.path.join(ROOT, "assets", "tk-iscrizioni.icns"),
    bundle_identifier="com.tecnikgeek.tkiscrizioni",  # interno: non cambiarlo
    version=VERSION,
    info_plist={
        "CFBundleName": "tk-iscrizioni",
        "CFBundleDisplayName": "tk-iscrizioni",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": True,
        "NSHumanReadableCopyright": "© 2026 Pietro De Filippis (TecnikGeek) - software libero AGPL-3.0",
        "LSApplicationCategoryType": "public.app-category.productivity",
    },
)
