"""Test del motore: scansione IMAP (finto server), classificazione, incrementale, cifratura. Uso: python tests/test_core.py"""
import imaplib
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ["TKISCR_DATA"] = tempfile.mkdtemp(prefix="tkiscr-test-")
os.environ["TKISCR_VAULT_SERVICE"] = "tk-iscrizioni-test"  # Linux: portachiavi, voci di prova (mai quelle vere)

import fake_imap  # noqa: E402
from tkiscrizioni import classify, mailscan, vault  # noqa: E402
from tkiscrizioni.store import Store  # noqa: E402

fails = []


def check(cond, what):
    print(("OK   " if cond else "FAIL ") + what)
    if not cond:
        fails.append(what)


srv, port = fake_imap.start()
store = Store()
aid = store.add_account("pietro@esempio-ditta.it", "altro", "127.0.0.1", port, "password")

im = imaplib.IMAP4("127.0.0.1", port)
try:
    im.login("pietro@esempio-ditta.it", "sbagliata")
    check(False, "password sbagliata rifiutata")
except imaplib.IMAP4.error:
    check(True, "password sbagliata rifiutata")
im.login("pietro@esempio-ditta.it", "segreta")
fl = mailscan.folders(im)
check(fl == ["INBOX", "Lavoro &AOg- archivio"], f"cartelle giuste (niente Inviata/Spam): {fl}")
check(mailscan.decode_mutf7("Lavoro &AOg- archivio") == "Lavoro è archivio", "nome cartella UTF-7 decodificato")
TOT = len(fake_imap.DEMO)
check("AUTHENTICATION-RESULTS" in mailscan.FIELDS.split(), "si chiede anche l'esito DKIM (Authentication-Results)")
n = mailscan.scan_account(im, store, aid)
check(n == TOT, f"{TOT} intestazioni lette (lette {n})")
n2 = mailscan.scan_account(im, store, aid)
check(n2 == 0, f"seconda analisi incrementale: 0 nuove (lette {n2})")
im.logout()

svc = {s["domain"]: s for s in store.services()}
exp = {"netflix.com": "account", "amazon.it": "acquisti", "zalando.it": "newsletter", "facebook.com": "social",
       "gmail.com": "persona", "spotify.com": "account", "posteitaliane.it": "account",
       "esempio-ditta.it": "persona", "booking.com": "acquisti"}
for d, c in exp.items():
    check(d in svc and svc[d]["cat"] == c, f"{d} → {c} (trovato {svc.get(d, {}).get('cat')})")
check(svc["netflix.com"]["name"] == "Netflix", f"nome Netflix ({svc['netflix.com']['name']})")
check(svc["amazon.it"]["name"] == "Amazon.it", f"nome Amazon ({svc['amazon.it']['name']})")
z = svc["zalando.it"]
check(z["unsub_post"] == 1 and classify.unsub_links(z["unsub"])[0].startswith("https://zalando"),
      "Zalando: disiscrizione in un clic")
check(classify.unsub_links(z["unsub"])[0] == "https://zalando.example/unsub?u=1",
      f"Zalando: solo il link firmato DKIM (niente email falsa, firma non allineata, data futura): {z['unsub']}")
check(z["last"] and z["last"] < 4e9 and abs(z["last"] - 1658296800) < 2,
      f"Zalando: l'email «dal 2099» non è l'ultima email (ultima = 20/07/2022: {z['last']})")
check(all(m["ts"] < 4e9 for m in store.recent("zalando.it")), "data futura salvata come sconosciuta (0)")
cnt = {r["domain"]: r["c"] for r in store.q("SELECT domain, COUNT(*) c FROM messages WHERE unsub<>'' GROUP BY domain")}
check(cnt.get("zalando.it") == 3, f"in archivio solo i link verificati (3 email Zalando su 5: {cnt.get('zalando.it')})")
check(abs(svc["netflix.com"]["first"] - 1580720400) < 2, "data di iscrizione Netflix = prima email (03/02/2020)")
rec = store.recent("zalando.it")
saldi = [m["subject"] for m in rec if m["subject"].startswith("Saldi")]
check(saldi and "Saldi fino al 70%" in saldi[0], f"oggetto con codifica decodificato: {saldi!r}")
store.set_status("zalando.it", "cancellare")
store.set_status("zalando.it", note="disiscritto")
z = {s["domain"]: s for s in store.services()}["zalando.it"]
check(z["status"] == "cancellare" and z["note"] == "disiscritto", "stato e nota salvati")

# connect() reale con porta TLS sbagliata → errore chiaro, non un crash
try:
    mailscan.connect("127.0.0.1", 1, "x", "y", timeout=3)
    check(False, "errore di connessione chiaro")
except ConnectionError as e:
    check(True, f"errore di connessione chiaro: {e}")

vault.set_secret("pietro@esempio-ditta.it", "pàssword segreta")
check(vault.get_secret("pietro@esempio-ditta.it") == "pàssword segreta", "password cifrata e riletta")
CRED = os.path.join(os.environ["TKISCR_DATA"], "credenziali.json")
if sys.platform == "win32":   # su Mac e Linux la password sta nel portachiavi, non in un file
    raw = open(CRED, encoding="utf-8").read()
    check("segreta" not in raw, "nel file la password non è in chiaro")
elif sys.platform.startswith("linux"):
    check(not os.path.exists(CRED) or "pietro@" not in open(CRED, encoding="utf-8").read(),
          "Linux: password nel portachiavi, non nel file")
vault.delete_secret("pietro@esempio-ditta.it")
check(vault.get_secret("pietro@esempio-ditta.it") is None, "password cancellata")

if sys.platform.startswith("linux"):
    import base64 as _b64  # noqa: E402
    import json as _json  # noqa: E402
    lungo = _json.dumps({"access_token": "é" * 5000, "refresh_token": "r" * 3000})
    vault.set_secret("o@x.it", lungo)
    check(vault.get_secret("o@x.it") == lungo, "Linux: token lungo di Outlook in una voce sola del portachiavi")
    vault.delete_secret("o@x.it")
    # password salvate nel file dalle versioni avviate dai sorgenti: passano nel portachiavi alla prima lettura
    with open(CRED, "w", encoding="utf-8") as fh:
        _json.dump({"v@x.it": "b64:" + _b64.b64encode("vècchia".encode()).decode()}, fh)
    check(vault.get_secret("v@x.it") == "vècchia", "Linux: password vecchia del file riletta")
    check("v@x.it" not in open(CRED, encoding="utf-8").read(), "Linux: password vecchia tolta dal file")
    check(vault.get_secret("v@x.it") == "vècchia", "Linux: password vecchia ora nel portachiavi")
    vault.delete_secret("v@x.it")
    check(vault.get_secret("v@x.it") is None, "Linux: voce di prova cancellata")
    vault.purge_service()

for s, exp_f in (("Il tuo codice di verifica: 482913", classify.F_SECURITY),
                 ("Welcome to Canva", classify.F_ACCOUNT),
                 ("Ricevuta del tuo pagamento", classify.F_PURCHASE),
                 ("Ti sei iscritto alla newsletter", classify.F_ACCOUNT)):
    check(classify.flags_for(s, "", "") & exp_f, f"segnale da «{s}»")
r = classify.parse_headers("From: Città <a@b.it>\r\nSubject: Novità della settimana\r\n\r\n".encode("utf-8"))
check(r["subject"] == "Novità della settimana" and r["from_name"] == "Città", "intestazioni in UTF-8 diretto")
check(classify.registrable("news.mail.amazon.co.uk") == "amazon.co.uk", "dominio registrato con suffisso doppio")

# ---- DKIM: Authentication-Results
AR_OUTLOOK = ("spf=pass (sender IP is 1.2.3.4) smtp.mailfrom=shop.it; dkim=pass (signature was verified) "
              "header.d=shop.it;dmarc=pass action=none header.from=shop.it")
check(classify.dkim_domini(AR_OUTLOOK) == ["shop.it"], "DKIM: formato Outlook (commenti, niente authserv-id)")
check(classify.dkim_domini("mx.google.com; dkim=pass header.i=@news.shop.it header.s=a; dkim=fail header.d=x.it")
      == ["news.shop.it"], "DKIM: formato Gmail (header.i) e firma fallita ignorata")
check(classify.dkim_domini("mx.x; dkim=pass (header.d=shop.it nel commento)") == [], "DKIM: niente domini dai commenti")
check(classify.dkim_allineato(AR_OUTLOOK, "news@mail.shop.it"), "DKIM: sottodominio del mittente allineato")
check(not classify.dkim_allineato(AR_OUTLOOK, "news@shop.it.truffa.com"), "DKIM: dominio diverso non allineato")
check(not classify.dkim_allineato("mx.x; dkim=pass header.d=co.uk", "a@shop.co.uk"), "DKIM: niente firma da un suffisso")
check(not classify.dkim_allineato("", "a@shop.it"), "DKIM: senza Authentication-Results niente fiducia")
base = "From: Shop <n@shop.it>\r\nSubject: Offerte\r\nDate: Mon, 03 Feb 2020 10:00:00 +0100\r\n"
lu = "List-Unsubscribe: <https://shop.it/u>\r\nList-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n"
r = classify.parse_headers((base + lu + "\r\n").encode())
check(r["unsub"] == "" and r["unsub_post"] == 0 and r["flags"] & classify.F_LIST,
      "senza DKIM: link non salvato, ma resta il segnale «newsletter»")
r = classify.parse_headers((base + "Authentication-Results: mx.x; dkim=pass header.d=shop.it\r\n" + lu + "\r\n").encode())
check(r["unsub"] == "<https://shop.it/u>" and r["unsub_post"] == 1, "con DKIM allineato: link salvato")
r = classify.parse_headers(("From: Shop <n@shop.it>\r\nDate: Fri, 01 Jan 2100 10:00:00 +0100\r\n\r\n").encode())
check(r["ts"] == 0, "data nel futuro → sconosciuta")
check(classify.stesso_servizio("click.news.zalando.it", "zalando.it") and
      classify.stesso_servizio("www.facebookmail.com", "facebook.com") and
      not classify.stesso_servizio("zalando.example", "zalando.it"), "host del link confrontato col servizio")

# ---- disiscrizione: solo https verso internet, anche nei redirect (nessuna rete: indirizzi numerici)
import urllib.request  # noqa: E402

from tkiscrizioni import disiscrizione as D  # noqa: E402
for h, ok in (("127.0.0.1", False), ("10.1.2.3", False), ("192.168.1.1", False), ("172.16.0.5", False),
              ("169.254.169.254", False), ("100.64.0.1", False), ("0.0.0.0", False), ("::1", False),
              ("fe80::1", False), ("::ffff:127.0.0.1", False), ("fd00::1", False), ("8.8.8.8", True),
              ("2001:4860:4860::8888", True), ("", False)):
    check(D.host_pubblico(h) is ok, f"indirizzo {h or '(vuoto)'}: {'pubblico' if ok else 'rifiutato'}")
check(not D.url_ammesso("http://8.8.8.8/u") and D.url_ammesso("https://8.8.8.8/u")
      and not D.url_ammesso("https://[::1]/u") and not D.url_ammesso("javascript:alert(1)"), "solo link https pubblici")
try:
    D.invia("https://127.0.0.1:9/u")
    check(False, "POST verso il computer stesso rifiutato")
except D.LinkNonAmmesso:
    check(True, "POST verso il computer stesso rifiutato (senza collegarsi)")
red = D._Redirect(D.host_pubblico)
req = urllib.request.Request("https://8.8.8.8/a", data=b"x", method="POST")
for dove in ("http://8.8.8.8/b", "https://192.168.0.1/b", "https://127.0.0.1/b", "/../http-relativo-ok"):
    try:
        nuovo = red.redirect_request(req, None, 302, "Found", {}, dove)
        check(dove.startswith("/") and nuovo is not None, f"redirect verso {dove}: seguito solo se https pubblico")
    except D.LinkNonAmmesso:
        check(not dove.startswith("/"), f"redirect verso {dove}: rifiutato")
check(D.host_di("mailto:unsub@liste.shop.it?subject=x") == "liste.shop.it" and
      D.host_di("https://Click.Shop.it/u?x=1") == "click.shop.it", "host del link da mostrare")

# ---- archivio di una versione precedente: i link non verificati si tolgono e la casella si rilegge
import sqlite3  # noqa: E402

vecchio = os.path.join(os.environ["TKISCR_DATA"], "vecchio.db")
db = sqlite3.connect(vecchio)
db.executescript(__import__("tkiscrizioni.store", fromlist=["SCHEMA"]).SCHEMA)
db.execute("INSERT INTO folders VALUES (1,'INBOX',7,99)")
db.execute("INSERT INTO messages VALUES (1,'INBOX',5,1e9,'a@b.it','B','b.it','ciao','<https://x.it/u>',1,8)")
db.commit()
db.close()
s2 = Store(vecchio)
check(s2.q("SELECT unsub FROM messages")[0]["unsub"] == "" and s2.folder_state(1, "INBOX") == (7, 0),
      "archivio vecchio: link non verificati tolti, la prossima analisi rilegge le intestazioni")
s2.x("UPDATE messages SET unsub='<https://x.it/u>'")
s2.db.close()
s3 = Store(vecchio)
check(s3.q("SELECT unsub FROM messages")[0]["unsub"] != "", "la pulizia dell'archivio si fa una volta sola")
s3.db.close()

# ---- Mac: password al Portachiavi via stdin (Portachiavi finto: qui si controlla la logica)
chiavi, argomenti = {}, []


def finto_security(cmd, input=None, **kw):
    import subprocess as sp
    argomenti.append(" ".join(cmd))
    if cmd[:2] == ["security", "-i"]:
        for riga in (input or "").splitlines():
            p = riga.split()
            assert p[0] == "add-generic-password" and p[1] == "-U"
            chiavi[(p[p.index("-s") + 1], p[p.index("-a") + 1])] = p[p.index("-w") + 1]
        return sp.CompletedProcess(cmd, 0, "", "")
    k = (cmd[cmd.index("-s") + 1], cmd[cmd.index("-a") + 1])
    if cmd[1] == "find-generic-password":
        return sp.CompletedProcess(cmd, 0 if k in chiavi else 44, chiavi.get(k, "") + "\n", "")
    if cmd[1] == "delete-generic-password":
        chiavi.pop(k, None)
        return sp.CompletedProcess(cmd, 0, "", "")
    raise AssertionError(cmd)


vero_run, vero_mac = vault.subprocess.run, vault.IS_MAC
vault.subprocess.run, vault.IS_MAC = finto_security, True
try:
    lungo = "token-outlook-" + "é" * 3000
    vault.set_secret("m@x.it", lungo)
    check(vault.get_secret("m@x.it") == lungo and len(chiavi) > 2, f"Mac: token lungo diviso in {len(chiavi) - 1} parti")
    vault.set_secret("m@x.it", "corta")
    check(vault.get_secret("m@x.it") == "corta" and len(chiavi) == 1, "Mac: parti vecchie tolte con una password corta")
    vault.set_secret("m@x.it", lungo)
    vault.delete_secret("m@x.it")
    check(not chiavi and vault.get_secret("m@x.it") is None, "Mac: casella tolta con tutte le parti")
    import base64  # noqa: E402
    segreti = ("corta", base64.b64encode("corta".encode()).decode())
    check(not any(s in a for a in argomenti for s in segreti),
          "Mac: la password non compare mai tra gli argomenti di «security»")
    try:
        vault.set_secret('a "b"@x.it', "x")
        check(False, "Mac: casella con virgolette rifiutata")
    except ValueError:
        check(True, "Mac: casella con virgolette rifiutata")
finally:
    vault.subprocess.run, vault.IS_MAC = vero_run, vero_mac

srv.shutdown()
print("\n" + ("TUTTO OK" if not fails else f"{len(fails)} TEST FALLITI"))
sys.exit(1 if fails else 0)
