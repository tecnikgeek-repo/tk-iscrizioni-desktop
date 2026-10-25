"""Lettura della casella via IMAP: solo le intestazioni (mittente, oggetto, data, disiscrizione), in sola lettura.
Le email non vengono mai aperte né segnate come lette (BODY.PEEK, cartelle in EXAMINE)."""
import imaplib
import re
import socket
import ssl
import time

from tkiscrizioni import classify

imaplib._MAXLINE = 50_000_000
# AUTHENTICATION-RESULTS: l'esito della verifica DKIM scritto dal server di posta (serve per fidarsi
# del link di disiscrizione, vedi classify.parse_headers)
FIELDS = "FROM SUBJECT DATE LIST-UNSUBSCRIBE LIST-UNSUBSCRIBE-POST LIST-ID AUTHENTICATION-RESULTS"
BATCH = 400

_SKIP_FLAGS = {"\\sent", "\\drafts", "\\trash", "\\junk", "\\noselect", "\\nonexistent"}
_SKIP_NAMES = re.compile(r"(^|/|\.)(sent|inviat|bozze|draft|cestino|trash|deleted|eliminat|spam|junk|"
                         r"posta indesiderata|indesiderat|outbox|in uscita|posta inviata)", re.I)
_LIST_RX = re.compile(r'\((?P<flags>[^)]*)\)\s+(?P<delim>"(?:[^"\\]|\\.)*"|NIL)\s+(?P<name>.+)$')


class AuthError(Exception):
    pass


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def quote(name):
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def decode_mutf7(s):
    """Nome cartella IMAP (UTF-7 modificato) → testo leggibile."""
    import base64

    def dec(m):
        b = m.group(1)
        if not b:
            return "&"
        b = b.replace(",", "/")
        b += "=" * (-len(b) % 4)
        try:
            return base64.b64decode(b).decode("utf-16-be")
        except Exception:
            return m.group(0)
    return re.sub(r"&([A-Za-z0-9+,]*)-", dec, s)


def connect(host, port, user, secret, auth="password", timeout=45):
    """Apre la connessione e fa l'accesso. auth='password' oppure 'oauth_ms' (secret = access token)."""
    try:
        if int(port) == 143:
            im = imaplib.IMAP4(host, 143, timeout=timeout)
            im.starttls(ssl_context=_ctx())
        else:
            im = imaplib.IMAP4_SSL(host, int(port), ssl_context=_ctx(), timeout=timeout)
    except socket.gaierror:
        raise ConnectionError(f"il server «{host}» non esiste: controlla il nome")
    except (socket.timeout, TimeoutError):
        raise ConnectionError(f"il server «{host}» non risponde (porta {port})")
    except ssl.SSLError as e:
        raise ConnectionError(f"connessione sicura non riuscita con «{host}»: {e.reason or e}")
    except OSError as e:
        raise ConnectionError(f"non riesco a collegarmi a «{host}»: {e.strerror or e}")
    try:
        if auth == "oauth_ms":
            im.authenticate("XOAUTH2", lambda _: f"user={user}\x01auth=Bearer {secret}\x01\x01".encode())
        elif secret.isascii():
            im.login(user, secret)
        else:
            im.authenticate("PLAIN", lambda _: b"\0" + user.encode() + b"\0" + secret.encode("utf-8"))
    except imaplib.IMAP4.error as e:
        try:
            im.shutdown()
        except Exception:
            pass
        msg = re.sub(r"^\[[A-Z-]+\]\s*", "", str(e).strip("b'\"")).strip()
        raise AuthError(msg or "credenziali non valide")
    return im


def folders(im):
    """Cartelle da analizzare: con Gmail basta «Tutti i messaggi»; altrove tutte tranne inviata, bozze, cestino, spam."""
    typ, data = im.list()
    if typ != "OK":
        return ["INBOX"]
    items = []
    for line in data:
        if isinstance(line, tuple):
            line = line[0] + b" " + quote(line[1].decode("utf-8", "replace")).encode()
        m = _LIST_RX.match(line.decode("utf-8", "replace") if isinstance(line, bytes) else str(line))
        if not m:
            continue
        flags = {f.lower() for f in m.group("flags").split()}
        name = m.group("name").strip()
        if name.startswith('"') and name.endswith('"'):
            name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        items.append((name, flags))
    for name, flags in items:
        if "\\all" in flags:
            return [name]
    out = []
    for name, flags in items:
        if flags & _SKIP_FLAGS or _SKIP_NAMES.search(decode_mutf7(name)):
            continue
        out.append(name)
    if not any(n.upper() == "INBOX" for n in out):
        out.insert(0, "INBOX")
    return out


def _uid_of(meta):
    m = re.search(rb"UID (\d+)", meta)
    return int(m.group(1)) if m else None


def parse_fetch(data):
    """Risposta di UID FETCH → [(uid, bytes intestazioni)]. Gestisce l'UID prima o dopo il blocco."""
    out = []
    pending = None
    for item in data:
        if isinstance(item, tuple):
            uid = _uid_of(item[0])
            if uid is not None:
                out.append((uid, item[1] or b""))
                pending = None
            else:
                pending = item[1] or b""
        elif isinstance(item, bytes) and pending is not None:
            uid = _uid_of(item)
            if uid is not None:
                out.append((uid, pending))
            pending = None
    return out


def scan_account(im, store, account_id, progress=None, cancelled=None):
    """Analizza le cartelle della casella e salva le intestazioni nuove. Ritorna quante ne ha lette."""
    total_new = 0
    flist = folders(im)
    for fi, name in enumerate(flist):
        if cancelled and cancelled():
            raise InterruptedError
        label = decode_mutf7(name)
        typ, _ = im.select(quote(name), readonly=True)
        if typ != "OK":
            continue
        try:
            uv = int((im.untagged_responses.get("UIDVALIDITY") or [b"0"])[-1])
        except Exception:
            uv = 0
        old_uv, last = store.folder_state(account_id, name)
        if old_uv != uv:
            store.reset_folder(account_id, name, uv)
            last = 0
        typ, data = im.uid("SEARCH", None, f"UID {last + 1}:*" if last else "ALL")
        uids = [int(x) for x in (data[0] or b"").split()] if typ == "OK" and data else []
        uids = sorted(u for u in uids if u > last)
        if not uids:
            continue
        for i in range(0, len(uids), BATCH):
            if cancelled and cancelled():
                raise InterruptedError
            chunk = uids[i:i + BATCH]
            spec = ",".join(str(u) for u in chunk)
            typ, data = im.uid("FETCH", spec, f"(UID BODY.PEEK[HEADER.FIELDS ({FIELDS})])")
            if typ != "OK":
                continue
            rows = []
            for uid, raw in parse_fetch(data):
                try:
                    r = classify.parse_headers(raw)
                except Exception:
                    r = None
                if r:
                    rows.append((uid, r))
            store.save_batch(account_id, name, rows, chunk[-1])
            total_new += len(rows)
            if progress:
                progress(f"{label}: {min(i + BATCH, len(uids))} di {len(uids)} email",
                         fi + min(i + BATCH, len(uids)) / len(uids), len(flist))
    return total_new
