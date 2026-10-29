# -*- mode: python -*-
# PyInstaller: crea la cartella «dist/tk-iscrizioni» per Linux, poi build_linux.sh la mette nell'AppImage.
# Uso: pyinstaller --noconfirm --clean linux/tk-iscrizioni-linux.spec
import os
import re

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
with open(os.path.join(ROOT, "tkiscrizioni", "__init__.py"), encoding="utf-8") as fh:
    VERSION = re.search(r'VERSION = "(.+)"', fh.read()).group(1)

# cartella delle licenze preparata da build_linux.sh (tools_licenze.py linux); da sola, quella del repo
LICENZE = os.path.join(ROOT, "build", "licenze")
if not os.path.isdir(LICENZE):
    LICENZE = os.path.join(ROOT, "licenze")

# libxcb-cursor (MIT/X11), messa nel pacchetto da build_linux.sh per chi usa X11
extra_bin = []
xcb_lib = os.path.join(ROOT, "build", "xcb-cursor", "libxcb-cursor.so.0")
if os.path.isfile(xcb_lib):
    extra_bin.append((xcb_lib, "."))

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[ROOT],
    binaries=extra_bin,
    # licenze in _internal/licenze; l'icona serve alla voce del menu delle applicazioni (tk_linux.installa_menu)
    datas=[(LICENZE, "licenze"), (os.path.join(ROOT, "assets", "tk-iscrizioni-512.png"), "assets")],
    hiddenimports=["certifi", "tkiscrizioni.tk_licenza", "tkiscrizioni.tk_licenza_qt", "tkiscrizioni.tk_aggiornamento",
                   "tkiscrizioni.disiscrizione", "tkiscrizioni.tk_linux", "secretstorage", "jeepney",
                   "jeepney.io.blocking"],
    excludes=["tkinter", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore", "PySide6.QtMultimedia",
              "PySide6.QtPdf"],
)

# componenti Qt non usati da un'app a widget (QtNetwork e QtOpenGL restano: servono ai plugin X11/Wayland)
DROP = ("QtQuick", "QtQml", "QtVirtualKeyboard", "QtPdf", "libqpdf", "QtWebEngine", "Qt3D", "QtMultimedia")
a.binaries = [b for b in a.binaries if not any(k in b[0] for k in DROP)]
a.datas = [d for d in a.datas if not any(k in d[0] for k in DROP)]

pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="tk-iscrizioni", console=False, strip=False)
coll = COLLECT(exe, a.binaries, a.datas, name="tk-iscrizioni")
