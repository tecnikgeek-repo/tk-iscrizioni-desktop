"""Accesso a Outlook/Hotmail con il login ufficiale di Microsoft (OAuth 2.0, codice + PKCE, client pubblico).
Accesso e token passano solo tra il programma e Microsoft: nessun server intermedio. Il client ID dell'app
registrata su Azure si legge da un file pubblico su pietrodefilippis.it (si può cambiare senza ripubblicare il
programma): è l'unica cosa che arriva dal sito, e non gli si manda nulla della casella."""
import base64
import hashlib
import http.server
import json
import os
import secrets
import ssl
import threading
import time
import urllib.parse
import urllib.request
import webbrowser

from tkiscrizioni import VERSION, tk_linux

CONFIG_URL = "https://pietrodefilippis.it/updates/tk-iscrizioni-config.json"
SCOPE = "https://outlook.office.com/IMAP.AccessAsUser.All offline_access"
AUTH = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
TOKEN = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _post(url, data, timeout=30):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"User-Agent": f"tk-iscrizioni/{VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {}
        raise RuntimeError(body.get("error_description", "").split("\r\n")[0] or f"errore {e.code} da Microsoft")


def config(timeout=10):
    """{'ms_client_id': '...', 'ms_tenant': 'common'} dal sito; client_id vuoto = Outlook non ancora attivo."""
    req = urllib.request.Request(CONFIG_URL + f"?t={int(time.time())}",
                                 headers={"User-Agent": f"tk-iscrizioni/{VERSION}", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
        data = json.loads(r.read().decode("utf-8-sig"))
    return {"client_id": str(data.get("ms_client_id") or "").strip(),
            "tenant": str(data.get("ms_tenant") or "common").strip()}


_PAGE = """<!doctype html><meta charset="utf-8"><title>tk-iscrizioni</title>
<body style="font-family:system-ui,Segoe UI,sans-serif;background:#0f172a;color:#fff;display:grid;place-items:center;
height:100vh;margin:0"><div style="text-align:center;max-width:420px;padding:24px"><h1 style="font-size:24px">{t}</h1>
<p style="color:#cbd5e1;font-size:16px">{m}</p></div></body>"""


def login(client_id, tenant="common", login_hint="", timeout=300, cancelled=None):
    """Apre il browser sulla pagina di Microsoft e attende il ritorno su http://localhost:<porta>.
    Ritorna il dizionario dei token (access_token, refresh_token, expires_in)."""
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    result = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] != state:
                self.send_response(404)
                self.end_headers()
                return
            result.update({k: v[0] for k, v in q.items()})
            ok = "code" in result
            page = _PAGE.format(t="Accesso riuscito" if ok else "Accesso non riuscito",
                                m="Puoi chiudere questa scheda e tornare a tk-iscrizioni." if ok else
                                (result.get("error_description") or "Riprova da tk-iscrizioni."))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page.encode("utf-8"))

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    srv.timeout = 0.5
    redirect = f"http://localhost:{srv.server_port}"
    params = {"client_id": client_id, "response_type": "code", "redirect_uri": redirect, "response_mode": "query",
              "scope": SCOPE, "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
              "prompt": "select_account"}
    if login_hint:
        params["login_hint"] = login_hint
    url = AUTH.format(tenant=tenant) + "?" + urllib.parse.urlencode(params)
    if tk_linux.IS_LINUX:
        tk_linux.apri(url)  # xdg-open con l'ambiente pulito: il browser non deve caricare le librerie del pacchetto
    else:
        webbrowser.open(url)
    end = time.time() + timeout
    try:
        while not result and time.time() < end:
            if cancelled and cancelled():
                raise InterruptedError("accesso annullato")
            srv.handle_request()
    finally:
        srv.server_close()
    if not result:
        raise TimeoutError("tempo scaduto: l'accesso a Microsoft non è stato completato")
    if "code" not in result:
        raise RuntimeError(result.get("error_description") or result.get("error") or "accesso rifiutato")
    tok = _post(TOKEN.format(tenant=tenant), {"client_id": client_id, "grant_type": "authorization_code",
                                              "code": result["code"], "redirect_uri": redirect,
                                              "code_verifier": verifier, "scope": SCOPE})
    tok["obtained"] = time.time()
    return tok


def refresh(client_id, refresh_token, tenant="common"):
    tok = _post(TOKEN.format(tenant=tenant), {"client_id": client_id, "grant_type": "refresh_token",
                                              "refresh_token": refresh_token, "scope": SCOPE})
    tok["obtained"] = time.time()
    if not tok.get("refresh_token"):
        tok["refresh_token"] = refresh_token
    return tok
