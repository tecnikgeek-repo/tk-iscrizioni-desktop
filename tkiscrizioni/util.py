"""Percorsi, impostazioni e piccole utilità di sistema (Windows, Mac e Linux)."""
import json
import os
import sys

from tkiscrizioni import APP_TITLE, LEGACY_TITLE, VERSION
from tkiscrizioni import tk_linux  # libreria comune dei software TK (su Windows e Mac non fa niente)

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

# dove stanno le password, per i testi dell'interfaccia
VAULT_NAME = ("Gestione credenziali di Windows" if IS_WIN else "Portachiavi del Mac" if IS_MAC
              else tk_linux.NOME_PORTACHIAVI)
LINUX_DESKTOP_ID = "tk-iscrizioni"  # nome del file .desktop = app_id della finestra su Wayland (icona nella barra)


def mac_bundle_path():
    """Percorso di «tk-iscrizioni.app» se il programma gira dal bundle macOS."""
    exe = os.path.abspath(sys.executable)
    marker = ".app/Contents/MacOS/"
    i = exe.find(marker)
    return exe[:i + 4] if i >= 0 else None


def is_installed():
    """True se gira dal pacchetto portatile (Windows: cartella «app» con il Python incluso; Mac: bundle .app;
    Linux: file AppImage)."""
    if IS_MAC:
        return bool(getattr(sys, "frozen", False) and mac_bundle_path())
    if IS_LINUX:
        return bool(tk_linux.appimage_path())
    bundled = os.path.join(APP_ROOT, "python")
    return os.path.isfile(os.path.join(bundled, "pythonw.exe")) and \
        os.path.normcase(os.path.abspath(sys.base_prefix)) == os.path.normcase(bundled)


def _writable_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".prova")
        open(probe, "w").close()
        os.remove(probe)
        return True
    except OSError:
        return False


def data_dir():
    """Archivio e impostazioni. Windows: «Dati» accanto ad «app» (portatile). Mac: Application Support.
    Linux: ~/.local/share/tk-iscrizioni. Gli aggiornamenti non la toccano. TKISCR_DATA la sostituisce (test).
    Su Mac la cartella tiene il nome storico (LEGACY_TITLE): cambiarlo farebbe sparire l'archivio."""
    if os.environ.get("TKISCR_DATA"):
        path = os.environ["TKISCR_DATA"]
    elif IS_MAC:
        path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", LEGACY_TITLE)
    elif IS_LINUX:
        path = tk_linux.cartella_dati(APP_TITLE)
    else:
        base = os.path.dirname(APP_ROOT) if is_installed() else APP_ROOT
        path = os.path.join(base, "Dati")
    if not _writable_dir(path):
        path = os.path.join(os.path.expanduser("~"), "Documents", LEGACY_TITLE)
        os.makedirs(path, exist_ok=True)
    return path


def log_dir():
    return data_dir()


def cartella_licenze():
    """Cartella «licenze» del pacchetto: Windows accanto a run.py (cartella «app»), Mac in
    Contents/Resources/licenze, Linux dentro l'AppImage (_internal/licenze); da sorgente quella del repo (senza COMPONENTI.txt, lo scrive la build)."""
    candidati = [os.path.join(APP_ROOT, "licenze")]
    if getattr(sys, "_MEIPASS", None):
        candidati.append(os.path.join(sys._MEIPASS, "licenze"))
    bundle = mac_bundle_path()
    if bundle:
        candidati.append(os.path.join(bundle, "Contents", "Resources", "licenze"))
    for c in candidati:
        if os.path.isdir(c):
            return c
    return candidati[0]


def export_dir():
    """Dove proporre il salvataggio delle esportazioni."""
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    if IS_LINUX:
        docs = cartella_documenti_linux() or docs
    return docs if os.path.isdir(docs) else os.path.expanduser("~")


def cartella_documenti_linux():
    """Linux: la cartella Documenti dell'utente col nome della sua lingua («Documenti» in italiano), da
    ~/.config/user-dirs.dirs (lo stesso file che legge xdg-user-dir). Vuoto se non c'è."""
    home = os.path.expanduser("~")
    conf = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config"), "user-dirs.dirs")
    try:
        with open(conf, encoding="utf-8") as fh:
            for riga in fh:
                riga = riga.strip()
                if riga.startswith("XDG_DOCUMENTS_DIR="):
                    valore = riga.split("=", 1)[1].strip().strip('"').replace("$HOME", home)
                    return valore if os.path.isdir(valore) and valore.rstrip("/") != home else ""
    except OSError:
        pass
    return ""


def open_path(path):
    import subprocess
    if IS_WIN:
        os.startfile(path)
    elif IS_MAC:
        subprocess.Popen(["open", path])
    else:
        tk_linux.apri(path)  # xdg-open con l'ambiente pulito (senza le librerie del pacchetto)


def install_linux_menu():
    """Linux: voce «tk-iscrizioni» nel menu delle applicazioni con l'icona (si corregge da sola se l'AppImage
    viene spostato, sparisce se viene cancellato)."""
    icon = os.path.join(getattr(sys, "_MEIPASS", APP_ROOT), "assets", "tk-iscrizioni-512.png")
    return tk_linux.installa_menu(LINUX_DESKTOP_ID, APP_TITLE,
                                  "A cosa sei iscritto con la tua email (TecnikGeek)", "Office;Network;Email;", icon,
                                  nome_generico="Iscrizioni email",
                                  parole="email;posta;newsletter;iscrizioni;disiscrizione;account;")


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


class Settings:
    """Impostazioni in un file JSON nella cartella dei dati."""

    def __init__(self):
        self.path = os.path.join(data_dir(), "impostazioni.json")
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                self.data = json.load(fh)
        except Exception:
            self.data = {}

    def value(self, key, default=None):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=1)
        except OSError:
            pass


def _make_shortcut(folder_expr):
    """Collegamento «tk-iscrizioni»: avvia il Python incluso (stesso pythonw.exe già accettato da Windows).
    Toglie il collegamento col nome vecchio («tkISCRIZIONI.lnk») nella stessa cartella."""
    import subprocess
    exe = os.path.join(APP_ROOT, "python", "pythonw.exe")
    if not os.path.isfile(exe):
        exe = sys.executable
    icon = os.path.join(APP_ROOT, "assets", "tk-iscrizioni.ico")
    # ogni percorso tra apostrofi con gli apostrofi raddoppiati (es. «C:\Users\D'Angelo\...»)
    q = _ps_literal
    ps = (
        f"$d={folder_expr};"
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d {q(APP_TITLE + '.lnk')}));"
        f"$s.TargetPath={q(exe)};"
        f"$s.Arguments={q(chr(34) + os.path.join(APP_ROOT, 'run.py') + chr(34))};"
        f"$s.WorkingDirectory={q(APP_ROOT)};"
        f"$s.IconLocation={q(icon + ',0')};"
        f"$s.Description={q(APP_TITLE + ' - a cosa sei iscritto con la tua email')};$s.Save();"
        f"$o=Join-Path $d {q(LEGACY_TITLE + '.lnk')};if(Test-Path -LiteralPath $o){{Remove-Item -LiteralPath $o -Force}};"
        f"Write-Output (Join-Path $d {q(APP_TITLE + '.lnk')})"
    )
    ps_exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0",
                          "powershell.exe")
    r = subprocess.run([ps_exe, "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, creationflags=0x08000000, timeout=30)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[-300:])
    return r.stdout.strip()


def create_desktop_shortcut():
    if not IS_WIN:
        raise RuntimeError("disponibile solo su Windows")
    return _make_shortcut("[Environment]::GetFolderPath('Desktop')")


def ensure_folder_shortcut():
    """Collegamento con icona nella cartella del programma (accanto ad «app» e «Dati»). Solo Windows."""
    if not IS_WIN:
        return ""
    return _make_shortcut(_ps_literal(os.path.dirname(APP_ROOT)))


def _ps_literal(path):
    return "'" + path.replace("'", "''") + "'"


def _shell_folder(csidl):
    import ctypes
    buf = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf) != 0:
        return ""
    return buf.value


UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\tk-iscrizioni"


def _rename_text_file(old, new, encoding):
    """Riscrive «old» come «new» con il nome nuovo nel testo, poi toglie «old»."""
    with open(old, "r", encoding=encoding, newline="") as fh:
        text = fh.read()
    with open(new, "w", encoding=encoding, newline="") as fh:
        fh.write(text.replace(LEGACY_TITLE, APP_TITLE))
    os.remove(old)


def migrate_legacy_names():
    """Dalla 1.0.5 il nome è «tk-iscrizioni». Chi aggiorna dalla 1.0.4 riceve solo la nuova cartella «app»:
    qui si rinominano collegamenti (cartella, menu Start, desktop), «Avvia …cmd», «Disinstalla …cmd»
    e la voce in «App installate». Solo Windows, solo dal pacchetto; ogni passo è facoltativo."""
    if not IS_WIN or not is_installed():
        return []
    import winreg
    done = []
    root = os.path.dirname(APP_ROOT)
    entry, installed_here = None, False
    try:
        entry = winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0,
                               winreg.KEY_READ | winreg.KEY_SET_VALUE)
        loc = winreg.QueryValueEx(entry, "InstallLocation")[0]
        installed_here = os.path.normcase(os.path.abspath(loc)) == os.path.normcase(os.path.abspath(root))
    except OSError:
        pass

    folders = [root]
    if installed_here:
        folders.append(_shell_folder(0x02))  # menu Start → Programmi
    if installed_here or entry is None:
        folders.append(_shell_folder(0x10))  # desktop (se c'è un'installazione altrove, il suo è di quella)
    for folder in folders:
        if folder and os.path.isfile(os.path.join(folder, LEGACY_TITLE + ".lnk")):
            try:
                _make_shortcut(_ps_literal(folder))
                done.append(folder)
            except Exception:
                pass

    for old, new, enc in ((f"Avvia {LEGACY_TITLE}.cmd", f"Avvia {APP_TITLE}.cmd", "latin-1"),
                          ("Leggimi.txt", "Leggimi.txt.nuovo", "utf-8-sig")):
        p = os.path.join(root, old)
        try:
            if old == "Leggimi.txt":
                with open(p, "r", encoding=enc) as fh:
                    if LEGACY_TITLE not in fh.read():
                        continue
                _rename_text_file(p, os.path.join(root, new), enc)
                os.replace(os.path.join(root, new), p)
            elif os.path.isfile(p):
                _rename_text_file(p, os.path.join(root, new), enc)
                done.append(new)
        except OSError:
            pass

    if entry is not None and installed_here:
        try:
            old_un = os.path.join(root, f"Disinstalla {LEGACY_TITLE}.cmd")
            new_un = os.path.join(root, f"Disinstalla {APP_TITLE}.cmd")
            if os.path.isfile(old_un):
                _rename_text_file(old_un, new_un, "latin-1")
                done.append(new_un)
            if os.path.isfile(new_un):
                winreg.SetValueEx(entry, "UninstallString", 0, winreg.REG_SZ, f'cmd.exe /c ""{new_un}""')
            winreg.SetValueEx(entry, "DisplayName", 0, winreg.REG_SZ, APP_TITLE)
            winreg.SetValueEx(entry, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
        except OSError:
            pass
    if entry is not None:
        winreg.CloseKey(entry)
    return done
