"""Prepara la cartella «licenze» del pacchetto: AGPL di tk-iscrizioni, testi delle licenze dei componenti
inclusi DAVVERO (Python, Qt/PySide6, certifi; su Mac e Linux anche il lanciatore di PyInstaller; su Linux
anche secretstorage, jeepney e libxcb-cursor) e COMPONENTI.txt con versioni e dove si scarica il sorgente.
Da eseguire col Python della build (venv), che conosce le versioni installate.
Uso: python tools_licenze.py <cartella di destinazione> windows|mac|linux"""
import glob
import os
import shutil
import sys
import sysconfig
from importlib import metadata

ROOT = os.path.dirname(os.path.abspath(__file__))
QT_SORGENTE = ("https://download.qt.io/official_releases/QtForPython/ e "
               "https://code.qt.io/cgit/pyside/pyside-setup.git (Qt: https://download.qt.io/official_releases/qt/)")


def versione(pacchetto):
    try:
        return metadata.version(pacchetto)
    except metadata.PackageNotFoundError:
        return "?"


def licenza_python():
    """LICENSE.txt del Python usato (con le note dei componenti inclusi: OpenSSL, libffi, SQLite, zlib…)."""
    for c in (os.path.join(sys.base_prefix, "LICENSE.txt"), os.path.join(sysconfig.get_path("stdlib"), "LICENSE.txt")):
        if os.path.isfile(c):
            return c
    return None


def licenza_dist_info(pacchetto):
    try:
        d = metadata.distribution(pacchetto)
    except metadata.PackageNotFoundError:
        return None
    for f in d.files or ():
        nome = os.path.basename(str(f)).upper()
        if nome.startswith(("LICENSE", "COPYING")):
            p = d.locate_file(f)
            if os.path.isfile(p):
                return str(p)
    return None


def main(dest, piattaforma):
    os.makedirs(dest, exist_ok=True)
    for f in glob.glob(os.path.join(ROOT, "licenze", "*.txt")):
        shutil.copy(f, dest)
    py = licenza_python()
    if py:
        shutil.copy(py, os.path.join(dest, "Python-PSF.txt"))
    cert = licenza_dist_info("certifi")
    if cert:
        shutil.copy(cert, os.path.join(dest, "certifi-LICENSE.txt"))
    if piattaforma == "linux":
        for pkg in ("secretstorage", "jeepney"):
            lic = licenza_dist_info(pkg)
            if lic:
                shutil.copy(lic, os.path.join(dest, f"{pkg}-LICENSE.txt"))
        # Python di sistema/setup-python senza LICENSE.txt: il copyright del pacchetto Debian/Ubuntu
        deb = f"/usr/share/doc/python{sys.version_info[0]}.{sys.version_info[1]}/copyright"
        if not py and os.path.isfile(deb):
            shutil.copy(deb, os.path.join(dest, "Python-PSF.txt"))
        # libxcb-cursor (MIT/X11), presa dal pacchetto Ubuntu da linux/build_linux.sh
        xcb = os.path.join(ROOT, "build", "xcb-cursor", "copyright")
        if os.path.isfile(xcb):
            shutil.copy(xcb, os.path.join(dest, "libxcb-cursor-LICENSE.txt"))
    pyside = versione("PySide6_Essentials")
    if pyside == "?":
        pyside = versione("PySide6")
    pyver = sys.version.split()[0]
    righe = [
        "tk-iscrizioni — componenti inclusi in questo pacchetto",
        "======================================================",
        "",
        "tk-iscrizioni",
        "  Licenza: GNU AGPL-3.0-or-later (COPYING-AGPL-3.0.txt)",
        "  Sorgente: https://github.com/tecnikgeek-repo/tk-iscrizioni-desktop",
        "  Il nome e il logo «tk-iscrizioni» non sono coperti dalla licenza (AGPL sez. 7).",
        "",
        f"Python {pyver}",
        "  Licenza: PSF License Agreement (Python-PSF.txt, con le licenze dei componenti di Python:",
        "  OpenSSL, libffi, SQLite, zlib, bzip2, xz, expat, mpdecimal…)",
        f"  Sorgente: https://www.python.org/downloads/source/ (versione {pyver})",
        "",
        f"Qt {pyside} (QtCore, QtGui, QtWidgets, QtSvg e plugin) + PySide6 {pyside} + shiboken6 {versione('shiboken6')}",
        "  Licenza: LGPL-3.0 (LGPL-3.0.txt, che si basa su GPL-3.0.txt); in alternativa GPL-2.0 / GPL-3.0",
        f"  Sorgente: {QT_SORGENTE}",
        "  Le librerie Qt sono file separati nel pacchetto: si possono sostituire con una versione modificata.",
        "",
        f"certifi {versione('certifi')}",
        "  Licenza: MPL-2.0 (MPL-2.0.txt, certifi-LICENSE.txt)",
        "  Sorgente: https://github.com/certifi/python-certifi e https://pypi.org/project/certifi/",
    ]
    if piattaforma == "windows":
        righe += [
            "",
            "Microsoft Visual C++ Runtime (vcruntime140.dll, msvcp140.dll…, inclusi con Python e PySide6)",
            "  Ridistribuibile secondo le condizioni di Microsoft Visual C++ Redistributable.",
        ]
    if piattaforma == "linux":
        righe += [
            "",
            f"SecretStorage {versione('secretstorage')} (solo Linux: portachiavi del sistema)",
            "  Licenza: BSD-3-Clause (secretstorage-LICENSE.txt)",
            "  Sorgente: https://github.com/mitya57/secretstorage e https://pypi.org/project/SecretStorage/",
            "",
            f"jeepney {versione('jeepney')} (solo Linux: collegamento D-Bus al portachiavi)",
            "  Licenza: MIT (jeepney-LICENSE.txt)",
            "  Sorgente: https://gitlab.com/takluyver/jeepney e https://pypi.org/project/jeepney/",
            "",
            "libxcb-cursor 0.1 (solo Linux, serve a Qt sotto X11)",
            "  Licenza: MIT/X11 (libxcb-cursor-LICENSE.txt)",
            "  Sorgente: https://gitlab.freedesktop.org/xorg/lib/libxcb-cursor",
            "",
            "Su Linux le librerie Qt sono dentro il file AppImage: si estrae con",
            "«tk-iscrizioni-….AppImage --appimage-extract» (cartella usr/lib/tk-iscrizioni/_internal).",
        ]
    if piattaforma != "windows":
        righe += [
            "",
            f"PyInstaller {versione('pyinstaller')} (solo il lanciatore dell'app)",
            "  Licenza: GPL-2.0 con l'eccezione per il bootloader (GPL-2.0.txt): l'eccezione permette di",
            "  distribuire il lanciatore insieme a programmi con altre licenze.",
            "  Sorgente: https://github.com/pyinstaller/pyinstaller e https://pypi.org/project/pyinstaller/",
        ]
    righe += ["", "Tutti i componenti sono forniti senza alcuna garanzia (vedi le rispettive licenze).", ""]
    with open(os.path.join(dest, "COMPONENTI.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(righe))
    print(f"licenze pronte in {dest}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in ("windows", "mac", "linux"):
        sys.exit("uso: python tools_licenze.py <cartella> windows|mac|linux")
    main(sys.argv[1], sys.argv[2])
