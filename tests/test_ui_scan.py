"""Percorso completo nell'interfaccia: casella salvata → Analizza → tabella piena → disiscrizione/stato/esporta.
Usa il finto server IMAP (connessione in chiaro al posto di SSL). Uso: python tests/test_ui_scan.py"""
import imaplib
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ["TKISCR_DATA"] = tempfile.mkdtemp(prefix="tkiscr-ui-")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import fake_imap  # noqa: E402
from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tkiscrizioni import app as A, mailscan, vault  # noqa: E402
from tkiscrizioni.store import Store  # noqa: E402
from tkiscrizioni.util import Settings  # noqa: E402

srv, port = fake_imap.start()


def fake_connect(host, p, user, secret, auth="password", timeout=45):
    im = imaplib.IMAP4("127.0.0.1", port)
    try:
        im.login(user, secret)
    except imaplib.IMAP4.error as e:
        raise mailscan.AuthError(str(e))
    return im


mailscan.connect = fake_connect
fails = []


def check(c, what):
    print(("OK   " if c else "FAIL ") + what)
    if not c:
        fails.append(what)


qa = QApplication(sys.argv)
store = Store()
store.add_account("pietro@esempio-ditta.it", "altro", "imap.esempio-ditta.it", 993, "password")
store.add_account("sbagliata@esempio-ditta.it", "altro", "imap.esempio-ditta.it", 993, "password")
vault.set_secret("pietro@esempio-ditta.it", "segreta")
vault.set_secret("sbagliata@esempio-ditta.it", "no")
win = A.MainWindow(Settings(), store)
A.tk_warn = lambda parent, title, text: print("     (avviso mostrato) " + text.replace("\n", " | "))
win.show()
check(win.stack.currentIndex() == 1, "con caselle si vede la schermata principale")

loop = QEventLoop()
win.start_scan(store.accounts())
win.scan_thread.finished_all.connect(lambda _r: QTimer.singleShot(200, loop.quit))
QTimer.singleShot(20000, loop.quit)
loop.exec()
check(win.proxy.rowCount() >= 7, f"tabella piena dopo l'analisi ({win.proxy.rowCount()} servizi)")
accs = {a["email"]: a for a in store.accounts()}
check(accs["pietro@esempio-ditta.it"]["last_scan"] > 0 and not accs["pietro@esempio-ditta.it"]["last_error"],
      "casella buona: analizzata, senza errori")
check("rifiutato" in accs["sbagliata@esempio-ditta.it"]["last_error"],
      f"casella con password sbagliata: errore salvato ({accs['sbagliata@esempio-ditta.it']['last_error']})")
TOT = str(len(fake_imap.DEMO))
check(win.tiles["mail"].text() == TOT, f"riquadro email analizzate = {TOT} ({win.tiles['mail'].text()})")

win._set_cat("newsletter")
check(win.proxy.rowCount() == 1, "filtro Newsletter: solo Zalando")
win._set_cat("")
win.search.setText("netf")
check(win.proxy.rowCount() == 1, "ricerca «netf»: solo Netflix")
win.search.setText("")
win.select_domain("netflix.com")
check(win.cur and win.cur["domain"] == "netflix.com", "dettaglio di Netflix aperto")
check(win.b_unsub.isEnabled() and "cerco come fare" in win.b_unsub.toolTip(),
      "Netflix senza link di disiscrizione: pulsante acceso, apre la ricerca")
win.act_status("cancellare")
check({s["domain"]: s for s in store.services()}["netflix.com"]["status"] == "cancellare", "stato «Da cancellare» salvato")
win._set_status_filter("cancellare")
check(win.proxy.rowCount() == 1, "filtro Stato «Da cancellare»")
win._set_status_filter("")
win.select_domain("zalando.it")
check(win.b_unsub.isEnabled() and win.b_unsub.toolTip() == "Disiscrizione in un clic",
      "Zalando: pulsante Disiscriviti acceso, disiscrizione in un clic")
avviso = A.MainWindow._avviso_link("https://zalando.example/unsub?u=1", win.cur)
check("«zalando.example»" in avviso and "Attenzione" in avviso, "prima di disiscriversi: host mostrato e avviso")
check("Attenzione" not in A.MainWindow._avviso_link("https://click.zalando.it/u", win.cur) and
      "«liste.zalando.it»" in A.MainWindow._avviso_link("mailto:via@liste.zalando.it", win.cur),
      "nessun avviso se il link è del servizio; per mailto si mostra il dominio")

# disiscrizione in un clic verso un host che non porta a internet: niente richiesta, stato invariato
avvisi = []
vero_choice, vero_warn, vero_info = A.tk_choice, A.tk_warn, A.tk_info
A.tk_choice = lambda *a, **k: 1
A.tk_warn = lambda parent, title, text: avvisi.append(text)
A.tk_info = lambda *a, **k: avvisi.append("OK")
win.act_unsub()
loop3 = QEventLoop()
win._unsub_worker.finished.connect(lambda: QTimer.singleShot(100, loop3.quit))
QTimer.singleShot(20000, loop3.quit)
loop3.exec()
check(avvisi and "Non mando la richiesta" in avvisi[0] and
      {s["domain"]: s for s in store.services()}["zalando.it"]["status"] == "",
      f"link verso un host non pubblico: richiesta non inviata ({avvisi})")
A.tk_choice, A.tk_warn, A.tk_info = vero_choice, vero_warn, vero_info
check(A.STATUS["disiscritto"][0] == "Richiesta inviata", "stato «Richiesta inviata» (non «Disiscritto»)")

store.set_status("netflix.com", note="=HYPERLINK(\"http://x\")")
win.refresh()
out = win.act_export(os.path.join(os.environ["TKISCR_DATA"], "prova.csv"))
txt = open(out, encoding="utf-8-sig").read()
check("Netflix;netflix.com;Account" in txt and "Da cancellare" in txt, "esportazione CSV con stato")
check("'=HYPERLINK" in txt and ";=HYPERLINK" not in txt and ';"=HYPERLINK' not in txt,"CSV: celle che Excel leggerebbe come formula con «'» davanti")
check([A.cella_csv(v) for v in ("=1+1", "+39", "-2", "@x", "\tx", "\rx", "Netflix", 5)] ==
      ["'=1+1", "'+39", "'-2", "'@x", "'\tx", "'\rx", "Netflix", 5], "CSV: tutti i caratteri pericolosi")

# seconda analisi: niente doppioni
loop2 = QEventLoop()
win.start_scan([a for a in store.accounts() if a["email"].startswith("pietro")])
win.scan_thread.finished_all.connect(lambda _r: QTimer.singleShot(200, loop2.quit))
QTimer.singleShot(20000, loop2.quit)
loop2.exec()
check(win.tiles["mail"].text() == TOT, "seconda analisi: nessun doppione")

a = [x for x in store.accounts() if x["email"].startswith("sbagliata")][0]
A.tk_choice = lambda *a, **k: 1
win.act_remove(a)
check(len(store.accounts()) == 1 and vault.get_secret("sbagliata@esempio-ditta.it") is None,
      "casella tolta insieme alla sua password")
srv.shutdown()
print("\n" + ("TUTTO OK" if not fails else f"{len(fails)} TEST FALLITI"))
sys.exit(1 if fails else 0)
