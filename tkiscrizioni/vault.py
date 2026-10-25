"""Password e token delle caselle, cifrati sul computer: Windows DPAPI (legati all'utente di Windows),
Mac Portachiavi. Non escono mai dal dispositivo."""
import base64
import json
import os
import subprocess

from tkiscrizioni.util import IS_MAC, IS_WIN, data_dir

SERVICE = "tkISCRIZIONI"  # nome storico, interno: cambiarlo renderebbe illeggibili le password salvate


def _file():
    return os.path.join(data_dir(), "credenziali.json")


def _load():
    try:
        with open(_file(), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save(d):
    tmp = _file() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)
    os.replace(tmp, _file())


if IS_WIN:
    import ctypes
    from ctypes import wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _blob(data):
        buf = ctypes.create_string_buffer(data, len(data))
        return _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

    def _out(blob):
        data = ctypes.string_at(blob.pbData, blob.cbData)
        ctypes.windll.kernel32.LocalFree(blob.pbData)
        return data

    _ENTROPY = b"tkISCRIZIONI/1"

    def _protect(data):
        src, _a = _blob(data)
        ent, _b = _blob(_ENTROPY)
        out = _Blob()
        if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(src), "tkISCRIZIONI", ctypes.byref(ent),
                                                      None, None, 0x01, ctypes.byref(out)):
            raise OSError("cifratura non riuscita")
        return _out(out)

    def _unprotect(data):
        src, _a = _blob(data)
        ent, _b = _blob(_ENTROPY)
        out = _Blob()
        if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(src), None, ctypes.byref(ent),
                                                        None, None, 0x01, ctypes.byref(out)):
            raise OSError("questa password è stata salvata su un altro computer o da un altro utente")
        return _out(out)


# ---- Mac: Portachiavi con lo strumento «security». La password NON va tra gli argomenti del comando
# (li vede chiunque sul Mac con «ps»): si scrive su stdin a «security -i», che legge i comandi riga per
# riga. Le righe di «security -i» hanno un limite di lunghezza: i valori lunghi (token di Outlook) si
# dividono in più voci «<casella>:parte1», «:parte2»… e la voce principale dice «parti:N».
_MAC_PARTE = 2000


def _mac_casella(account):
    # nella riga di «security -i» la casella va senza virgolette: niente spazi, virgolette o barre
    if not account or any(c.isspace() or c in "\"'\\" for c in account):
        raise ValueError("indirizzo email non valido per il Portachiavi")
    return account


def _mac_leggi(account):
    r = subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-a", account, "-w"],
                       capture_output=True, text=True)
    return r.stdout.rstrip("\n") if r.returncode == 0 else None


def _mac_parti(valore):
    if valore and valore.startswith("parti:"):
        try:
            return int(valore[6:])
        except ValueError:
            return 0
    return 0


def _mac_cancella(account):
    subprocess.run(["security", "delete-generic-password", "-s", SERVICE, "-a", account], capture_output=True)


def _mac_scrivi(account, value):
    vecchie = _mac_parti(_mac_leggi(account))
    if len(value) <= _MAC_PARTE:
        voci = [(account, value)]
    else:
        pezzi = [value[i:i + _MAC_PARTE] for i in range(0, len(value), _MAC_PARTE)]
        voci = [(account, f"parti:{len(pezzi)}")] + [(f"{account}:parte{i}", p) for i, p in enumerate(pezzi, 1)]
    righe = "".join(f"add-generic-password -U -s {SERVICE} -a {a} -w {v}\n" for a, v in voci)
    subprocess.run(["security", "-i"], input=righe, capture_output=True, text=True, timeout=30)
    for i in range(len(voci), vecchie + 1):
        _mac_cancella(f"{account}:parte{i}")


def set_secret(account, secret):
    if IS_MAC:
        # in base64: «security … -w» restituisce in esadecimale le password con lettere accentate
        value = "b64:" + base64.b64encode(secret.encode("utf-8")).decode()
        _mac_scrivi(_mac_casella(account), value)
        if get_secret(account) != secret:
            raise OSError("non riesco a salvare la password nel Portachiavi del Mac")
        return
    d = _load()
    raw = secret.encode("utf-8")
    d[account] = "dpapi:" + base64.b64encode(_protect(raw)).decode() if IS_WIN else \
        "b64:" + base64.b64encode(raw).decode()
    _save(d)


def get_secret(account):
    """La password/il token salvato, oppure None (mai salvato o non leggibile su questo computer)."""
    if IS_MAC:
        out = _mac_leggi(account)
        if out is None:
            return None
        n = _mac_parti(out)
        if n:
            pezzi = [_mac_leggi(f"{account}:parte{i}") for i in range(1, n + 1)]
            if any(p is None for p in pezzi):
                return None
            out = "".join(pezzi)
        if out.startswith("b64:"):
            try:
                return base64.b64decode(out[4:]).decode("utf-8")
            except Exception:
                return None
        return out
    v = _load().get(account)
    if not v:
        return None
    try:
        kind, payload = v.split(":", 1)
        raw = base64.b64decode(payload)
        return (_unprotect(raw) if kind == "dpapi" else raw).decode("utf-8")
    except Exception:
        return None


def delete_secret(account):
    if IS_MAC:
        for i in range(1, _mac_parti(_mac_leggi(account)) + 1):
            _mac_cancella(f"{account}:parte{i}")
        _mac_cancella(account)
        return
    d = _load()
    if d.pop(account, None) is not None:
        _save(d)
